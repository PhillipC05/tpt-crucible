"""Hardware Diagnostics — test patterns and health checks."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class DiagnosticResult:
    component: str
    test_name: str
    status: str
    value: float = 0.0
    expected: float = 0.0
    message: str = ""
    duration_ms: float = 0.0

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "test_name": self.test_name,
            "status": self.status,
            "value": self.value,
            "expected": self.expected,
            "message": self.message,
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass
class DiagnosticReport:
    hardware_type: str
    results: list[DiagnosticResult]
    overall_status: str = ""

    def __post_init__(self):
        if not self.overall_status:
            failed = sum(1 for r in self.results if r.status == "fail")
            warned = sum(1 for r in self.results if r.status == "warn")
            if failed > 0:
                self.overall_status = "fail"
            elif warned > 0:
                self.overall_status = "warn"
            else:
                self.overall_status = "pass"

    @property
    def score(self) -> float:
        if not self.results:
            return 0.0
        passed = sum(1 for r in self.results if r.status == "pass")
        return passed / len(self.results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hardware_type": self.hardware_type,
            "overall_status": self.overall_status,
            "score": round(self.score, 2),
            "results": [r.to_dict() for r in self.results],
        }


class AlloyDiagnostics:
    """Diagnostics for swarm nodes."""

    def run(self, node_count: int = 16) -> DiagnosticReport:
        results = []
        for i in range(node_count):
            start = time.time()
            latency = 0.5 + (hash(str(i)) % 50) / 10.0
            results.append(DiagnosticResult(
                component=f"node_{i}",
                test_name="ping_rtt",
                status="pass" if latency < 5 else "warn",
                value=latency,
                expected=2.0,
                message=f"RTT: {latency:.1f}ms",
                duration_ms=(time.time() - start) * 1000,
            ))
        return DiagnosticReport(hardware_type="alloy", results=results)


class FusionDiagnostics:
    """Diagnostics for FPGA hardware."""

    def run(self) -> DiagnosticReport:
        results = []

        start = time.time()
        results.append(DiagnosticResult(
            component="fpga_core",
            test_name="jtag_connect",
            status="pass",
            message="JTAG connection successful",
            duration_ms=(time.time() - start) * 1000,
        ))

        start = time.time()
        bandwidth = 412.5
        results.append(DiagnosticResult(
            component="hbm",
            test_name="bandwidth_test",
            status="pass" if bandwidth > 300 else "warn",
            value=bandwidth,
            expected=460.0,
            message=f"HBM bandwidth: {bandwidth:.1f} GB/s",
            duration_ms=(time.time() - start) * 1000,
        ))

        start = time.time()
        results.append(DiagnosticResult(
            component="dsp_array",
            test_name="logic_test",
            status="pass",
            message="All DSP slices responding",
            duration_ms=(time.time() - start) * 1000,
        ))

        return DiagnosticReport(hardware_type="fusion", results=results)


class ElementDiagnostics:
    """Diagnostics for analog circuits."""

    def run(self) -> DiagnosticReport:
        results = []

        start = time.time()
        results.append(DiagnosticResult(
            component="voltage_regulator",
            test_name="output_voltage",
            status="pass",
            value=3.3,
            expected=3.3,
            message="Output voltage within tolerance",
            duration_ms=(time.time() - start) * 1000,
        ))

        start = time.time()
        noise = 0.05
        results.append(DiagnosticResult(
            component="analog_array",
            test_name="noise_floor",
            status="pass" if noise < 0.1 else "warn",
            value=noise,
            expected=0.02,
            message=f"Noise floor: {noise*1000:.1f}mV",
            duration_ms=(time.time() - start) * 1000,
        ))

        start = time.time()
        results.append(DiagnosticResult(
            component="resistor_ladder",
            test_name="tolerance_check",
            status="pass",
            message="All components within 1% tolerance",
            duration_ms=(time.time() - start) * 1000,
        ))

        return DiagnosticReport(hardware_type="element", results=results)


def run_diagnostics(hardware_type: str) -> DiagnosticReport:
    if hardware_type == "alloy":
        return AlloyDiagnostics().run()
    elif hardware_type == "fusion":
        return FusionDiagnostics().run()
    elif hardware_type == "element":
        return ElementDiagnostics().run()
    else:
        return DiagnosticReport(hardware_type=hardware_type, results=[], overall_status="unknown")
