"""Tests for telemetry adapters and remaining gap features."""

from pathlib import Path
from tpt_fusion.telemetry_adapter import FpgaTelemetryAdapter
from tpt_element.telemetry_adapter import AnalogTelemetryAdapter
from tpt_alloy.telemetry_adapter import SwarmTelemetryAdapter


class TestFpgaTelemetryAdapter:
    def test_sample(self):
        adapter = FpgaTelemetryAdapter()
        point = adapter.sample()
        assert point.clock_mhz == 200.0
        assert point.timestamp > 0

    def test_summary(self):
        adapter = FpgaTelemetryAdapter()
        adapter.sample()
        adapter.sample()
        s = adapter.get_summary()
        assert s["total_samples"] == 2


class TestAnalogTelemetryAdapter:
    def test_sample(self):
        adapter = AnalogTelemetryAdapter(node_count=4)
        points = adapter.sample()
        assert len(points) == 4
        assert points[0].voltage_v == 3.3

    def test_drift_over_time(self):
        adapter = AnalogTelemetryAdapter(node_count=2)
        adapter.sample()
        drift = adapter.get_drift_over_time("analog_0")
        assert len(drift) >= 1


class TestSwarmTelemetryAdapter:
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


class TestReplayOverlay:
    def test_component_exists(self):
        from tpt_catalyst.tptlog import TptLogWriter, TptLogReader
        writer = TptLogWriter(Path("/tmp/test.tptlog"))
        writer.record("fpga", "core_0", {"tps": 100})
        writer.save()
        reader = TptLogReader(Path("/tmp/test.tptlog"))
        reader.load()
        assert len(reader.entries) == 1
