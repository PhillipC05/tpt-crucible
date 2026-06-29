"""Tests for FPGA overlay, hot-swap, quant search, and accuracy regression."""

from pathlib import Path
import json

from tpt_fusion.overlay import (
    FuseCfg, OverlayManifest, OverlayCompiler, OverlayHotSwap, HbmSlot,
)
from tpt_catalyst.quant_search import QuantSearchEngine, QuantSearchResult, LayerQuantDecision
from tpt_catalyst.accuracy_regression import RegressionChecker, RegressionResult


class TestFuseCfg:
    def test_roundtrip_json(self):
        cfg = FuseCfg(datapath_width=8, layer_count=22, precision="int8")
        json_str = cfg.to_json()
        restored = FuseCfg.from_json(json_str)
        assert restored.datapath_width == 8
        assert restored.layer_count == 22

    def test_save_and_load(self, tmp_path):
        cfg = FuseCfg(model_name="test", precision="int4")
        path = tmp_path / "test.fusecfg"
        cfg.save(path)
        loaded = FuseCfg.load(path)
        assert loaded.model_name == "test"


class TestOverlayManifest:
    def test_compatibility_check(self):
        overlay = OverlayManifest(
            name="dense-int4", board="alveo_u250", datapath="dense",
            precision="int4|int8", max_layers=32, max_model_size_mb=4000,
        )
        compatible = FuseCfg(precision="int8", layer_count=16)
        incompatible = FuseCfg(precision="int8", layer_count=64)
        assert overlay.is_compatible(compatible) is True
        assert overlay.is_compatible(incompatible) is False


class TestOverlayCompiler:
    def test_compile(self):
        compiler = OverlayCompiler()
        cfg = compiler.compile(ir_nodes=10, precision="int8")
        assert cfg.layer_count == 10
        assert cfg.datapath_width == 8

    def test_weight_binary(self):
        compiler = OverlayCompiler()
        binary = compiler.generate_weight_binary([0.1, 0.5, 0.9], precision=8)
        assert len(binary) == 3


class TestOverlayHotSwap:
    def test_load_model(self):
        swap = OverlayHotSwap(cache_slots=4)
        cfg = FuseCfg()
        success, msg = swap.load_model("model_a", cfg, 100.0)
        assert success
        assert "slot 0" in msg

    def test_cache_hit(self):
        swap = OverlayHotSwap(cache_slots=4)
        cfg = FuseCfg()
        swap.load_model("model_a", cfg, 100.0)
        success, msg = swap.load_model("model_a", cfg, 100.0)
        assert success
        assert "Cache hit" in msg

    def test_eviction(self):
        swap = OverlayHotSwap(cache_slots=2)
        cfg = FuseCfg()
        swap.load_model("a", cfg, 100.0)
        swap.load_model("b", cfg, 100.0)
        swap.load_model("c", cfg, 100.0)
        cache = swap.list_cache()
        assert len(cache) == 2

    def test_evict_model(self):
        swap = OverlayHotSwap(cache_slots=4)
        cfg = FuseCfg()
        swap.load_model("a", cfg, 100.0)
        assert swap.evict_model("a") is True
        assert swap.evict_model("a") is False


class TestQuantSearch:
    def test_search(self):
        engine = QuantSearchEngine(accuracy_budget=0.05)
        result = engine.search(
            layer_names=["l0", "l1", "l2", "l3"],
            sensitivities=[0.9, 0.6, 0.3, 0.1],
        )
        assert len(result.decisions) == 4
        assert result.decisions[0].bits == 32
        assert result.decisions[-1].bits == 4

    def test_budget_constraint(self):
        engine = QuantSearchEngine(accuracy_budget=0.01)
        result = engine.search(
            layer_names=["l0", "l1"],
            sensitivities=[0.3, 0.3],
        )
        assert all(d.bits >= 8 for d in result.decisions)

    def test_to_dict(self):
        engine = QuantSearchEngine()
        result = engine.search(["l0", "l1"], [0.5, 0.5])
        d = result.to_dict()
        assert "decisions" in d
        assert "compression_ratio" in d


class TestRegressionChecker:
    def test_check_improved(self):
        checker = RegressionChecker()
        result = checker.check_regression(0.80, 0.85)
        assert result.improved
        assert result.status == "improved"

    def test_check_regressed(self):
        checker = RegressionChecker(threshold=0.02)
        result = checker.check_regression(0.85, 0.80)
        assert result.regressed
        assert result.status == "regressed"

    def test_check_unchanged(self):
        checker = RegressionChecker()
        result = checker.check_regression(0.85, 0.85)
        assert not result.improved
        assert not result.regressed
        assert result.status == "unchanged"

    def test_record_and_history(self):
        checker = RegressionChecker()
        result = checker.check_regression(0.80, 0.85)
        checker.record_result("model_a", result)
        history = checker.get_history("model_a")
        assert len(history) == 1

    def test_find_baseline(self):
        checker = RegressionChecker()
        checker.record_result("m", checker.check_regression(0.80, 0.85))
        baseline = checker.find_baseline("m")
        assert baseline == 0.85
