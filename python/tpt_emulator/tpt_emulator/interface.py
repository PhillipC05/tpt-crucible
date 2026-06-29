"""Unified emulator interface — same telemetry schema as real hardware."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import time


class HardwareType(Enum):
    ALLOY = "alloy"
    FUSION = "fusion"
    ELEMENT = "element"


@dataclass
class TelemetryPoint:
    timestamp: float
    hardware_type: str
    node_id: str
    metrics: dict[str, Any]


@dataclass
class SparkBaselineRef:
    """Compact reference to the GPU baseline loaded from Spark benchmark files."""
    model_name: str
    tokens_per_second: float
    hardware: str
    date: str = ""
    time_to_first_token_ms: float = 0.0

    def display_label(self) -> str:
        parts = ["GPU reference: TPT Spark"]
        if self.date:
            parts.append(self.date)
        if self.hardware:
            parts.append(self.hardware)
        parts.append(f"{self.tokens_per_second:.1f} tok/s")
        return ", ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "tokens_per_second": round(self.tokens_per_second, 2),
            "hardware": self.hardware,
            "date": self.date,
            "time_to_first_token_ms": round(self.time_to_first_token_ms, 2),
            "label": self.display_label(),
        }


@dataclass
class EmulatorResult:
    success: bool
    telemetry: list[TelemetryPoint] = field(default_factory=list)
    inference_time_ms: float = 0.0
    tokens_per_second: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    # Spark GPU baseline loaded on startup — None when no benchmark file is found.
    spark_baseline: SparkBaselineRef | None = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "success": self.success,
            "telemetry_count": len(self.telemetry),
            "inference_time_ms": self.inference_time_ms,
            "tokens_per_second": self.tokens_per_second,
            "metadata": self.metadata,
        }
        if self.spark_baseline is not None:
            d["spark_baseline"] = self.spark_baseline.to_dict()
        return d


def load_spark_baseline_for_model(model_name: str) -> SparkBaselineRef | None:
    """Try to load the most recent Spark benchmark for model_name.

    Returns None silently when no benchmark file exists — the emulator always
    works; the baseline is optional context for Observer's comparison panel.
    """
    try:
        from tpt_catalyst.spark_benchmark import load_spark_baseline
        b = load_spark_baseline(model_name)
        if b is None:
            return None
        return SparkBaselineRef(
            model_name=b.model_name,
            tokens_per_second=b.tokens_per_second,
            hardware=b.hardware,
            date=b.date,
            time_to_first_token_ms=b.time_to_first_token_ms,
        )
    except ImportError:
        return None


class EmulatorInterface(ABC):
    """Base class for all SiL emulators.

    Each emulator produces the same telemetry schema as its real hardware
    counterpart, so Observer cannot tell the difference.

    On load_model(), the emulator automatically probes ~/.tpt/benchmarks/ for
    a Spark baseline matching the model name. If found, it is attached to every
    EmulatorResult so Observer's benchmark panel can show a side-by-side
    comparison without user configuration.
    """

    def __init__(self, hardware_type: HardwareType):
        self.hardware_type = hardware_type
        self.telemetry_log: list[TelemetryPoint] = []
        self._spark_baseline: SparkBaselineRef | None = None

    @abstractmethod
    def load_model(self, model_path: str) -> bool:
        """Load a compiled model for emulation."""
        ...

    @abstractmethod
    def run_inference(self, input_data: Any) -> EmulatorResult:
        """Run inference and return results with telemetry."""
        ...

    @abstractmethod
    def get_telemetry(self) -> list[TelemetryPoint]:
        """Get collected telemetry points."""
        ...

    def _load_spark_baseline(self, model_name: str) -> None:
        """Probe for a Spark baseline and cache it on the instance."""
        self._spark_baseline = load_spark_baseline_for_model(model_name)

    def _make_result(
        self,
        success: bool,
        inference_time_ms: float = 0.0,
        tokens_per_second: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> EmulatorResult:
        """Construct an EmulatorResult pre-populated with the Spark baseline."""
        return EmulatorResult(
            success=success,
            telemetry=list(self.telemetry_log),
            inference_time_ms=inference_time_ms,
            tokens_per_second=tokens_per_second,
            metadata=metadata or {},
            spark_baseline=self._spark_baseline,
        )

    def _record_telemetry(self, node_id: str, metrics: dict[str, Any]) -> TelemetryPoint:
        point = TelemetryPoint(
            timestamp=time.time(),
            hardware_type=self.hardware_type.value,
            node_id=node_id,
            metrics=metrics,
        )
        self.telemetry_log.append(point)
        return point

    def clear_telemetry(self) -> None:
        self.telemetry_log.clear()
