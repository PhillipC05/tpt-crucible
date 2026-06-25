"""Tests for HuggingFace search and streaming pre-flight."""

from pathlib import Path

from tpt_catalyst.hf_search import HuggingFaceSearch, HfModel
from tpt_catalyst.streaming_preflight import (
    stream_preflight, apply_fix, PreflightEvent,
)
from tpt_catalyst.ir import TptIr, OpNode, ComputationalGraph, ModelMetadata
from tpt_catalyst.compat import HardwareTarget


class TestHfModel:
    def test_to_dict(self):
        model = HfModel(
            model_id="test/model", name="model", author="test",
            downloads=100, quant_type="Q4_K_M",
        )
        d = model.to_dict()
        assert d["model_id"] == "test/model"
        assert d["quant_type"] == "Q4_K_M"


class TestHuggingFaceSearch:
    def test_fallback_search(self, tmp_path):
        search = HuggingFaceSearch(cache_dir=tmp_path / "cache")
        results = search._fallback_search("tiny", limit=5)
        assert len(results) >= 1
        assert any("TinyLlama" in m.model_id for m in results)

    def test_search_with_cache(self, tmp_path):
        search = HuggingFaceSearch(cache_dir=tmp_path / "cache")
        results1 = search._fallback_search("llama", limit=3)
        search._cache["test:3:None:None"] = [m.to_dict() for m in results1]
        search._save_cache()
        search._load_cache()
        assert "test:3:None:None" in search._cache

    def test_popular(self, tmp_path):
        search = HuggingFaceSearch(cache_dir=tmp_path / "cache")
        popular = search.get_popular(limit=3)
        assert len(popular) <= 3


def _make_test_ir() -> TptIr:
    return TptIr(
        version="1.0.0",
        metadata=ModelMetadata(name="test", source_format="pytorch"),
        graph=ComputationalGraph(
            nodes=[
                OpNode(id=0, op_type="matmul", name="layer0"),
                OpNode(id=1, op_type="relu", name="act0"),
                OpNode(id=2, op_type="softmax", name="out"),
            ],
            edges=[],
        ),
    )


class TestStreamingPreflight:
    def test_yields_events(self):
        ir = _make_test_ir()
        events = list(stream_preflight(ir, HardwareTarget.FUSION))
        assert len(events) >= 4
        assert events[0].event_type == "start"
        assert events[-1].event_type == "complete"

    def test_progress_increases(self):
        ir = _make_test_ir()
        events = list(stream_preflight(ir, HardwareTarget.ALLOY))
        progresses = [e.progress for e in events]
        assert progresses == sorted(progresses)

    def test_preflight_event_to_dict(self):
        event = PreflightEvent(
            event_type="result", node_id=0, op_type="matmul",
            severity="pass", message="OK", progress=0.5,
        )
        d = event.to_dict()
        assert d["op_type"] == "matmul"
        assert d["progress"] == 0.5


class TestApplyFix:
    def test_substitute_op(self):
        ir = _make_test_ir()
        ir.graph.nodes[2].op_type = "attention"
        fixed = apply_fix(ir, 2, "flash_attention_to_mha")
        assert fixed.graph.nodes[2].op_type == "mha"

    def test_noop_on_unknown_fix(self):
        ir = _make_test_ir()
        original_type = ir.graph.nodes[0].op_type
        fixed = apply_fix(ir, 0, "nonexistent_fix")
        assert fixed.graph.nodes[0].op_type == original_type
