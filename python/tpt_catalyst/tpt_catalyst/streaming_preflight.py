"""Streaming pre-flight check — emit results as a stream rather than blocking."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Generator, Any

from .compat import check_compatibility, HardwareTarget, Severity, OpCompatibility
from .ir import TptIr


@dataclass
class PreflightEvent:
    event_type: str
    node_id: int
    op_type: str
    severity: str
    message: str
    suggestion: str = ""
    progress: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "node_id": self.node_id,
            "op_type": self.op_type,
            "severity": self.severity,
            "message": self.message,
            "suggestion": self.suggestion,
            "progress": self.progress,
        }


def stream_preflight(
    ir: TptIr,
    target: HardwareTarget,
) -> Generator[PreflightEvent, None, None]:
    """Stream pre-flight results one operator at a time."""
    total = len(ir.graph.nodes)

    yield PreflightEvent(
        event_type="start",
        node_id=-1,
        op_type="",
        severity="info",
        message=f"Starting pre-flight check for {target.value} with {total} operators",
        progress=0.0,
    )

    for i, node in enumerate(ir.graph.nodes):
        report = check_compatibility(
            TptIr(
                version=ir.version,
                metadata=ir.metadata,
                graph=type(ir.graph)(nodes=[node], edges=[]),
            ),
            target,
        )

        if report.results:
            result = report.results[0]
            yield PreflightEvent(
                event_type="result",
                node_id=node.id,
                op_type=node.op_type,
                severity=result.severity.value,
                message=result.message,
                suggestion=result.suggestion,
                progress=(i + 1) / total,
            )
        else:
            yield PreflightEvent(
                event_type="result",
                node_id=node.id,
                op_type=node.op_type,
                severity="pass",
                message=f"Operator '{node.op_type}' checked",
                progress=(i + 1) / total,
            )

    full_report = check_compatibility(ir, target)
    yield PreflightEvent(
        event_type="complete",
        node_id=-1,
        op_type="",
        severity="info",
        message=f"Pre-flight complete. Score: {full_report.score:.0%}, "
                f"Warnings: {len(full_report.warnings)}, Failures: {len(full_report.failures)}",
        progress=1.0,
    )


def apply_fix(ir: TptIr, op_id: int, substitution: str) -> TptIr:
    """Apply a deterministic operator substitution."""
    substitution_map = {
        "flash_attention_to_mha": ("attention", "mha"),
        "swiglu_to_gelu": ("swiglu", "gelu"),
        "rmsnorm_to_layernorm": ("rmsnorm", "layernorm"),
    }

    if substitution not in substitution_map:
        return ir

    old_op, new_op = substitution_map[substitution]

    for node in ir.graph.nodes:
        if node.id == op_id and node.op_type == old_op:
            node.op_type = new_op
            break

    return ir
