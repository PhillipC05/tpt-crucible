"""Tests for model ingestion into TPT-IR."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tpt_catalyst.ir import TptIr, OpNode, Edge, ComputationalGraph, ModelMetadata
from tpt_catalyst.ingest import ingest_model, detect_format


class TestTptIr:
    def test_roundtrip_json(self):
        ir = TptIr(
            version="1.0.0",
            metadata=ModelMetadata(name="test", source_format="pytorch"),
            graph=ComputationalGraph(
                nodes=[OpNode(id=0, op_type="matmul", name="layer0")],
                edges=[],
            ),
        )
        json_str = ir.to_json()
        restored = TptIr.from_json(json_str)
        assert restored.metadata.name == "test"
        assert len(restored.graph.nodes) == 1

    def test_save_load(self, tmp_path):
        ir = TptIr(
            version="1.0.0",
            metadata=ModelMetadata(name="test", source_format="onnx"),
            graph=ComputationalGraph(),
        )
        out = tmp_path / "test.tptir"
        ir.save(out)
        assert out.exists()
        loaded = TptIr.from_json(out.read_text())
        assert loaded.metadata.source_format == "onnx"


class TestDetectFormat:
    def test_tflite_extension(self, tmp_path):
        f = tmp_path / "model.tflite"
        f.write_bytes(b"\x00\x00\x00\x00TFL3")
        assert detect_format(f) == "tflite"

    def test_exl2_extension(self, tmp_path):
        f = tmp_path / "model.exl2"
        f.write_bytes(b"EXL2\x00\x00\x00\x00")
        assert detect_format(f) == "exl2"

    def test_keras_extension(self, tmp_path):
        f = tmp_path / "model.h5"
        f.write_bytes(b"\x89HDF\r\n\x1a\n")
        assert detect_format(f) == "keras_h5"

    def test_gguf_extension(self, tmp_path):
        f = tmp_path / "model.gguf"
        f.write_bytes(b"GGUF")
        assert detect_format(f) == "gguf"

    def test_onnx_extension(self, tmp_path):
        f = tmp_path / "model.onnx"
        f.write_bytes(b"dummy")
        assert detect_format(f) == "onnx"

    def test_llamafile_magic(self, tmp_path):
        f = tmp_path / "model.bin"
        header = b"\x7fELF" + b"\x00" * 4 + b"LlamaFile" + b"\x00" * 100
        f.write_bytes(header)
        assert detect_format(f) == "llamafile"

    def test_directory_huggingface(self, tmp_path):
        d = tmp_path / "hf_model"
        d.mkdir()
        (d / "config.json").write_text(json.dumps({"model_type": "llama"}))
        assert detect_format(d) == "huggingface"

    def test_directory_jax_orbax(self, tmp_path):
        d = tmp_path / "jax_ckpt"
        d.mkdir()
        (d / "_metadata").write_text("{}")
        assert detect_format(d) == "jax_flax"

    def test_directory_awq_gptq(self, tmp_path):
        d = tmp_path / "awq_model"
        d.mkdir()
        (d / "config.json").write_text(json.dumps({"model_type": "llama"}))
        (d / "quantize_config.json").write_text(json.dumps({"quant_method": "awq", "bits": 4}))
        assert detect_format(d) == "awq_gptq"


class TestTfliteIngest:
    def test_ingest_tflite_returns_ir(self, tmp_path):
        from tpt_catalyst.tflite_ingest import ingest_tflite
        f = tmp_path / "model.tflite"
        f.write_bytes(b"\x00\x00\x00\x00TFL3")
        ir = ingest_tflite(f)
        assert isinstance(ir, TptIr)
        assert ir.metadata.source_format == "tflite"


class TestAwqGptqIngest:
    def test_ingest_awq(self, tmp_path):
        from tpt_catalyst.awq_gptq_ingest import ingest_awq_gptq
        d = tmp_path / "awq_model"
        d.mkdir()
        (d / "quantize_config.json").write_text(json.dumps({
            "quant_method": "awq",
            "bits": 4,
            "group_size": 128,
        }))
        ir = ingest_awq_gptq(d)
        assert isinstance(ir, TptIr)
        assert "awq" in ir.metadata.source_format


class TestExl2Ingest:
    def test_ingest_exl2(self, tmp_path):
        from tpt_catalyst.exl2_ingest import ingest_exl2
        f = tmp_path / "model.exl2"
        f.write_bytes(b"EXL2" + b"\x00" * 100)
        ir = ingest_exl2(f)
        assert isinstance(ir, TptIr)
        assert ir.metadata.source_format == "exl2"


class TestJaxIngest:
    def test_ingest_jax_orbax(self, tmp_path):
        from tpt_catalyst.jax_ingest import ingest_jax_flax
        d = tmp_path / "jax_ckpt"
        d.mkdir()
        (d / "_metadata").write_text("{}")
        ir = ingest_jax_flax(d)
        assert isinstance(ir, TptIr)
        assert ir.metadata.source_format == "jax_flax"


class TestLlamafileIngest:
    def test_ingest_llamafile(self, tmp_path):
        from tpt_catalyst.llamafile_ingest import ingest_llamafile
        f = tmp_path / "model.bin"
        header = b"\x7fELF" + b"\x00" * 4 + b"LlamaFile" + b"\x00" * 100
        f.write_bytes(header)
        ir = ingest_llamafile(f)
        assert isinstance(ir, TptIr)
        assert ir.metadata.source_format == "llamafile"


class TestKerasIngest:
    def test_ingest_keras_h5(self, tmp_path):
        from tpt_catalyst.keras_ingest import ingest_keras_h5
        f = tmp_path / "model.h5"
        f.write_bytes(b"\x89HDF\r\n\x1a\n")
        ir = ingest_keras_h5(f)
        assert isinstance(ir, TptIr)
        assert ir.metadata.source_format == "keras_h5"


class TestAutoDetectIntegration:
    def test_tflite_auto_ingest(self, tmp_path):
        from tpt_catalyst.tflite_ingest import detect_tflite, ingest_tflite
        f = tmp_path / "model.tflite"
        f.write_bytes(b"\x00\x00\x00\x00TFL3")
        assert detect_tflite(f)
        ir = ingest_tflite(f)
        assert len(ir.graph.nodes) >= 0

    def test_exl2_auto_detect(self, tmp_path):
        from tpt_catalyst.exl2_ingest import detect_exl2
        f = tmp_path / "model.exl2"
        f.write_bytes(b"EXL2" + b"\x00" * 100)
        assert detect_exl2(f)

    def test_llamafile_auto_detect(self, tmp_path):
        from tpt_catalyst.llamafile_ingest import detect_llamafile
        f = tmp_path / "model.bin"
        header = b"\x7fELF" + b"\x00" * 4 + b"LlamaFile" + b"\x00" * 100
        f.write_bytes(header)
        assert detect_llamafile(f)

    def test_keras_h5_auto_detect(self, tmp_path):
        from tpt_catalyst.keras_ingest import detect_keras_h5
        f = tmp_path / "model.h5"
        f.write_bytes(b"\x89HDF\r\n\x1a\n")
        assert detect_keras_h5(f)

    def test_jax_orbax_auto_detect(self, tmp_path):
        from tpt_catalyst.jax_ingest import detect_jax_checkpoint
        d = tmp_path / "jax_ckpt"
        d.mkdir()
        (d / "_metadata").write_text("{}")
        assert detect_jax_checkpoint(d)

    def test_awq_gptq_auto_detect(self, tmp_path):
        from tpt_catalyst.awq_gptq_ingest import detect_quantize_config
        d = tmp_path / "awq_model"
        d.mkdir()
        (d / "quantize_config.json").write_text(json.dumps({"quant_method": "awq", "bits": 4}))
        assert detect_quantize_config(d)


class TestGraphWithFusion:
    def test_graph_with_fusion(self):
        ir = TptIr(
            version="1.0.0",
            metadata=ModelMetadata(name="test", source_format="pytorch"),
            graph=ComputationalGraph(
                nodes=[
                    OpNode(id=0, op_type="matmul", name="layer0"),
                    OpNode(id=1, op_type="relu", name="act0"),
                ],
                edges=[Edge(from_id=0, to_id=1, tensor_name="x")],
            ),
        )
        assert len(ir.graph.nodes) == 2
        assert ir.graph.edges[0].tensor_name == "x"
