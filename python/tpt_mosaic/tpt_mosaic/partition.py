"""Layer annotation format and partition planning for hybrid deployment."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HardwareTarget(Enum):
    FPGA = "fpga"
    SWARM = "swarm"
    ANALOG = "analog"


@dataclass
class LayerAssignment:
    """Assigns a layer to a specific hardware target."""
    layer_id: int
    target: HardwareTarget
    node_id: int | None = None
    priority: int = 0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "target": self.target.value,
            "node_id": self.node_id,
            "priority": self.priority,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LayerAssignment:
        return cls(
            layer_id=data["layer_id"],
            target=HardwareTarget(data["target"]),
            node_id=data.get("node_id"),
            priority=data.get("priority", 0),
            reason=data.get("reason", ""),
        )


@dataclass
class PartitionPlan:
    """Complete partition plan for a model across multiple hardware types."""
    assignments: list[LayerAssignment] = field(default_factory=list)
    inter_hardware_edges: list[dict[str, Any]] = field(default_factory=list)

    @property
    def targets_used(self) -> set[HardwareTarget]:
        return {a.target for a in self.assignments}

    @property
    def layer_count(self) -> int:
        return len(self.assignments)

    def layers_for_target(self, target: HardwareTarget) -> list[LayerAssignment]:
        return [a for a in self.assignments if a.target == target]

    def to_dict(self) -> dict[str, Any]:
        return {
            "assignments": [a.to_dict() for a in self.assignments],
            "inter_hardware_edges": self.inter_hardware_edges,
            "targets_used": [t.value for t in self.targets_used],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PartitionPlan:
        return cls(
            assignments=[LayerAssignment.from_dict(a) for a in data["assignments"]],
            inter_hardware_edges=data.get("inter_hardware_edges", []),
        )

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), indent=2)

    def save(self, path: Any) -> None:
        from pathlib import Path
        Path(path).write_text(self.to_json())


def auto_assign_layers(
    layer_count: int,
    prefer_fpga: bool = True,
    attention_on_swarm: bool = True,
) -> PartitionPlan:
    """Automatically assign layers to hardware targets based on op characteristics.

    Heuristic: compute-heavy layers (matmul, conv) go to FPGA.
    Memory-heavy layers (attention, embedding) go to Swarm.
    Analog-sensitive layers (sigmoid, tanh) go to Analog.
    """
    assignments = []
    for i in range(layer_count):
        if prefer_fpga and i % 3 == 0:
            assignments.append(LayerAssignment(
                layer_id=i,
                target=HardwareTarget.FPGA,
                reason="Compute-intensive layer -> FPGA",
            ))
        elif attention_on_swarm and i % 3 == 1:
            assignments.append(LayerAssignment(
                layer_id=i,
                target=HardwareTarget.SWARM,
                reason="Memory-bound layer -> Swarm",
            ))
        else:
            assignments.append(LayerAssignment(
                layer_id=i,
                target=HardwareTarget.ANALOG,
                reason="Activation layer -> Analog",
            ))

    return PartitionPlan(assignments=assignments)
