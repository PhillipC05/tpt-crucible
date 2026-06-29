"""SPICE Dataset Auto-Generation — parametric sweep for Reality Check training."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import itertools


@dataclass
class SweepConfig:
    tolerances: list[float] = field(default_factory=lambda: [0.01, 0.05, 0.10])
    temperature_range: tuple[float, float] = (-20.0, 85.0)
    temperature_steps: int = 5
    voltage_variance: float = 0.10
    voltage_steps: int = 3

    def get_param_grid(self) -> list[dict[str, float]]:
        temps = [
            self.temperature_range[0] + i * (self.temperature_range[1] - self.temperature_range[0]) / max(self.temperature_steps - 1, 1)
            for i in range(self.temperature_steps)
        ]
        voltages = [
            3.3 * (1 + (i - self.voltage_steps // 2) * self.voltage_variance / self.voltage_steps)
            for i in range(self.voltage_steps)
        ]

        grid = []
        for tol in self.tolerances:
            for temp in temps:
                for volt in voltages:
                    grid.append({
                        "tolerance": tol,
                        "temperature_c": temp,
                        "voltage_v": volt,
                    })
        return grid


@dataclass
class SweepResult:
    config: dict[str, float]
    output_voltage: float = 0.0
    power_mw: float = 0.0
    failure_mode: str = ""
    passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config,
            "output_voltage": round(self.output_voltage, 4),
            "power_mw": round(self.power_mw, 4),
            "failure_mode": self.failure_mode,
            "passed": self.passed,
        }


class SpiceSweepOrchestrator:
    """Orchestrate parametric SPICE simulation sweeps."""

    def __init__(self, config: SweepConfig | None = None):
        self.config = config or SweepConfig()
        self.results: list[SweepResult] = []

    def run_sweep(self, total_runs: int | None = None) -> list[SweepResult]:
        grid = self.config.get_param_grid()
        if total_runs:
            grid = grid[:total_runs]

        self.results = []
        for params in grid:
            result = self._simulate_single(params)
            self.results.append(result)

        return self.results

    def _simulate_single(self, params: dict[str, float]) -> SweepResult:
        tol = params["tolerance"]
        temp = params["temperature_c"]
        volt = params["voltage_v"]

        output_v = volt * (1 - tol * 0.5) * (1 - (temp - 25) * 0.001)
        power = (volt ** 2) / 1000.0 * (1 + tol)

        failure = ""
        if output_v < volt * 0.8:
            failure = "output_voltage_low"
        elif output_v > volt * 1.2:
            failure = "output_voltage_high"
        elif power > 10.0:
            failure = "power_exceeded"

        return SweepResult(
            config=params,
            output_voltage=output_v,
            power_mw=power * 1000,
            failure_mode=failure,
            passed=failure == "",
        )

    def get_failure_modes(self) -> dict[str, int]:
        modes: dict[str, int] = {}
        for r in self.results:
            if r.failure_mode:
                modes[r.failure_mode] = modes.get(r.failure_mode, 0) + 1
        return modes

    def get_pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)
