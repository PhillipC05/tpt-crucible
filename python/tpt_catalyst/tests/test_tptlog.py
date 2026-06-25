"""Tests for .tptlog telemetry replay format."""

from tpt_catalyst.tptlog import (
    TptLogWriter,
    TptLogReader,
    TptLogEntry,
    TptLogHeader,
)


class TestTptLogEntry:
    def test_roundtrip_bytes(self):
        entry = TptLogEntry(
            timestamp_ms=1000,
            hardware_type="fpga",
            node_id="core_0",
            metrics={"tps": 120.5, "util": 85.0},
        )
        data = entry.to_bytes()
        restored, offset = TptLogEntry.from_bytes(data)
        assert restored.timestamp_ms == 1000
        assert restored.hardware_type == "fpga"
        assert restored.metrics["tps"] == 120.5


class TestTptLogWriterReader:
    def test_write_and_read(self, tmp_path):
        log_path = tmp_path / "test.tptlog"
        writer = TptLogWriter(log_path, metadata={"model": "llama3"})
        writer.record("fpga", "core_0", {"tps": 100.0})
        writer.record("swarm", "node_1", {"latency_ms": 5.2})
        writer.save()

        reader = TptLogReader(log_path)
        reader.load()
        assert len(reader.entries) == 2
        assert reader.header.metadata["model"] == "llama3"

    def test_filter_by_hardware(self, tmp_path):
        log_path = tmp_path / "test.tptlog"
        writer = TptLogWriter(log_path)
        writer.record("fpga", "core_0", {"tps": 100.0})
        writer.record("swarm", "node_1", {"latency": 5.0})
        writer.record("fpga", "core_1", {"tps": 200.0})
        writer.save()

        reader = TptLogReader(log_path)
        reader.load()
        fpga = reader.get_entries(hardware_type="fpga")
        assert len(fpga) == 2

    def test_summary(self, tmp_path):
        log_path = tmp_path / "test.tptlog"
        writer = TptLogWriter(log_path)
        writer.record("fpga", "core_0", {"tps": 100.0})
        writer.save()

        reader = TptLogReader(log_path)
        reader.load()
        s = reader.summary()
        assert s["entry_count"] == 1
        assert "fpga" in s["hardware_types"]
