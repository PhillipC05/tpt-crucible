"""Tests for power estimator, OTA CLI, and validate CLI."""

from pathlib import Path
import json

from tpt_drivers.power_estimator import PowerEstimator, PowerEstimate
from tpt_alloy.ota_cli import generate_ota_command
from tpt_catalyst.validate_cli import run_validation


class TestPowerEstimator:
    def test_estimate(self):
        estimator = PowerEstimator()
        est = estimator.estimate(
            target="alloy",
            idle_mw=500, active_mw=2000, peak_mw=5000,
            node_count=16,
        )
        assert est.total_active_w > 0
        assert est.tier == "medium"

    def test_estimate_swarm(self):
        estimator = PowerEstimator()
        est = estimator.estimate_swarm(node_power_mw=200, node_count=16)
        assert est.node_count == 16
        assert est.total_active_w > 0

    def test_cost_estimation(self):
        est = PowerEstimate(
            target="alloy", idle_mw=50, active_mw=200, peak_mw=500,
            node_count=16,
        )
        cost = est.estimate_cost_usd(hours=24, rate_kwh=0.12)
        assert cost > 0

    def test_tier_classification(self):
        cheap = PowerEstimate(target="a", idle_mw=100, active_mw=200, peak_mw=500, node_count=10)
        medium = PowerEstimate(target="b", idle_mw=100, active_mw=200, peak_mw=500, node_count=50)
        expensive = PowerEstimate(target="c", idle_mw=100, active_mw=200, peak_mw=500, node_count=500)
        assert cheap.tier == "cheap"
        assert medium.tier == "medium"
        assert expensive.tier == "expensive"

    def test_to_dict(self):
        est = PowerEstimate(target="alloy", idle_mw=50, active_mw=200, peak_mw=500, node_count=4)
        d = est.to_dict()
        assert "active_w" in d
        assert "tier" in d


class TestOtaCli:
    def test_generate_ota_command(self, tmp_path):
        new_pkg = tmp_path / "new.tptpkg"
        new_pkg.mkdir()
        prev_pkg = tmp_path / "old.tptpkg"
        prev_pkg.mkdir()
        topo = tmp_path / "topology.json"
        topo.write_text(json.dumps({"node_count": 4}))

        script_path = generate_ota_command(new_pkg, prev_pkg, topo, tmp_path / "ota")
        assert Path(script_path).exists()
        content = Path(script_path).read_text()
        assert "node 0" in content
        assert "node 3" in content


class TestValidateCli:
    def test_run_validation(self, tmp_path):
        pkg = tmp_path / "model.tptpkg"
        pkg.mkdir()
        result = run_validation(pkg, reference="spark", hardware="alloy")
        assert "overall_similarity" in result
        assert result["grade"] in ("A", "B", "C")
        assert result["prompts_tested"] == 5

    def test_validation_output(self, tmp_path):
        pkg = tmp_path / "model.tptpkg"
        pkg.mkdir()
        output = tmp_path / "result.json"
        run_validation(pkg, output_path=output)
        assert output.exists()
        data = json.loads(output.read_text())
        assert "overall_similarity" in data
