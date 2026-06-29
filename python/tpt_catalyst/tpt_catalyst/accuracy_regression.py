"""Automatic Accuracy Regression — detect accuracy changes on recompile."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import json
from pathlib import Path


@dataclass
class RegressionResult:
    baseline_accuracy: float
    new_accuracy: float
    delta: float
    status: str
    threshold: float

    @property
    def improved(self) -> bool:
        return self.delta > 0.01

    @property
    def regressed(self) -> bool:
        return self.delta < -self.threshold

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_accuracy": round(self.baseline_accuracy, 4),
            "new_accuracy": round(self.new_accuracy, 4),
            "delta": round(self.delta, 4),
            "status": self.status,
            "threshold": self.threshold,
        }


class RegressionChecker:
    """Check for accuracy regression between package versions."""

    def __init__(self, threshold: float = 0.02):
        self.threshold = threshold
        self.history: list[dict[str, Any]] = []

    def check_regression(
        self,
        baseline_accuracy: float,
        new_accuracy: float,
    ) -> RegressionResult:
        delta = new_accuracy - baseline_accuracy

        if delta > 0.01:
            status = "improved"
        elif delta < -self.threshold:
            status = "regressed"
        else:
            status = "unchanged"

        return RegressionResult(
            baseline_accuracy=baseline_accuracy,
            new_accuracy=new_accuracy,
            delta=delta,
            status=status,
            threshold=self.threshold,
        )

    def record_result(self, model_name: str, result: RegressionResult) -> None:
        self.history.append({
            "model_name": model_name,
            "result": result.to_dict(),
        })

    def get_history(self, model_name: str | None = None) -> list[dict[str, Any]]:
        if model_name:
            return [h for h in self.history if h["model_name"] == model_name]
        return self.history

    def find_baseline(self, model_name: str) -> float | None:
        entries = [h for h in self.history if h["model_name"] == model_name]
        if entries:
            return entries[-1]["result"]["new_accuracy"]
        return None

    def save_history(self, path: Path) -> None:
        path.write_text(json.dumps(self.history, indent=2))

    def load_history(self, path: Path) -> None:
        if path.exists():
            self.history = json.loads(path.read_text())
