"""Pre-flight compatibility analyzer — checks operator support per hardware target."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .ir import TptIr, OpNode


class HardwareTarget(Enum):
    FUSION = "fusion"
    ALLOY = "alloy"
    ELEMENT = "element"


class Severity(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class OpCompatibility:
    op_type: str
    target: HardwareTarget
    severity: Severity
    message: str
    suggestion: str = ""


@dataclass
class CompatibilityReport:
    results: list[OpCompatibility] = field(default_factory=list)

    @property
    def score(self) -> float:
        if not self.results:
            return 1.0
        passes = sum(1 for r in self.results if r.severity == Severity.PASS)
        return passes / len(self.results)

    @property
    def has_failures(self) -> bool:
        return any(r.severity == Severity.FAIL for r in self.results)

    @property
    def warnings(self) -> list[OpCompatibility]:
        return [r for r in self.results if r.severity == Severity.WARN]

    @property
    def failures(self) -> list[OpCompatibility]:
        return [r for r in self.results if r.severity == Severity.FAIL]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "total_ops": len(self.results),
            "passes": sum(1 for r in self.results if r.severity == Severity.PASS),
            "warnings": len(self.warnings),
            "failures": len(self.failures),
            "details": [
                {
                    "op": r.op_type,
                    "severity": r.severity.value,
                    "message": r.message,
                    "suggestion": r.suggestion,
                }
                for r in self.results
            ],
        }


OPERATOR_SUPPORT: dict[HardwareTarget, dict[str, Severity]] = {
    HardwareTarget.FUSION: {
        "matmul": Severity.PASS,
        "fused_matmul_relu": Severity.PASS,
        "fused_matmul_gelu": Severity.PASS,
        "fused_add_relu": Severity.PASS,
        "relu": Severity.PASS,
        "gelu": Severity.WARN,
        "sigmoid": Severity.WARN,
        "tanh": Severity.WARN,
        "conv2d": Severity.PASS,
        "maxpool": Severity.PASS,
        "avgpool": Severity.PASS,
        "softmax": Severity.FAIL,
        "attention": Severity.FAIL,
        "layernorm": Severity.WARN,
        "batchnorm": Severity.PASS,
        "dropout": Severity.PASS,
        "embedding": Severity.WARN,
        "softmax_temperature": Severity.FAIL,
    },
    HardwareTarget.ALLOY: {
        "matmul": Severity.PASS,
        "fused_matmul_relu": Severity.PASS,
        "fused_matmul_gelu": Severity.PASS,
        "fused_add_relu": Severity.PASS,
        "relu": Severity.PASS,
        "gelu": Severity.PASS,
        "sigmoid": Severity.WARN,
        "tanh": Severity.WARN,
        "conv2d": Severity.PASS,
        "maxpool": Severity.PASS,
        "avgpool": Severity.PASS,
        "softmax": Severity.WARN,
        "attention": Severity.WARN,
        "layernorm": Severity.PASS,
        "batchnorm": Severity.PASS,
        "dropout": Severity.PASS,
        "embedding": Severity.PASS,
        "softmax_temperature": Severity.WARN,
    },
    HardwareTarget.ELEMENT: {
        "matmul": Severity.PASS,
        "fused_matmul_relu": Severity.FAIL,
        "fused_matmul_gelu": Severity.FAIL,
        "fused_add_relu": Severity.FAIL,
        "relu": Severity.WARN,
        "gelu": Severity.FAIL,
        "sigmoid": Severity.PASS,
        "tanh": Severity.PASS,
        "conv2d": Severity.FAIL,
        "maxpool": Severity.FAIL,
        "avgpool": Severity.FAIL,
        "softmax": Severity.FAIL,
        "attention": Severity.FAIL,
        "layernorm": Severity.FAIL,
        "batchnorm": Severity.WARN,
        "dropout": Severity.FAIL,
        "embedding": Severity.FAIL,
        "softmax_temperature": Severity.FAIL,
    },
}

SUBSTITUTION_SUGGESTIONS = {
    ("attention", HardwareTarget.FUSION): "Use Flash Attention or tiling strategy for FPGA",
    ("softmax", HardwareTarget.FUSION): "Approximate softmax with lookup table or piecewise linear",
    ("gelu", HardwareTarget.FUSION): "Approximate GELU with sigmoid-based polynomial",
    ("sigmoid", HardwareTarget.ELEMENT): "Replace with piecewise linear approximation for analog",
    ("attention", HardwareTarget.ELEMENT): "Replace with linear attention or state-space model",
    ("fused_matmul_relu", HardwareTarget.ELEMENT): "Split into separate matmul + activation nodes",
}


def check_compatibility(ir: TptIr, target: HardwareTarget) -> CompatibilityReport:
    """Check TPT-IR compatibility with a hardware target."""
    report = CompatibilityReport()
    support = OPERATOR_SUPPORT[target]

    for node in ir.graph.nodes:
        severity = support.get(node.op_type, Severity.FAIL)
        suggestion = SUBSTITUTION_SUGGESTIONS.get((node.op_type, target), "")

        if severity == Severity.PASS:
            msg = f"Operator '{node.op_type}' fully supported on {target.value}"
        elif severity == Severity.WARN:
            msg = f"Operator '{node.op_type}' partially supported on {target.value}"
        else:
            msg = f"Operator '{node.op_type}' NOT supported on {target.value}"

        report.results.append(OpCompatibility(
            op_type=node.op_type,
            target=target,
            severity=severity,
            message=msg,
            suggestion=suggestion,
        ))

    return report
