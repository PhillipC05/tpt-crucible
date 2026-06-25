"""Tests for .tptpkg report writers."""

from pathlib import Path

from tpt_catalyst.compat import CompatibilityReport, OpCompatibility, HardwareTarget, Severity
from tpt_catalyst.quantize import QuantizationProfile, QuantTarget
from tpt_catalyst.package_reports import (
    write_preflight_report,
    write_quant_profile,
    write_mosaic_partition,
)


class TestWritePreflightReport:
    def test_writes_report(self, tmp_path):
        report = CompatibilityReport()
        report.results.append(OpCompatibility(
            op_type="matmul", target=HardwareTarget.FUSION,
            severity=Severity.PASS, message="OK",
        ))
        path = write_preflight_report(report, tmp_path)
        assert path.exists()
        import json
        data = json.loads(path.read_text())
        assert data["score"] == 1.0


class TestWriteQuantProfile:
    def test_writes_profile(self, tmp_path):
        profile = QuantizationProfile(
            name="FPGA INT8", target=QuantTarget.FUSION_INT8,
            weight_bits=8, activation_bits=8, accumulator_bits=32,
            estimated_accuracy_loss=0.01, estimated_speedup=4.0, memory_reduction=0.25,
        )
        path = write_quant_profile(profile, tmp_path)
        assert path.exists()
        import json
        data = json.loads(path.read_text())
        assert data["weight_bits"] == 8


class TestWriteMosaicPartition:
    def test_writes_partition(self, tmp_path):
        plan = {
            "assignments": [{"layer_id": 0, "target": "fpga"}],
            "targets_used": ["fpga"],
        }
        path = write_mosaic_partition(plan, tmp_path)
        assert path.exists()
        import json
        data = json.loads(path.read_text())
        assert len(data["assignments"]) == 1
