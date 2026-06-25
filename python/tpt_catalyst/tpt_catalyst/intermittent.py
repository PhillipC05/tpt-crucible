"""Intermittent Computing — checkpoint ops for energy-harvesting devices."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from .ir import TptIr, OpNode


class CheckpointGranularity(Enum):
    LAYER = "layer"
    BLOCK = "block"
    OPERATOR = "operator"


@dataclass
class CheckpointConfig:
    granularity: CheckpointGranularity = CheckpointGranularity.LAYER
    energy_budget_mj: float = 100.0
    checkpoint_storage: str = "eeprom"
    power_monitor_pin: str = "GPIO0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "granularity": self.granularity.value,
            "energy_budget_mj": self.energy_budget_mj,
            "checkpoint_storage": self.checkpoint_storage,
            "power_monitor_pin": self.power_monitor_pin,
        }


@dataclass
class CheckpointOp:
    op_id: int
    layer_name: str
    checkpoint_type: str
    storage_offset: int = 0
    state_size_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "op_id": self.op_id,
            "layer_name": self.layer_name,
            "checkpoint_type": self.checkpoint_type,
            "storage_offset": self.storage_offset,
            "state_size_bytes": self.state_size_bytes,
        }


@dataclass
class EnergyEstimate:
    layer_name: str
    energy_mj: float
    has_checkpoint: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer_name": self.layer_name,
            "energy_mj": round(self.energy_mj, 4),
            "has_checkpoint": self.has_checkpoint,
        }


class CheckpointPlanner:
    """Plan checkpoint insertion for intermittent computing."""

    def __init__(self, config: CheckpointConfig):
        self.config = config
        self.checkpoints: list[CheckpointOp] = []
        self.energy_estimates: list[EnergyEstimate] = []

    def estimate_energy_per_layer(self, ir: TptIr, energy_per_op_mj: float = 0.5) -> list[EnergyEstimate]:
        estimates = []
        for node in ir.graph.nodes:
            energy = energy_per_op_mj
            estimates.append(EnergyEstimate(
                layer_name=node.name,
                energy_mj=energy,
            ))
        self.energy_estimates = estimates
        return estimates

    def insert_checkpoints(self, ir: TptIr) -> list[CheckpointOp]:
        self.checkpoints = []
        storage_offset = 0
        accum_energy = 0.0

        for i, node in enumerate(ir.graph.nodes):
            layer_energy = 0.5
            accum_energy += layer_energy

            should_checkpoint = False
            if self.config.granularity == CheckpointGranularity.LAYER:
                should_checkpoint = True
            elif self.config.granularity == CheckpointGranularity.BLOCK:
                should_checkpoint = i % 4 == 0
            else:
                should_checkpoint = True

            if should_checkpoint and accum_energy > 0:
                state_size = 4096
                self.checkpoints.append(CheckpointOp(
                    op_id=node.id,
                    layer_name=node.name,
                    checkpoint_type=self.config.checkpoint_storage,
                    storage_offset=storage_offset,
                    state_size_bytes=state_size,
                ))
                storage_offset += state_size
                accum_energy = 0.0

        return self.checkpoints

    def validate_budget(self, total_energy_mj: float | None = None) -> dict[str, Any]:
        if total_energy_mj is None:
            total_energy_mj = sum(e.energy_mj for e in self.energy_estimates)

        budget_ok = total_energy_mj <= self.config.energy_budget_mj
        checkpoints_needed = len(self.checkpoints)

        return {
            "total_energy_mj": round(total_energy_mj, 4),
            "budget_mj": self.config.energy_budget_mj,
            "budget_ok": budget_ok,
            "checkpoints_needed": checkpoints_needed,
            "margin_mj": round(self.config.energy_budget_mj - total_energy_mj, 4),
        }
