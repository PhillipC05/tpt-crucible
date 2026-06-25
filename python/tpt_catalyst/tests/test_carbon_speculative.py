"""Tests for carbon, speculative decoding, IP lock, and sparsity."""

import numpy as np

from tpt_catalyst.carbon import (
    estimate_carbon, select_lowest_carbon_target, compare_targets,
    CarbonEstimate, GRID_INTENSITY_GCO2_PER_KWH,
)
from tpt_mosaic.speculative import (
    SpeculativeConfig, SpeculativeOrchestrator, SpeculativeMetrics,
)
from tpt_catalyst.ip_lock import (
    HardwareLock, create_lock, verify_lock, fingerprint_hardware,
)
from tpt_catalyst.sparsity import (
    SparsityMode, SparsityPattern, SparsityAnalyzer,
)


class TestCarbonEstimate:
    def test_estimate_carbon(self):
        est = estimate_carbon(
            target="alloy",
            power_watts=5.0,
            inference_time_s=1.0,
            region="us",
        )
        assert est.carbon_gco2 > 0
        assert est.energy_wh > 0
        assert est.cost_usd > 0

    def test_select_lowest(self):
        estimates = [
            estimate_carbon("alloy", 5.0, 1.0, "us"),
            estimate_carbon("fusion", 100.0, 1.0, "eu-no"),
        ]
        lowest = select_lowest_carbon_target(estimates)
        assert lowest is not None
        assert lowest.target == "fusion"

    def test_compare_targets(self):
        targets = [
            {"name": "alloy", "power_watts": 5.0},
            {"name": "fusion", "power_watts": 100.0},
        ]
        results = compare_targets(targets, inference_time_s=1.0, region="eu")
        assert len(results) == 2

    def test_grid_intensity(self):
        assert "us" in GRID_INTENSITY_GCO2_PER_KWH
        assert "eu" in GRID_INTENSITY_GCO2_PER_KWH


class TestSpeculativeDecoding:
    def test_run_speculative(self):
        config = SpeculativeConfig(draft_pkg="a", verify_pkg="b", gamma=4)
        orchestrator = SpeculativeOrchestrator(config)
        result = orchestrator.run_speculative([1, 2, 3], max_new_tokens=10)
        assert len(result) > 0
        assert orchestrator.metrics.total_tokens > 0

    def test_metrics(self):
        config = SpeculativeConfig(gamma=2)
        orch = SpeculativeOrchestrator(config)
        orch.run_speculative([1], max_new_tokens=5)
        metrics = orch.get_metrics()
        assert metrics.acceptance_rate >= 0
        d = metrics.to_dict()
        assert "acceptance_rate" in d


class TestIpLock:
    def test_create_lock(self):
        lock = create_lock(["hw_001", "hw_002"])
        assert len(lock.allowed_ids) == 2
        assert len(lock.fingerprint_sha256) == 64

    def test_verify_lock_pass(self):
        lock = create_lock(["hw_001", "hw_002"])
        assert verify_lock(lock, ["hw_001", "hw_002"]) is True

    def test_verify_lock_fail(self):
        lock = create_lock(["hw_001"])
        assert verify_lock(lock, ["hw_001", "hw_999"]) is False

    def test_empty_lock_always_passes(self):
        lock = HardwareLock(fingerprint_sha256="abc", allowed_ids=[])
        assert verify_lock(lock, ["anything"]) is True

    def test_fingerprint_hardware(self):
        fp = fingerprint_hardware({"serial": "abc", "model": "esp32"})
        assert len(fp) == 64


class TestSparsity:
    def test_analyze_dense(self):
        analyzer = SparsityAnalyzer()
        weights = np.ones((4, 4))
        pattern = analyzer.analyze(weights)
        assert pattern.mode == SparsityMode.NONE

    def test_enforce_2_4(self):
        analyzer = SparsityAnalyzer()
        weights = np.random.rand(4, 16)
        sparse, indices = analyzer.enforce_2_4(weights)
        non_zero_per_row = [np.count_nonzero(sparse[i]) for i in range(4)]
        assert all(n <= 2 for n in non_zero_per_row)

    def test_enforce_4_8(self):
        analyzer = SparsityAnalyzer()
        weights = np.random.rand(4, 16)
        sparse, indices = analyzer.enforce_4_8(weights)
        non_zero_per_row = [np.count_nonzero(sparse[i]) for i in range(4)]
        assert all(n <= 4 for n in non_zero_per_row)

    def test_speedup_estimate(self):
        analyzer = SparsityAnalyzer()
        pattern = SparsityPattern(mode=SparsityMode.TWO_FOUR, density=0.5)
        speedup = analyzer.estimate_speedup(pattern, 10.0)
        assert speedup == 2.0

    def test_pattern_to_dict(self):
        pattern = SparsityPattern(mode=SparsityMode.TWO_FOUR, density=0.5)
        d = pattern.to_dict()
        assert d["mode"] == "2:4"
