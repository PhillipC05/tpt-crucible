"""Tests for model ingestion into TPT-IR."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tpt_catalyst.ir import TptIr, OpNode, Edge, ComputationalGraph, ModelMetadata
from tpt_catalyst.ingest import ingest_model


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


class TestIngestModel:
    def test_unsupported_format(self, tmp_path):
        f = tmp_path / "model.xyz"
        f.write_text("dummy")
        with pytest.raises(ValueError, match="Unsupported"):
            ingest_model(f)

    def test_pytorch_fallback(self, tmp_path):
        f = tmp_path / "model.pt"
        f.write_text("dummy")
        with patch("tpt_catalyst.ingest._ingest_pytorch") as mock:
            mock.return_value = TptIr(
                version="1.0.0",
                metadata=ModelMetadata(name="model", source_format="pytorch"),
                graph=ComputationalGraph(),
            )
            ir = ingest_model(f)
            assert ir.metadata.source_format == "pytorch"

    def test_onnx_fallback(self, tmp_path):
        f = tmp_path / "model.onnx"
        f.write_text("dummy")
        with patch("tpt_catalyst.ingest._ingest_onnx") as mock:
            mock.return_value = TptIr(
                version="1.0.0",
                metadata=ModelMetadata(name="model", source_format="onnx"),
                graph=ComputationalGraph(),
            )
            ir = ingest_model(f)
            assert ir.metadata.source_format == "onnx"

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
