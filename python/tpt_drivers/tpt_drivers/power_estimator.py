"""Power consumption estimator — compute and estimate power draw."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from .driver import DriverManifest, PowerProfile


@dataclass
class PowerEstimate:
    total_idle_mw: float
    total_active_mw: float
    total_peak_mw: float
    per_node_active_mw: float
    overhead_factor: float = 1.15
    efficiency_pct: float = 85.0

    @property
    def total_idle_w(self) -> float:
        return self.total_idle_mw / 1000

    @property
    def total_active_w(self) -> float:
        return self.total_active_mw / 1000

    @property
    def total_peak_w(self) -> float:
        return self.total_peak_mw / 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "idle_mw": round(self.total_idle_mw, 2),
            "active_mw": round(self.total_active_mw, 2),
            "peak_mw": round(self.total_peak_mw, 2),
            "idle_w": round(self.total_idle_w, 2),
            "active_w": round(self.total_active_w, 2),
            "peak_w": round(self.total_peak_w, 2),
            "per_node_active_mw": round(self.per_node_active_mw, 2),
            "overhead_factor": self.overhead_factor,
            "efficiency_pct": self.efficiency_pct,
        }

    def estimate_cost_usd(self, hours: float = 24.0, rate_kwh: float = 0.12) -> float:
        kwh = (self.total_active_w * hours) / 1000
        return round(kwh * rate_kwh, 4)

    def tier_badge(self) -> str:
        active_w = self.total_active_w
        if active_w < 10:
            return "cheap"
        elif active_w < 100:
            return "medium"
        return "expensive"


class PowerEstimator:
    """Estimate total power consumption for a deployment."""

    def __init__(self, overhead_factor: float = 1.15):
        self.overhead_factor = overhead_factor

    def estimate(
        self,
        manifests: list[DriverManifest],
        node_counts: list[int] | None = None,
    ) -> PowerEstimate:
        if node_counts is None:
            node_counts = [1] * len(manifests)

        total_idle = 0.0
        total_active = 0.0
        total_peak = 0.0
        total_nodes = 0

        for manifest, count in zip(manifests, node_counts):
            pw = manifest.power
            total_idle += pw.idle_mw * count
            total_active += pw.active_mw * count
            total_peak += pw.peak_mw * count
            total_nodes += count

        total_idle *= self.overhead_factor
        total_active *= self.overhead_factor
        total_peak *= self.overhead_factor

        per_node = total_active / max(total_nodes, 1)

        return PowerEstimate(
            total_idle_mw=total_idle,
            total_active_mw=total_active,
            total_peak_mw=total_peak,
            per_node_active_mw=per_node,
            overhead_factor=self.overhead_factor,
        )

    def estimate_for_swarm(
        self,
        manifest: DriverManifest,
        node_count: int,
    ) -> PowerEstimate:
        return self.estimate([manifest], [node_count])
