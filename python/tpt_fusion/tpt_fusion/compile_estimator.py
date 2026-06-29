"""Predictive Compile Time Estimator — predict synthesis duration."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CompileEstimate:
    estimated_minutes: float
    confidence_low: float
    confidence_high: float
    model_ops: int
    board: str
    synthesis_mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "estimated_minutes": round(self.estimated_minutes, 1),
            "confidence_range": [round(self.confidence_low, 1), round(self.confidence_high, 1)],
            "model_ops": self.model_ops,
            "board": self.board,
            "synthesis_mode": self.synthesis_mode,
        }


@dataclass
class JobRecord:
    model_ops: int
    tensor_shapes: list[int]
    board: str
    synthesis_mode: str
    duration_minutes: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_ops": self.model_ops,
            "board": self.board,
            "synthesis_mode": self.synthesis_mode,
            "duration_minutes": round(self.duration_minutes, 1),
        }


class CompileEstimator:
    """Predict synthesis compile time based on historical data."""

    def __init__(self):
        self.history: list[JobRecord] = []

    def log_job(self, record: JobRecord) -> None:
        self.history.append(record)

    def estimate(
        self,
        model_ops: int,
        board: str,
        synthesis_mode: str = "full",
    ) -> CompileEstimate:
        similar = self._find_similar(model_ops, board, synthesis_mode)

        if not similar:
            base = self._base_estimate(model_ops, board)
            return CompileEstimate(
                estimated_minutes=base,
                confidence_low=base * 0.5,
                confidence_high=base * 2.0,
                model_ops=model_ops,
                board=board,
                synthesis_mode=synthesis_mode,
            )

        durations = [r.duration_minutes for r in similar]
        avg = sum(durations) / len(durations)
        std = (sum((d - avg) ** 2 for d in durations) / len(durations)) ** 0.5

        return CompileEstimate(
            estimated_minutes=avg,
            confidence_low=max(0, avg - 1.96 * std),
            confidence_high=avg + 1.96 * std,
            model_ops=model_ops,
            board=board,
            synthesis_mode=synthesis_mode,
        )

    def _base_estimate(self, model_ops: int, board: str) -> float:
        base_minutes = model_ops / 1_000_000
        board_factor = {"alveo_u250": 1.0, "alveo_u280": 0.8, "ice40": 0.3}.get(board, 1.0)
        return max(1.0, base_minutes * board_factor)

    def _find_similar(
        self,
        model_ops: int,
        board: str,
        synthesis_mode: str,
    ) -> list[JobRecord]:
        scored = []
        for job in self.history:
            ops_sim = 1.0 - abs(job.model_ops - model_ops) / max(job.model_ops, model_ops, 1)
            board_sim = 1.0 if job.board == board else 0.0
            mode_sim = 1.0 if job.synthesis_mode == synthesis_mode else 0.0
            similarity = ops_sim * 0.5 + board_sim * 0.3 + mode_sim * 0.2
            scored.append((similarity, job))
        scored.sort(key=lambda x: -x[0])
        return [job for _, job in scored[:5] if _ > 0.3]
