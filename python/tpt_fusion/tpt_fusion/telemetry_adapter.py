"""FPGA Telemetry Adapter — memory bandwidth utilization monitoring."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import time


@dataclass
class FpgaTelemetryPoint:
    timestamp: float
    memory_bandwidth_utilization: float
    dsp_utilization: float
    clock_mhz: float
    power_watts: float
    temperature_c: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "memory_bandwidth_utilization": round(self.memory_bandwidth_utilization, 2),
            "dsp_utilization": round(self.dsp_utilization, 2),
            "clock_mhz": self.clock_mhz,
            "power_watts": round(self.power_watts, 2),
            "temperature_c": round(self.temperature_c, 1),
        }


class FpgaTelemetryAdapter:
    """Collect and report FPGA-specific telemetry metrics."""

    def __init__(self, clock_mhz: float = 200.0, hbm_bandwidth_gbs: float = 460.0):
        self.clock_mhz = clock_mhz
        self.hbm_bandwidth_gbs = hbm_bandwidth_gbs
        self.log: list[FpgaTelemetryPoint] = []

    def sample(self) -> FpgaTelemetryPoint:
        point = FpgaTelemetryPoint(
            timestamp=time.time(),
            memory_bandwidth_utilization=0.0,
            dsp_utilization=0.0,
            clock_mhz=self.clock_mhz,
            power_watts=0.0,
            temperature_c=0.0,
        )
        self.log.append(point)
        return point

    def get_summary(self) -> dict[str, float]:
        if not self.log:
            return {}
        bw = [p.memory_bandwidth_utilization for p in self.log]
        return {
            "avg_bandwidth_util": sum(bw) / len(bw),
            "max_bandwidth_util": max(bw),
            "total_samples": len(self.log),
        }
