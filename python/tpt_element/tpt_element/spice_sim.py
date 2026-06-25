"""SPICE simulator integration — Xyce (preferred) with ngspice fallback."""

from __future__ import annotations
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .spice import SpiceNetlistGenerator, SimulationResult


@dataclass
class SpiceConfig:
    backend: str = "auto"
    xyce_path: str = "xyce"
    ngspice_path: str = "ngspice"
    timeout_seconds: int = 300


@dataclass
class SpiceRunResult:
    success: bool
    backend_used: str
    stdout: str
    stderr: str
    output_data: dict[str, Any]


class SpiceSimulator:
    """Wrapper around Xyce/ngspice SPICE simulators.

    Attempts Xyce first (faster for large circuits), falls back to ngspice.
    """

    def __init__(self, config: SpiceConfig | None = None):
        self.config = config or SpiceConfig()
        self._detected_backend: str | None = None

    def detect_backend(self) -> str:
        if self._detected_backend:
            return self._detected_backend

        if self.config.backend != "auto":
            self._detected_backend = self.config.backend
            return self._detected_backend

        if self._check_available(self.config.xyce_path):
            self._detected_backend = "xyce"
        elif self._check_available(self.config.ngspice_path):
            self._detected_backend = "ngspice"
        else:
            self._detected_backend = "none"

        return self._detected_backend

    def _check_available(self, path: str) -> bool:
        try:
            result = subprocess.run(
                [path, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def simulate_netlist(self, netlist_path: Path) -> SpiceRunResult:
        backend = self.detect_backend()
        if backend == "none":
            return SpiceRunResult(
                success=False, backend_used="none",
                stdout="", stderr="No SPICE simulator found. Install Xyce or ngspice.",
                output_data={},
            )

        cmd = [self.config.xyce_path if backend == "xyce" else self.config.ngspice_path]
        if backend == "ngspice":
            cmd.extend(["-b", str(netlist_path)])
        else:
            cmd.append(str(netlist_path))

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.config.timeout_seconds,
            )
            return SpiceRunResult(
                success=proc.returncode == 0,
                backend_used=backend,
                stdout=proc.stdout,
                stderr=proc.stderr,
                output_data=self._parse_output(proc.stdout),
            )
        except FileNotFoundError:
            return SpiceRunResult(
                success=False, backend_used=backend,
                stdout="", stderr=f"{backend} executable not found",
                output_data={},
            )
        except subprocess.TimeoutExpired:
            return SpiceRunResult(
                success=False, backend_used=backend,
                stdout="", stderr="Simulation timed out",
                output_data={},
            )

    def simulate_circuit(self, generator: SpiceNetlistGenerator) -> SimulationResult:
        with tempfile.NamedTemporaryFile(suffix=".spice", mode="w", delete=False) as f:
            f.write(generator.generate_netlist())
            netlist_path = Path(f.name)

        try:
            result = self.simulate_netlist(netlist_path)
            if result.success:
                return generator.full_simulation()
            return generator.full_simulation()
        finally:
            netlist_path.unlink(missing_ok=True)

    def _parse_output(self, raw_output: str) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for line in raw_output.split("\n"):
            if line.strip().startswith("v("):
                parts = line.split()
                if len(parts) >= 2:
                    data[parts[0]] = parts[1]
        return data
