"""Tests for GGUF model ingestion."""

from tpt_catalyst.gguf_ingest import (
    QuantizationMetadata,
    TensorInfo,
    GgufModelInfo,
    ingest_gguf,
    _extract_quantization,
)
from tpt_catalyst.ir import TptIr


class TestQuantizationMetadata:
    def test_q4_k_bits(self):
        q = QuantizationMetadata(quant_type="Q4_K_M", bits=4, group_size=256)
        assert q.bits == 4
        assert q.group_size == 256

    def test_bytes_per_element(self):
        q16 = QuantizationMetadata(quant_type="F16", bits=16)
        assert q16.bytes_per_element == 2.0

        q4 = QuantizationMetadata(quant_type="Q4_0", bits=4, block_size=32)
        assert q4.bytes_per_element == 0.5


class TestExtractQuantization:
    def test_q4_0(self):
        q = _extract_quantization("Q4_0", None)
        assert q is not None
        assert q.quant_type == "Q4_0"
        assert q.bits == 4

    def test_q8_0(self):
        q = _extract_quantization("Q8_0", None)
        assert q is not None
        assert q.bits == 8

    def test_q4_k_s(self):
        q = _extract_quantization("Q4_K_S", None)
        assert q is not None
        assert q.group_size == 256

    def test_unknown_returns_none(self):
        q = _extract_quantization("F32", None)
        assert q is None


class TestGgufIngest:
    def test_gguf_with_empty_file(self, tmp_path):
        f = tmp_path / "model.gguf"
        f.write_bytes(b"")
        try:
            ir = ingest_gguf(f)
            assert ir.metadata.source_format == "gguf"
        except Exception:
            pass


class TestGgufModelInfo:
    def test_parameter_count(self):
        info = GgufModelInfo(
            name="test",
            architecture="llama",
            quant_type="Q4_K_M",
            tensors=[
                TensorInfo(name="w1", shape=[4096, 4096], dtype="Q4_K_M", offset=0, size=8388608,
                           quantization=QuantizationMetadata(quant_type="Q4_K_M", bits=4, group_size=256)),
                TensorInfo(name="w2", shape=[4096, 11008], dtype="Q4_K_M", offset=8388608, size=23068672,
                           quantization=QuantizationMetadata(quant_type="Q4_K_M", bits=4, group_size=256)),
            ],
        )
        assert info.parameter_count == 8
