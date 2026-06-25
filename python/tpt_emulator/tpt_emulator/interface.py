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
class EmulatorResult:
    success: bool
    telemetry: list[TelemetryPoint] = field(default_factory=list)
    inference_time_ms: float = 0.0
    tokens_per_second: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "telemetry_count": len(self.telemetry),
            "inference_time_ms": self.inference_time_ms,
            "tokens_per_second": self.tokens_per_second,
            "metadata": self.metadata,
        }


class EmulatorInterface(ABC):
    """Base class for all SiL emulators.

    Each emulator produces the same telemetry schema as its real hardware
    counterpart, so Observer cannot tell the difference.
    """

    def __init__(self, hardware_type: HardwareType):
        self.hardware_type = hardware_type
        self.telemetry_log: list[TelemetryPoint] = []

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
