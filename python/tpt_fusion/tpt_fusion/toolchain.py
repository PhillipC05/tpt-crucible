"""Yosys and Nextpnr CLI wrappers."""

from __future__ import annotations
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ToolResult:
    success: bool
    stdout: str
    stderr: str
    returncode: int


class YosysRunner:
    """Wrapper around Yosys logic synthesis."""

    def __init__(self, yosys_path: str = "yosys"):
        self.yosys_path = yosys_path

    def synthesize(self, verilog_path: Path, output_blif: Path) -> ToolResult:
        """Run Yosys synthesis on a Verilog file."""
        cmd = [
            self.yosys_path,
            "-p", f"read_verilog {verilog_path}; synth_xilinx -blif {output_blif}",
            "-o", str(output_blif),
        ]
        return self._run(cmd)

    def check_available(self) -> bool:
        """Check if Yosys is installed."""
        result = self._run([self.yosys_path, "--version"])
        return result.success

    def _run(self, cmd: list[str]) -> ToolResult:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            return ToolResult(
                success=proc.returncode == 0,
                stdout=proc.stdout,
                stderr=proc.stderr,
                returncode=proc.returncode,
            )
        except FileNotFoundError:
            return ToolResult(
                success=False,
                stdout="",
                stderr=f"{cmd[0]} not found. Install Yosys first.",
                returncode=-1,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                stdout="",
                stderr="Yosys synthesis timed out",
                returncode=-2,
            )


class NextpnrRunner:
    """Wrapper around Nextpnr place-and-route."""

    def __init__(self, nextpnr_path: str = "nextpnr-xilinx"):
        self.nextpnr_path = nextpnr_path

    def place_and_route(
        self, blif_path: Path, output_bitstream: Path, board_fpga: str
    ) -> ToolResult:
        """Run Nextpnr place-and-route."""
        cmd = [
            self.nextpnr_path,
            "--blif", str(blif_path),
            "--board", board_fpga,
            "--output", str(output_bitstream),
        ]
        return self._run(cmd)

    def check_available(self) -> bool:
        """Check if Nextpnr is installed."""
        result = self._run([self.nextpnr_path, "--help"])
        return result.success

    def _run(self, cmd: list[str]) -> ToolResult:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )
            return ToolResult(
                success=proc.returncode == 0,
                stdout=proc.stdout,
                stderr=proc.stderr,
                returncode=proc.returncode,
            )
        except FileNotFoundError:
            return ToolResult(
                success=False,
                stdout="",
                stderr=f"{cmd[0]} not found. Install Nextpnr first.",
                returncode=-1,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                stdout="",
                stderr="Nextpnr timed out",
                returncode=-2,
            )
