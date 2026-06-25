"""Analog telemetry adapter — thermal drift monitoring over time."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import time


@dataclass
class AnalogTelemetryPoint:
    timestamp: float
    node_id: str
    temperature_c: float
    thermal_drift_pct: float
    voltage_v: float
    confidence_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "node_id": self.node_id,
            "temperature_c": self.temperature_c,
            "thermal_drift_pct": self.thermal_drift_pct,
            "voltage_v": self.voltage_v,
            "confidence_score": self.confidence_score,
        }


class AnalogTelemetryAdapter:
    """Collects and reports analog-specific telemetry metrics."""

    def __init__(self, node_count: int = 4):
        self.node_count = node_count
        self.log: list[AnalogTelemetryPoint] = []

    def sample(self) -> list[AnalogTelemetryPoint]:
        points = []
        for i in range(self.node_count):
            point = AnalogTelemetryPoint(
                timestamp=time.time(),
                node_id=f"analog_{i}",
                temperature_c=25.0,
                thermal_drift_pct=0.0,
                voltage_v=3.3,
                confidence_score=1.0,
            )
            self.log.append(point)
            points.append(point)
        return points

    def get_drift_over_time(self, node_id: str | None = None) -> list[dict]:
        entries = self.log
        if node_id:
            entries = [p for p in entries if p.node_id == node_id]
        return [{"timestamp": p.timestamp, "drift_pct": p.thermal_drift_pct} for p in entries]
