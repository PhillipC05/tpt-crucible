"""Structured error handling for toolchain errors."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import json
import re


@dataclass
class StructuredError:
    tool: str
    error_type: str
    message: str
    suggested_action: str
    raw_output: str = ""
    context: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "error_type": self.error_type,
            "message": self.message,
            "suggested_action": self.suggested_action,
            "raw_output": self.raw_output[:500],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


ERROR_CATALOG: list[dict[str, Any]] = [
    {
        "tool": "yosys",
        "pattern": r"ERROR:.*module.*not found",
        "error_type": "missing_module",
        "message": "A required module was not found during synthesis.",
        "suggested_action": "Check that all required Verilog modules are included in the source files.",
    },
    {
        "tool": "yosys",
        "pattern": r"ERROR:.*timing.*fail",
        "error_type": "timing_failure",
        "message": "Timing constraints could not be met.",
        "suggested_action": "Try reducing clock frequency or adding pipeline registers.",
    },
    {
        "tool": "yosys",
        "pattern": r"ERROR:.*resource.*overflow",
        "error_type": "resource_overflow",
        "message": "Design exceeds available FPGA resources.",
        "suggested_action": "Reduce MAC array size or use a larger FPGA board.",
    },
    {
        "tool": "nextpnr",
        "pattern": r"ERROR:.*failed to place",
        "error_type": "placement_failure",
        "message": "Could not place all logic cells on the FPGA.",
        "suggested_action": "Try a different routing seed or increase timing margin.",
    },
    {
        "tool": "nextpnr",
        "pattern": r"ERROR:.*timing.*unmet",
        "error_type": "timing_unmet",
        "message": "Post-place-and-route timing analysis shows unmet constraints.",
        "suggested_action": "Reduce clock frequency or optimize critical path.",
    },
    {
        "tool": "platformio",
        "pattern": r"Error:.*board.*not found",
        "error_type": "board_not_found",
        "message": "The specified board is not recognized by PlatformIO.",
        "suggested_action": "Check board name in platformio.ini. Run 'pio boards' to list supported boards.",
    },
    {
        "tool": "platformio",
        "pattern": r"Error:.*upload.*failed",
        "error_type": "upload_failed",
        "message": "Firmware upload to the microcontroller failed.",
        "suggested_action": "Check USB connection, ensure board is in flash mode, try different USB port.",
    },
    {
        "tool": "ngspice",
        "pattern": r"Error:.*convergence",
        "error_type": "convergence_failure",
        "message": "SPICE simulation failed to converge.",
        "suggested_action": "Check component values, reduce time step, or add series resistance.",
    },
    {
        "tool": "xyce",
        "pattern": r"ERROR:.*singular matrix",
        "error_type": "singular_matrix",
        "message": "SPICE matrix is singular — circuit may have floating nodes.",
        "suggested_action": "Ensure all nodes have a DC path to ground.",
    },
    {
        "tool": "verilator",
        "pattern": r"%Error:.*unsupported",
        "error_type": "unsupported_feature",
        "message": "Verilator does not support a language feature used in the Verilog.",
        "suggested_action": "Simplify Verilog or use Verilator-compatible constructs.",
    },
]


def classify_error(tool: str, stderr: str) -> StructuredError:
    for entry in ERROR_CATALOG:
        if entry["tool"] == tool or entry["tool"] == "all":
            if re.search(entry["pattern"], stderr, re.IGNORECASE):
                return StructuredError(
                    tool=tool,
                    error_type=entry["error_type"],
                    message=entry["message"],
                    suggested_action=entry["suggested_action"],
                    raw_output=stderr,
                )

    return StructuredError(
        tool=tool,
        error_type="unknown",
        message=stderr.strip().split("\n")[-1][:200] if stderr else "Unknown error",
        suggested_action="Check the raw output for details. If the issue persists, file a bug report.",
        raw_output=stderr,
    )


def format_error_for_cli(error: StructuredError) -> str:
    lines = [
        f"[{error.tool}] {error.error_type}: {error.message}",
        f"  Suggested: {error.suggested_action}",
    ]
    return "\n".join(lines)
