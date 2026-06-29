"""Synthesis Constraint Auto-Tuner — predict optimal Yosys/Nextpnr parameters."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json


@dataclass
class SynthParams:
    yosys_strategy: str = "area"
    effort_level: int = 2
    abc_passes: int = 3
    nextpnr_seed: int = 42
    timing_margin_ns: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "yosys_strategy": self.yosys_strategy,
            "effort_level": self.effort_level,
            "abc_passes": self.abc_passes,
            "nextpnr_seed": self.nextpnr_seed,
            "timing_margin_ns": self.timing_margin_ns,
        }


@dataclass
class SynthResult:
    params: SynthParams
    timing_slack_ns: float
    lut_utilization: float
    dsp_utilization: float
    duration_s: float
    model_shape: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "params": self.params.to_dict(),
            "timing_slack_ns": round(self.timing_slack_ns, 3),
            "lut_utilization": round(self.lut_utilization, 4),
            "dsp_utilization": round(self.dsp_utilization, 4),
            "duration_s": round(self.duration_s, 2),
        }


class SynthesisTuner:
    """Tune synthesis parameters based on accumulated job logs."""

    def __init__(self):
        self.job_history: list[SynthResult] = []

    def log_job(self, result: SynthResult) -> None:
        self.job_history.append(result)

    def predict_params(self, model_shape: dict[str, int]) -> SynthParams:
        if not self.job_history:
            return SynthParams()

        similar = self._find_similar(model_shape)
        if not similar:
            return SynthParams()

        best = min(similar, key=lambda r: -r.timing_slack_ns if r.timing_slack_ns < 0 else 0)
        return best.params

    def _find_similar(self, model_shape: dict[str, int]) -> list[SynthResult]:
        if not self.job_history:
            return []
        target_ops = model_shape.get("total_ops", 0)
        scored = []
        for job in self.job_history:
            job_ops = job.model_shape.get("total_ops", 0)
            similarity = 1.0 - abs(target_ops - job_ops) / max(target_ops, job_ops, 1)
            scored.append((similarity, job))
        scored.sort(key=lambda x: -x[0])
        return [job for _, job in scored[:5]]

    def get_stats(self) -> dict[str, Any]:
        if not self.job_history:
            return {"jobs": 0}
        slacks = [r.timing_slack_ns for r in self.job_history]
        return {
            "jobs": len(self.job_history),
            "avg_slack_ns": round(sum(slacks) / len(slacks), 3),
            "best_slack_ns": round(max(slacks), 3),
        }
