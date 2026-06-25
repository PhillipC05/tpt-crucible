"""Tests for tpt-doctor and structured error handling."""

from tpt_catalyst.doctor import (
    ToolStatus, DoctorReport, check_tool, run_doctor,
)
from tpt_catalyst.errors import (
    StructuredError, classify_error, format_error_for_cli,
)


class TestToolStatus:
    def test_ok_status(self):
        status = ToolStatus(name="python", installed=True, version="3.11.0", status="ok")
        assert status.color == "green"

    def test_missing_status(self):
        status = ToolStatus(name="yosys", installed=False, status="missing")
        assert status.color == "red"


class TestDoctorReport:
    def test_readiness_score(self):
        report = DoctorReport(tools=[
            ToolStatus(name="a", installed=True, status="ok"),
            ToolStatus(name="b", installed=True, status="ok"),
            ToolStatus(name="c", installed=False, status="missing"),
        ])
        assert report.readiness_score == 2 / 3

    def test_overall_status(self):
        report = DoctorReport(tools=[
            ToolStatus(name="a", installed=True, status="ok"),
            ToolStatus(name="b", installed=True, status="ok"),
        ])
        assert report.overall_status == "ready"

    def test_to_dict(self):
        report = DoctorReport(tools=[
            ToolStatus(name="python", installed=True, version="3.11", status="ok"),
        ])
        d = report.to_dict()
        assert "readiness_score" in d
        assert len(d["tools"]) == 1


class TestRunDoctor:
    def test_check_python(self):
        status = check_tool({"name": "python", "cmd": ["python", "--version"], "target": "all", "install": ""})
        assert status.installed
        assert status.status == "ok"

    def test_check_missing_tool(self):
        status = check_tool({"name": "nonexistent_tool_xyz", "cmd": ["nonexistent_tool_xyz", "--version"], "target": "all", "install": ""})
        assert not status.installed
        assert status.status == "missing"

    def test_run_doctor_all(self):
        report = run_doctor()
        assert len(report.tools) > 0
        assert report.readiness_score >= 0


class TestStructuredError:
    def test_to_dict(self):
        err = StructuredError(
            tool="yosys", error_type="timing_failure",
            message="Timing failed", suggested_action="Reduce clock",
        )
        d = err.to_dict()
        assert d["tool"] == "yosys"
        assert d["error_type"] == "timing_failure"


class TestClassifyError:
    def test_yosys_timing(self):
        stderr = "ERROR: timing analysis failed for module top"
        err = classify_error("yosys", stderr)
        assert err.error_type == "timing_failure"

    def test_platformio_board(self):
        stderr = "Error: board esp32dev not found in platformio"
        err = classify_error("platformio", stderr)
        assert err.error_type == "board_not_found"

    def test_unknown_error(self):
        stderr = "some random error message"
        err = classify_error("unknown_tool", stderr)
        assert err.error_type == "unknown"

    def test_format_for_cli(self):
        err = StructuredError(
            tool="yosys", error_type="timing",
            message="Timing failed", suggested_action="Reduce clock",
        )
        formatted = format_error_for_cli(err)
        assert "yosys" in formatted
        assert "Reduce clock" in formatted
