"""Swarm Telemetry Adapter — per-node latency monitoring."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import time


@dataclass
class SwarmTelemetryPoint:
    timestamp: float
    node_id: str
    latency_ms: float
    memory_usage_kb: float
    cpu_utilization: float
    message_rate: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "node_id": self.node_id,
            "latency_ms": round(self.latency_ms, 2),
            "memory_usage_kb": round(self.memory_usage_kb, 1),
            "cpu_utilization": round(self.cpu_utilization, 2),
            "message_rate": round(self.message_rate, 1),
        }


class SwarmTelemetryAdapter:
    """Collect and report swarm-specific telemetry metrics."""

    def __init__(self, node_count: int = 16):
        self.node_count = node_count
        self.log: list[SwarmTelemetryPoint] = []

    def sample(self) -> list[SwarmTelemetryPoint]:
        points = []
        for i in range(self.node_count):
            point = SwarmTelemetryPoint(
                timestamp=time.time(),
                node_id=f"node_{i}",
                latency_ms=0.0,
                memory_usage_kb=0.0,
                cpu_utilization=0.0,
                message_rate=0.0,
            )
            self.log.append(point)
            points.append(point)
        return points

    def get_latency_heatmap(self) -> dict[str, list[float]]:
        heatmap: dict[str, list[float]] = {}
        for p in self.log:
            if p.node_id not in heatmap:
                heatmap[p.node_id] = []
            heatmap[p.node_id].append(p.latency_ms)
        return heatmap
