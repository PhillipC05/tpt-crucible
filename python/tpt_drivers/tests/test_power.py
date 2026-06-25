"""Tests for power consumption estimator."""

from tpt_drivers.driver import DriverManifest, PowerProfile, SynthesisConstraints, BomEntry
from tpt_drivers.power_estimator import PowerEstimator, PowerEstimate


def _make_manifest(name: str, idle: float, active: float, peak: float) -> DriverManifest:
    return DriverManifest(
        name=name, version="1.0.0", hardware_type="fpga",
        power=PowerProfile(idle_mw=idle, active_mw=active, peak_mw=peak),
    )


class TestPowerEstimate:
    def test_to_dict(self):
        est = PowerEstimate(
            total_idle_mw=100, total_active_mw=200, total_peak_mw=500,
            per_node_active_mw=50,
        )
        d = est.to_dict()
        assert d["idle_w"] == 0.1
        assert d["active_w"] == 0.2

    def test_estimate_cost(self):
        est = PowerEstimate(
            total_idle_mw=100, total_active_mw=200, total_peak_mw=500,
            per_node_active_mw=50,
        )
        cost = est.estimate_cost_usd(hours=24, rate_kwh=0.12)
        assert cost > 0

    def test_tier_badge(self):
        cheap = PowerEstimate(total_idle_mw=0, total_active_mw=5000, total_peak_mw=0, per_node_active_mw=0)
        assert cheap.tier_badge() == "cheap"

        medium = PowerEstimate(total_idle_mw=0, total_active_mw=50000, total_peak_mw=0, per_node_active_mw=0)
        assert medium.tier_badge() == "medium"

        expensive = PowerEstimate(total_idle_mw=0, total_active_mw=500000, total_peak_mw=0, per_node_active_mw=0)
        assert expensive.tier_badge() == "expensive"


class TestPowerEstimator:
    def test_single_manifest(self):
        estimator = PowerEstimator()
        manifest = _make_manifest("esp32", idle=50, active=200, peak=500)
        est = estimator.estimate([manifest])
        assert est.total_active_mw > 200

    def test_multi_node(self):
        estimator = PowerEstimator()
        manifest = _make_manifest("esp32", idle=50, active=200, peak=500)
        est = estimator.estimate_for_swarm(manifest, node_count=16)
        assert est.total_active_mw > 3000

    def test_overhead_factor(self):
        estimator = PowerEstimator(overhead_factor=1.0)
        manifest = _make_manifest("test", idle=100, active=100, peak=100)
        est = estimator.estimate([manifest])
        assert est.total_active_mw == 100.0
