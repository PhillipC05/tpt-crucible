"""Analog Telemetry Adapter — thermal drift monitoring over time."""

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
            "temperature_c": round(self.temperature_c, 1),
            "thermal_drift_pct": round(self.thermal_drift_pct, 4),
            "voltage_v": round(self.voltage_v, 3),
            "confidence_score": round(self.confidence_score, 4),
        }


class AnalogTelemetryAdapter:
    """Collect and report analog-specific telemetry metrics."""

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
