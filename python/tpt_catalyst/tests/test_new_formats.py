"""Unit tests for new model format ingestion: TFLite, AWQ/GPTQ, EXL2, JAX/Flax, Llamafile, Keras.

Verifies TPT-IR output is structurally equivalent across formats.
"""

from pathlib import Path
import json
import struct

from tpt_catalyst.ingest import detect_format, ingest_model
from tpt_catalyst.tflite_ingest import (
    detect_tflite, ingest_tflite, TFLITE_MAGIC, TFLITE_OP_CODES,
    TfliteQuantizationParams, TfliteTensorInfo, TfliteModelInfo,
)
from tpt_catalyst.awq_gptq_ingest import (
    detect_quantize_config, parse_quantize_config, ingest_awq_gptq,
    AwqConfig, GptqConfig, QuantLayerConfig,
)
from tpt_catalyst.exl2_ingest import (
    detect_exl2, ingest_exl2, EXL2_MAGIC, EXL2_QUANT_TYPES,
    Exl2QuantTable, Exl2LayerInfo, Exl2ModelInfo,
)
from tpt_catalyst.jax_ingest import (
    detect_jax_checkpoint, detect_jax_safetensors, ingest_jax_flax,
    JaxParamTensor, JaxParamTree,
)
from tpt_catalyst.llamafile_ingest import (
    detect_llamafile, find_gguf_offset, ingest_llamafile,
    ELF_MAGIC, LLAMAFILE_MAGIC, GGUF_MAGIC,
)
from tpt_catalyst.keras_ingest import (
    detect_keras_h5, ingest_keras_h5, HDF5_MAGIC,
)


# ─── Helpers ────────────────────────────────────────────────────────

def _make_tflite_file(path: Path, num_ops: int = 3) -> None:
    """Create a minimal TFLite-like file with TFL3 magic."""
    # FlatBuffer-like structure: root offset + TFL3 magic + op codes
    data = bytearray()
    # Offset to root table (4 bytes, points to end of file)
    data += struct.pack("<I", 0)  # placeholder
    # TFL3 magic
    data += TFLITE_MAGIC
    # Version
    data += struct.pack("<I", 3)
    # Simple op entries
    for i in range(min(num_ops, 3)):
        data += struct.pack("<I", i)  # op code
    # Update root offset
    struct.pack_into("<I", data, 0, len(data) - 4)
    path.write_bytes(bytes(data))


def _make_exl2_file(path: Path, num_layers: int = 2) -> None:
    """Create a minimal EXL2-like file."""
    data = bytearray()
    # Header: magic(4) + version(4) + num_layers(4) + metadata_size(4) + reserved(4)
    data += EXL2_MAGIC
    data += struct.pack("<I", 2)  # version
    data += struct.pack("<I", num_layers)
    metadata = json.dumps({"model_name": path.stem}).encode()
    data += struct.pack("<I", len(metadata))
    data += struct.pack("<I", 0)  # reserved
    data += metadata

    # Layer headers
    for i in range(num_layers):
        name = f"layer_{i}".encode()
        data += struct.pack("<I", len(name))
        data += name
        data += struct.pack("<I", 6)  # quant_type = Q4_K
        data += struct.pack("<I", 128)  # weight_rows
        data += struct.pack("<I", 256)  # weight_cols
        data += struct.pack("<Q", 0)  # scale_offset
        data += struct.pack("<I", 0)  # scale_size
        data += struct.pack("<Q", 0)  # zero_offset
        data += struct.pack("<I", 0)  # zero_size

    path.write_bytes(bytes(data))


def _make_llamafile(path: Path) -> None:
    """Create a minimal llamafile (ELF header + LlamaFile marker + GGUF data)."""
    data = bytearray()
    # ELF header (64 bytes for 64-bit)
    data += ELF_MAGIC  # e_ident[0:4]
    data += b"\x02"  # EI_CLASS: 64-bit
    data += b"\x01"  # EI_DATA: little-endian
    data += b"\x01"  # EI_VERSION
    data += b"\x00" * 9  # padding
    # Put LlamaFile marker at offset 0x08 (right after e_ident)
    data += LLAMAFILE_MAGIC
    # Continue with rest of ELF header
    data += struct.pack("<H", 0x0002)  # e_type: EXEC
    data += struct.pack("<H", 0x003E)  # e_machine: x86-64
    data += struct.pack("<I", 1)  # e_version
    data += struct.pack("<Q", 0)  # e_entry
    data += struct.pack("<Q", 64)  # e_phoff
    data += struct.pack("<Q", 0)  # e_shoff
    data += struct.pack("<I", 0)  # e_flags
    data += struct.pack("<H", 64)  # e_ehsize
    data += struct.pack("<H", 56)  # e_phentsize
    data += struct.pack("<H", 0)  # e_phnum
    data += struct.pack("<H", 0)  # e_shentsize
    data += struct.pack("<H", 0)  # e_shnum
    data += struct.pack("<H", 0)  # e_shstrndx
    # Pad to offset 0x40
    while len(data) < 0x40:
        data += b"\x00"
    # GGUF data
    data += GGUF_MAGIC
    data += struct.pack("<I", 3)  # version
    data += struct.pack("<Q", 0)  # tensor_count
    data += struct.pack("<Q", 0)  # metadata_kv_count
    path.write_bytes(bytes(data))


def _make_keras_h5_file(path: Path) -> None:
    """Create a minimal HDF5-like file (Keras uses HDF5 format)."""
    data = bytearray()
    data += HDF5_MAGIC
    # Superblock
    data += b"\x00"  # version
    data += b"\x00"  # superblock version
    data += b"\x00" * 2  # free space version + root group symbol table entry
    data += b"\x00" * 4  # shared header message format version
    data += b"\x08"  # size of offsets
    data += b"\x08"  # size of lengths
    data += b"\x00"  # file consistency flags
    data += struct.pack("<H", 0)  # indexed storage internal node K
    data += b"\x00" * 2  # reserved
    data += struct.pack("<I", 1)  # group leaf node K
    data += struct.pack("<I", 0)  # base address
    data += struct.pack("<I", 0)  # superblock extension address
    data += struct.pack("<I", 0)  # end of file address
    data += struct.pack("<I", 0)  # root group symbol table entry address
    path.write_bytes(bytes(data))


# ─── TFLite Tests ───────────────────────────────────────────────────

class TestTfliteIngestion:
    def test_detect_tflite_by_magic(self, tmp_path):
        f = tmp_path / "model.tflite"
        _make_tflite_file(f)
        assert detect_tflite(f)

    def test_detect_tflite_rejects_non_tflite(self, tmp_path):
        f = tmp_path / "model.tflite"
        f.write_bytes(b"NOT_TFLITE_DATA")
        assert not detect_tflite(f)

    def test_ingest_tflite_stub(self, tmp_path):
        f = tmp_path / "model.tflite"
        _make_tflite_file(f)
        ir = ingest_tflite(f)
        assert ir.metadata.source_format == "tflite"
        assert ir.version == "1.0.0"

    def test_ingest_tflite_via_dispatch(self, tmp_path):
        f = tmp_path / "model.tflite"
        _make_tflite_file(f)
        ir = ingest_model(f)
        assert ir.metadata.source_format == "tflite"

    def test_detect_format_tflite(self, tmp_path):
        f = tmp_path / "model.tflite"
        _make_tflite_file(f)
        assert detect_format(f) == "tflite"

    def test_tflite_quant_params(self):
        q = TfliteQuantizationParams(scale=0.5, zero_point=128, quantized=True, bits=8, quant_type="INT8")
        d = q.to_dict()
        assert d["scale"] == 0.5
        assert d["zero_point"] == 128
        assert d["quantized"] is True
        assert d["bits"] == 8

    def test_tflite_tensor_info(self):
        t = TfliteTensorInfo(name="test", shape=[1, 224, 224, 3], dtype="float30")
        d = t.to_dict()
        assert d["name"] == "test"
        assert d["shape"] == [1, 224, 224, 3]

    def test_tflite_model_info_has_quantization(self):
        info = TfliteModelInfo(name="test")
        info.tensors.append(TfliteTensorInfo(
            name="q_tensor", shape=[128], dtype="int8",
            quantization=TfliteQuantizationParams(quantized=True, bits=8),
        ))
        assert info.has_quantization

    def test_tflite_model_info_no_quantization(self):
        info = TfliteModelInfo(name="test")
        info.tensors.append(TfliteTensorInfo(
            name="f_tensor", shape=[128], dtype="float32",
        ))
        assert not info.has_quantization


# ─── AWQ/GPTQ Tests ────────────────────────────────────────────────

class TestAwqGptqIngestion:
    def test_detect_quantize_config(self, tmp_path):
        model_dir = tmp_path / "model"
        model_dir.mkdir()
        config = {"quant_method": "awq", "bits": 4, "group_size": 128}
        (model_dir / "quantize_config.json").write_text(json.dumps(config))
        assert detect_quantize_config(model_dir)

    def test_detect_quantize_config_missing(self, tmp_path):
        model_dir = tmp_path / "model"
        model_dir.mkdir()
        assert not detect_quantize_config(model_dir)

    def test_parse_awq_config(self, tmp_path):
        config_path = tmp_path / "quantize_config.json"
        config = {"quant_method": "awq", "bits": 4, "group_size": 128, "version": "GEMM"}
        config_path.write_text(json.dumps(config))
        result = parse_quantize_config(config_path)
        assert isinstance(result, AwqConfig)
        assert result.bits == 4
        assert result.group_size == 128
        assert result.quant_method == "awq"

    def test_parse_gptq_config(self, tmp_path):
        config_path = tmp_path / "quantize_config.json"
        config = {"quant_method": "gptq", "bits": 4, "group_size": 128, "sym": True}
        config_path.write_text(json.dumps(config))
        result = parse_quantize_config(config_path)
        assert isinstance(result, GptqConfig)
        assert result.bits == 4
        assert result.sym is True
        assert result.quant_method == "gptq"

    def test_ingest_awq_with_config(self, tmp_path):
        model_dir = tmp_path / "awq_model"
        model_dir.mkdir()
        quant_config = {"quant_method": "awq", "bits": 4, "group_size": 128}
        (model_dir / "quantize_config.json").write_text(json.dumps(quant_config))
        model_config = {
            "model_type": "llama",
            "architectures": ["LlamaForCausalLM"],
            "hidden_size": 2048,
            "num_hidden_layers": 4,
            "num_attention_heads": 32,
        }
        (model_dir / "config.json").write_text(json.dumps(model_config))
        ir = ingest_awq_gptq(model_dir)
        assert ir.metadata.source_format == "huggingface_awq"
        assert len(ir.graph.nodes) > 0

    def test_ingest_gptq_with_config(self, tmp_path):
        model_dir = tmp_path / "gptq_model"
        model_dir.mkdir()
        quant_config = {"quant_method": "gptq", "bits": 4, "group_size": 128}
        (model_dir / "quantize_config.json").write_text(json.dumps(quant_config))
        model_config = {
            "model_type": "mistral",
            "architectures": ["MistralForCausalLM"],
            "hidden_size": 4096,
            "num_hidden_layers": 2,
            "num_attention_heads": 32,
        }
        (model_dir / "config.json").write_text(json.dumps(model_config))
        ir = ingest_awq_gptq(model_dir)
        assert ir.metadata.source_format == "huggingface_gptq"
        assert len(ir.graph.nodes) > 0

    def test_ingest_awq_gptq_stub(self, tmp_path):
        model_dir = tmp_path / "empty_model"
        model_dir.mkdir()
        ir = ingest_awq_gptq(model_dir)
        assert ir.metadata.source_format == "huggingface_awq_gptq"

    def test_detect_format_awq(self, tmp_path):
        model_dir = tmp_path / "awq_model"
        model_dir.mkdir()
        (model_dir / "config.json").write_text(json.dumps({"model_type": "llama"}))
        (model_dir / "quantize_config.json").write_text(json.dumps({"quant_method": "awq", "bits": 4}))
        assert detect_format(model_dir) == "awq_gptq"

    def test_quant_layer_config_to_dict(self):
        cfg = QuantLayerConfig(layer_name="layer_0", bits=4, group_size=128)
        d = cfg.to_dict()
        assert d["layer_name"] == "layer_0"
        assert d["bits"] == 4
        assert d["group_size"] == 128


# ─── EXL2 Tests ────────────────────────────────────────────────────

class TestExl2Ingestion:
    def test_detect_exl2_by_magic(self, tmp_path):
        f = tmp_path / "model.exl2"
        _make_exl2_file(f)
        assert detect_exl2(f)

    def test_detect_exl2_rejects_non_exl2(self, tmp_path):
        f = tmp_path / "model.exl2"
        f.write_bytes(b"NOT_EXL2_DATA")
        assert not detect_exl2(f)

    def test_ingest_exl2_stub(self, tmp_path):
        f = tmp_path / "model.exl2"
        _make_exl2_file(f)
        ir = ingest_exl2(f)
        assert ir.metadata.source_format == "exl2"

    def test_ingest_exl2_via_dispatch(self, tmp_path):
        f = tmp_path / "model.exl2"
        _make_exl2_file(f)
        ir = ingest_model(f)
        assert ir.metadata.source_format == "exl2"

    def test_detect_format_exl2(self, tmp_path):
        f = tmp_path / "model.exl2"
        _make_exl2_file(f)
        assert detect_format(f) == "exl2"

    def test_exl2_quant_table(self):
        qt = Exl2QuantTable(layer_name="layer_0", quant_type="Q4_K", bits=4)
        d = qt.to_dict()
        assert d["quant_type"] == "Q4_K"
        assert d["bits"] == 4

    def test_exl2_model_info_parameter_count(self):
        info = Exl2ModelInfo(name="test")
        info.layers.append(Exl2LayerInfo(name="l0", quant_type=6, weight_rows=128, weight_cols=256))
        info.layers.append(Exl2LayerInfo(name="l1", quant_type=6, weight_rows=256, weight_cols=128))
        assert info.parameter_count == 128 * 256 + 256 * 128


# ─── JAX/Flax Tests ────────────────────────────────────────────────

class TestJaxFlaxIngestion:
    def test_detect_jax_checkpoint(self, tmp_path):
        model_dir = tmp_path / "jax_model"
        model_dir.mkdir()
        (model_dir / "_metadata").write_text("{}")
        assert detect_jax_checkpoint(model_dir)

    def test_detect_jax_checkpoint_missing(self, tmp_path):
        model_dir = tmp_path / "jax_model"
        model_dir.mkdir()
        assert not detect_jax_checkpoint(model_dir)

    def test_detect_jax_safetensors(self, tmp_path):
        model_dir = tmp_path / "flax_model"
        model_dir.mkdir()
        (model_dir / "config.json").write_text(json.dumps({
            "model_type": "llama",
            "architectures": ["FlaxLlamaForCausalLM"],
        }))
        (model_dir / "model.safetensors").write_bytes(b"")
        assert detect_jax_safetensors(model_dir)

    def test_detect_jax_safetensors_no_flax(self, tmp_path):
        model_dir = tmp_path / "non_flax_model"
        model_dir.mkdir()
        (model_dir / "config.json").write_text(json.dumps({
            "model_type": "llama",
            "architectures": ["LlamaForCausalLM"],
        }))
        (model_dir / "model.safetensors").write_bytes(b"")
        assert not detect_jax_safetensors(model_dir)

    def test_ingest_jax_flax_stub(self, tmp_path):
        model_dir = tmp_path / "jax_model"
        model_dir.mkdir()
        (model_dir / "_metadata").write_text("{}")
        ir = ingest_jax_flax(model_dir)
        assert ir.metadata.source_format == "jax_flax"

    def test_detect_format_jax(self, tmp_path):
        model_dir = tmp_path / "jax_model"
        model_dir.mkdir()
        (model_dir / "_metadata").write_text("{}")
        assert detect_format(model_dir) == "jax_flax"

    def test_jax_param_tensor_num_elements(self):
        t = JaxParamTensor(name="test", shape=[128, 256], dtype="float32")
        assert t.num_elements == 128 * 256

    def test_jax_param_tree_parameter_count(self):
        tree = JaxParamTree()
        tree.params["w1"] = JaxParamTensor(name="w1", shape=[128, 256], dtype="float32")
        tree.params["w2"] = JaxParamTensor(name="w2", shape=[256, 128], dtype="float32")
        assert tree.parameter_count == 128 * 256 + 256 * 128


# ─── Llamafile Tests ───────────────────────────────────────────────

class TestLlamafileIngestion:
    def test_detect_llamafile(self, tmp_path):
        f = tmp_path / "model.llamafile"
        # Create a file with ELF magic + LlamaFile marker
        data = bytearray(b"\x7fELF" + b"\x00" * 4 + b"LlamaFile" + b"\x00" * 100)
        f.write_bytes(bytes(data))
        assert detect_llamafile(f)

    def test_detect_llamafile_rejects_non_llamafile(self, tmp_path):
        f = tmp_path / "model.llamafile"
        f.write_bytes(b"NOT_ELF_DATA")
        assert not detect_llamafile(f)

    def test_find_gguf_offset(self, tmp_path):
        f = tmp_path / "model.llamafile"
        _make_llamafile(f)
        offset = find_gguf_offset(f)
        assert offset > 0

    def test_ingest_llamafile_stub(self, tmp_path):
        f = tmp_path / "model.llamafile"
        _make_llamafile(f)
        ir = ingest_llamafile(f)
        assert ir.metadata.source_format == "llamafile"

    def test_ingest_llamafile_via_dispatch(self, tmp_path):
        f = tmp_path / "model.llamafile"
        _make_llamafile(f)
        ir = ingest_model(f)
        assert ir.metadata.source_format == "llamafile"

    def test_detect_format_llamafile(self, tmp_path):
        f = tmp_path / "model.llamafile"
        _make_llamafile(f)
        assert detect_format(f) == "llamafile"


# ─── Keras Tests ───────────────────────────────────────────────────

class TestKerasIngestion:
    def test_detect_keras_h5(self, tmp_path):
        f = tmp_path / "model.h5"
        _make_keras_h5_file(f)
        assert detect_keras_h5(f)

    def test_detect_keras_h5_rejects_non_hdf5(self, tmp_path):
        f = tmp_path / "model.h5"
        f.write_bytes(b"NOT_HDF5_DATA")
        assert not detect_keras_h5(f)

    def test_ingest_keras_stub(self, tmp_path):
        f = tmp_path / "model.h5"
        _make_keras_h5_file(f)
        ir = ingest_keras_h5(f)
        assert ir.metadata.source_format == "keras_h5"

    def test_ingest_keras_via_dispatch(self, tmp_path):
        f = tmp_path / "model.h5"
        _make_keras_h5_file(f)
        ir = ingest_model(f)
        assert ir.metadata.source_format == "keras_h5"

    def test_detect_format_keras(self, tmp_path):
        f = tmp_path / "model.h5"
        _make_keras_h5_file(f)
        assert detect_format(f) == "keras_h5"

    def test_detect_format_keras_keras_ext(self, tmp_path):
        f = tmp_path / "model.keras"
        _make_keras_h5_file(f)
        assert detect_format(f) == "keras_h5"


# ─── Auto-Detection Tests ──────────────────────────────────────────

class TestAutoDetection:
    def test_detect_format_by_extension_tflite(self, tmp_path):
        f = tmp_path / "model.tflite"
        _make_tflite_file(f)
        assert detect_format(f) == "tflite"

    def test_detect_format_by_extension_exl2(self, tmp_path):
        f = tmp_path / "model.exl2"
        _make_exl2_file(f)
        assert detect_format(f) == "exl2"

    def test_detect_format_by_extension_llamafile(self, tmp_path):
        f = tmp_path / "model.llamafile"
        _make_llamafile(f)
        assert detect_format(f) == "llamafile"

    def test_detect_format_by_extension_keras(self, tmp_path):
        f = tmp_path / "model.h5"
        _make_keras_h5_file(f)
        assert detect_format(f) == "keras_h5"

    def test_detect_format_by_extension_gguf(self, tmp_path):
        f = tmp_path / "model.gguf"
        f.write_bytes(b"GGUF" + b"\x00" * 100)
        assert detect_format(f) == "gguf"

    def test_detect_format_by_extension_safetensors(self, tmp_path):
        f = tmp_path / "model.safetensors"
        f.write_bytes(b"PK" + b"\x00" * 100)
        assert detect_format(f) == "safetensors"

    def test_detect_format_directory_huggingface(self, tmp_path):
        model_dir = tmp_path / "hf_model"
        model_dir.mkdir()
        (model_dir / "config.json").write_text(json.dumps({"model_type": "llama"}))
        assert detect_format(model_dir) == "huggingface"

    def test_detect_format_directory_safetensors(self, tmp_path):
        model_dir = tmp_path / "st_model"
        model_dir.mkdir()
        (model_dir / "model.safetensors").write_bytes(b"")
        assert detect_format(model_dir) == "safetensors"

    def test_detect_format_unsupported(self, tmp_path):
        f = tmp_path / "model.unknown"
        f.write_bytes(b"UNKNOWN")
        import pytest
        with pytest.raises(ValueError, match="Unsupported model format"):
            detect_format(f)


# ─── Structural Equivalence Tests ──────────────────────────────────

class TestStructuralEquivalence:
    """Verify TPT-IR output structure is consistent across all new formats."""

    def test_all_formats_produce_valid_ir(self, tmp_path):
        """Every format should produce a TptIr with version, metadata, and graph."""
        test_files = [
            ("model.tflite", lambda p: _make_tflite_file(p)),
            ("model.exl2", lambda p: _make_exl2_file(p)),
            ("model.llamafile", lambda p: _make_llamafile(p)),
            ("model.h5", lambda p: _make_keras_h5_file(p)),
        ]
        for filename, maker in test_files:
            f = tmp_path / filename
            maker(f)
            ir = ingest_model(f)
            assert ir.version == "1.0.0"
            assert ir.metadata.name == "model"
            assert ir.metadata.source_format != ""
            assert ir.graph is not None

    def test_all_formats_have_source_format(self, tmp_path):
        """Each format should set a distinct source_format."""
        formats_and_files = [
            ("tflite", "model.tflite", lambda p: _make_tflite_file(p)),
            ("exl2", "model.exl2", lambda p: _make_exl2_file(p)),
            ("llamafile", "model.llamafile", lambda p: _make_llamafile(p)),
            ("keras_h5", "model.h5", lambda p: _make_keras_h5_file(p)),
        ]
        for expected_format, filename, maker in formats_and_files:
            f = tmp_path / filename
            maker(f)
            ir = ingest_model(f)
            assert ir.metadata.source_format == expected_format, (
                f"Expected {expected_format}, got {ir.metadata.source_format}"
            )

    def test_ir_json_roundtrip(self, tmp_path):
        """TPT-IR from any format should survive JSON serialization roundtrip."""
        f = tmp_path / "model.tflite"
        _make_tflite_file(f)
        ir = ingest_model(f)
        json_str = ir.to_json()
        restored = ir.__class__.from_json(json_str)
        assert restored.version == ir.version
        assert restored.metadata.source_format == ir.metadata.source_format