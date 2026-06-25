"""Tests for hardware telemetry adapters."""

from tpt_fusion.telemetry import FpgaTelemetryAdapter
from tpt_element.telemetry import AnalogTelemetryAdapter
from tpt_alloy.telemetry import SwarmTelemetryAdapter


class TestFpgaTelemetry:
    def test_sample(self):
        adapter = FpgaTelemetryAdapter()
        point = adapter.sample()
        assert point.clock_mhz == 200.0

    def test_summary(self):
        adapter = FpgaTelemetryAdapter()
        adapter.sample()
        adapter.sample()
        s = adapter.get_summary()
        assert s["total_samples"] == 2

    def test_to_dict(self):
        adapter = FpgaTelemetryAdapter()
        point = adapter.sample()
        d = point.to_dict()
        assert "clock_mhz" in d


class TestAnalogTelemetry:
    def test_sample(self):
        adapter = AnalogTelemetryAdapter(node_count=4)
        points = adapter.sample()
        assert len(points) == 4

    def test_drift_over_time(self):
        adapter = AnalogTelemetryAdapter(node_count=2)
        adapter.sample()
        drift = adapter.get_drift_over_time("analog_0")
        assert len(drift) >= 1


class TestSwarmTelemetry:
    def test_sample(self):
        adapter = SwarmTelemetryAdapter(node_count=8)
        points = adapter.sample()
        assert len(points) == 8

    def test_latency_heatmap(self):
        adapter = SwarmTelemetryAdapter(node_count=4)
        adapter.sample()
        heatmap = adapter.get_latency_heatmap()
        assert len(heatmap) == 4
        assert all(len(v) >= 1 for v in heatmap.values())
