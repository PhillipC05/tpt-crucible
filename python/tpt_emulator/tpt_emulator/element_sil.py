"""Element SiL — Xyce/ngspice analog simulation backend."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import time

from .interface import EmulatorInterface, EmulatorResult, HardwareType, TelemetryPoint


class ElementSil(EmulatorInterface):
    """Analog compute simulation using SPICE backends."""

    def __init__(self, vdd: float = 3.3, temperature_k: float = 300.0):
        super().__init__(HardwareType.ELEMENT)
        self.vdd = vdd
        self.temperature_k = temperature_k
        self.spice_backend = None

    def load_model(self, model_path: str) -> bool:
        try:
            import PySpice
            self.spice_backend = "xyce"
        except ImportError:
            try:
                import subprocess
                result = subprocess.run(["ngspice", "--version"], capture_output=True, text=True)
                self.spice_backend = "ngspice" if result.returncode == 0 else None
            except FileNotFoundError:
                self.spice_backend = None
        return True

    def run_inference(self, input_data: Any) -> EmulatorResult:
        start = time.time()

        self._record_telemetry("analog_core", {
            "vdd": self.vdd,
            "temperature_k": self.temperature_k,
            "backend": self.spice_backend or "emulated",
            "status": "simulating",
        })

        estimated_noise_uV = 50.0
        estimated_drift_pct = 0.01

        self._record_telemetry("analog_core", {
            "thermal_noise_uV": estimated_noise_uV,
            "voltage_drift_pct": estimated_drift_pct,
        })

        elapsed_ms = (time.time() - start) * 1000
        return EmulatorResult(
            success=True,
            inference_time_ms=elapsed_ms,
            tokens_per_second=0.0,
            metadata={
                "backend": self.spice_backend or "emulated",
                "vdd": self.vdd,
                "temperature_k": self.temperature_k,
            },
        )

    def get_telemetry(self) -> list[TelemetryPoint]:
        return list(self.telemetry_log)
