"""Power Consumption Estimator — compute and monitor power draw."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PowerEstimate:
    target: str
    idle_mw: float
    active_mw: float
    peak_mw: float
    node_count: int
    overhead_factor: float = 1.15
    efficiency_pct: float = 85.0

    @property
    def total_idle_w(self) -> float:
        return (self.idle_mw * self.node_count * self.overhead_factor) / 1000

    @property
    def total_active_w(self) -> float:
        return (self.active_mw * self.node_count * self.overhead_factor) / 1000

    @property
    def total_peak_w(self) -> float:
        return (self.peak_mw * self.node_count * self.overhead_factor) / 1000

    @property
    def tier(self) -> str:
        if self.total_active_w < 5:
            return "cheap"
        elif self.total_active_w < 50:
            return "medium"
        return "expensive"

    def estimate_cost_usd(self, hours: float = 24.0, rate_kwh: float = 0.12) -> float:
        kwh = (self.total_active_w * hours) / 1000
        return round(kwh * rate_kwh, 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "idle_w": round(self.total_idle_w, 2),
            "active_w": round(self.total_active_w, 2),
            "peak_w": round(self.total_peak_w, 2),
            "node_count": self.node_count,
            "tier": self.tier,
            "cost_24h_usd": self.estimate_cost_usd(),
        }


class PowerEstimator:
    """Estimate total power consumption for a deployment."""

    def __init__(self, overhead_factor: float = 1.15):
        self.overhead_factor = overhead_factor

    def estimate(
        self,
        target: str,
        idle_mw: float,
        active_mw: float,
        peak_mw: float,
        node_count: int,
    ) -> PowerEstimate:
        return PowerEstimate(
            target=target,
            idle_mw=idle_mw,
            active_mw=active_mw,
            peak_mw=peak_mw,
            node_count=node_count,
            overhead_factor=self.overhead_factor,
        )

    def estimate_swarm(
        self,
        node_power_mw: float,
        node_count: int,
        target: str = "alloy",
    ) -> PowerEstimate:
        return PowerEstimate(
            target=target,
            idle_mw=node_power_mw * 0.3,
            active_mw=node_power_mw,
            peak_mw=node_power_mw * 1.5,
            node_count=node_count,
            overhead_factor=self.overhead_factor,
        )
