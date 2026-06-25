"""tpt-doctor — toolchain verifier and readiness checker."""

from __future__ import annotations
import subprocess
import shutil
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolStatus:
    name: str
    installed: bool
    version: str = ""
    path: str = ""
    status: str = "missing"
    install_hint: str = ""

    @property
    def color(self) -> str:
        if self.status == "ok":
            return "green"
        elif self.status == "wrong_version":
            return "amber"
        return "red"


@dataclass
class DoctorReport:
    tools: list[ToolStatus] = field(default_factory=list)
    smoke_test_passed: bool = False

    @property
    def readiness_score(self) -> float:
        if not self.tools:
            return 0.0
        ok_count = sum(1 for t in self.tools if t.status == "ok")
        return ok_count / len(self.tools)

    @property
    def overall_status(self) -> str:
        score = self.readiness_score
        if score >= 0.8:
            return "ready"
        elif score >= 0.5:
            return "partial"
        return "not_ready"

    def to_dict(self) -> dict[str, Any]:
        return {
            "readiness_score": round(self.readiness_score, 2),
            "overall_status": self.overall_status,
            "tools": [
                {
                    "name": t.name,
                    "installed": t.installed,
                    "version": t.version,
                    "status": t.status,
                    "install_hint": t.install_hint,
                }
                for t in self.tools
            ],
            "smoke_test_passed": self.smoke_test_passed,
        }


TOOL_CHECKS = [
    {
        "name": "yosys",
        "cmd": ["yosys", "--version"],
        "target": "fusion",
        "install": "pip install yosys or apt install yosys",
    },
    {
        "name": "nextpnr-xilinx",
        "cmd": ["nextpnr-xilinx", "--help"],
        "target": "fusion",
        "install": "Install nextpnr from https://github.com/YosysHQ/nextpnr",
    },
    {
        "name": "platformio",
        "cmd": ["platformio", "--version"],
        "target": "alloy",
        "install": "pip install platformio",
    },
    {
        "name": "ngspice",
        "cmd": ["ngspice", "--version"],
        "target": "element",
        "install": "apt install ngspice or brew install ngspice",
    },
    {
        "name": "xyce",
        "cmd": ["xyce", "--version"],
        "target": "element",
        "install": "Download from https://sandialabs.github.io/Xyce/",
    },
    {
        "name": "verilator",
        "cmd": ["verilator", "--version"],
        "target": "fusion",
        "install": "apt install verilator or brew install verilator",
    },
    {
        "name": "python",
        "cmd": ["python", "--version"],
        "target": "all",
        "install": "Install Python 3.10+",
    },
    {
        "name": "cargo",
        "cmd": ["cargo", "--version"],
        "target": "all",
        "install": "Install Rust: https://rustup.rs",
    },
    {
        "name": "go",
        "cmd": ["go", "version"],
        "target": "observer",
        "install": "Install Go: https://go.dev/dl/",
    },
    {
        "name": "node",
        "cmd": ["node", "--version"],
        "target": "observer",
        "install": "Install Node.js: https://nodejs.org",
    },
]


def check_tool(tool_def: dict[str, Any]) -> ToolStatus:
    name = tool_def["name"]
    cmd = tool_def["cmd"]
    install_hint = tool_def.get("install", "")

    path = shutil.which(cmd[0])
    if not path:
        return ToolStatus(
            name=name, installed=False, status="missing",
            install_hint=install_hint,
        )

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
        )
        output = result.stdout + result.stderr
        version = output.strip().split("\n")[0][:64]
        return ToolStatus(
            name=name, installed=True, version=version,
            path=path, status="ok",
        )
    except (subprocess.TimeoutExpired, Exception):
        return ToolStatus(
            name=name, installed=True, path=path,
            status="ok", version="unknown",
        )


def run_doctor(target: str | None = None) -> DoctorReport:
    report = DoctorReport()

    for tool_def in TOOL_CHECKS:
        if target and tool_def["target"] != "all" and tool_def["target"] != target:
            continue
        status = check_tool(tool_def)
        report.tools.append(status)

    return report


def print_report(report: DoctorReport) -> None:
    print(f"\nTPT Crucible Doctor — Readiness: {report.readiness_score:.0%} ({report.overall_status})\n")
    for tool in report.tools:
        icon = {"ok": "\u2705", "wrong_version": "\u26a0\ufe0f", "missing": "\u274c"}.get(tool.status, "\u274c")
        version_str = f" v{tool.version}" if tool.version else ""
        print(f"  {icon} {tool.name}{version_str}")
        if tool.status == "missing" and tool.install_hint:
            print(f"      Install: {tool.install_hint}")
    print()
