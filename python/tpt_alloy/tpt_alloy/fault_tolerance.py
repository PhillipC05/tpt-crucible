"""Fault-Tolerant Execution — heartbeat, rerouting, and recovery."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class HeartbeatConfig:
    interval_ms: int = 1000
    timeout_ms: int = 3000
    max_missed: int = 3

    def to_dict(self) -> dict[str, Any]:
        return {
            "interval_ms": self.interval_ms,
            "timeout_ms": self.timeout_ms,
            "max_missed": self.max_missed,
        }


@dataclass
class NodeStatus:
    node_id: int
    last_heartbeat: float = 0.0
    missed_heartbeats: int = 0
    status: str = "online"
    assigned_layers: list[int] = field(default_factory=list)

    @property
    def is_alive(self) -> bool:
        return self.status == "online"

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat,
            "missed_heartbeats": self.missed_heartbeats,
            "assigned_layers": self.assigned_layers,
        }


@dataclass
class RecoveryPlan:
    """Describes the layer rebalancing performed when a node rejoins the swarm."""
    recovered_node_id: int
    reclaimed_layers: list[int]
    donor_nodes: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "recovered_node_id": self.recovered_node_id,
            "reclaimed_layers": self.reclaimed_layers,
            "donor_nodes": self.donor_nodes,
        }


@dataclass
class FaultToleranceReport:
    total_nodes: int
    online_nodes: int
    dead_nodes: list[int]
    reassigned_layers: list[dict[str, Any]]
    recovered_nodes: list[int] = field(default_factory=list)
    recovery_plans: list[RecoveryPlan] = field(default_factory=list)

    @property
    def health_score(self) -> float:
        return self.online_nodes / max(self.total_nodes, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_nodes": self.total_nodes,
            "online_nodes": self.online_nodes,
            "dead_nodes": self.dead_nodes,
            "health_score": round(self.health_score, 2),
            "reassigned_layers": self.reassigned_layers,
            "recovered_nodes": self.recovered_nodes,
            "recovery_plans": [r.to_dict() for r in self.recovery_plans],
        }


class FaultToleranceManager:
    """Manage fault detection and recovery for swarm nodes."""

    def __init__(self, config: HeartbeatConfig | None = None):
        self.config = config or HeartbeatConfig()
        self.nodes: dict[int, NodeStatus] = {}
        self._recovery_history: list[RecoveryPlan] = []

    def register_node(self, node_id: int) -> NodeStatus:
        status = NodeStatus(node_id=node_id)
        self.nodes[node_id] = status
        return status

    def receive_heartbeat(self, node_id: int) -> None:
        if node_id in self.nodes:
            self.nodes[node_id].last_heartbeat = time.time()
            self.nodes[node_id].missed_heartbeats = 0
            self.nodes[node_id].status = "online"

    def check_timeouts(self) -> list[int]:
        now = time.time()
        dead_nodes = []
        for node_id, status in self.nodes.items():
            if status.status == "online":
                elapsed = (now - status.last_heartbeat) * 1000
                if elapsed > self.config.timeout_ms:
                    status.missed_heartbeats += 1
                    if status.missed_heartbeats >= self.config.max_missed:
                        status.status = "dead"
                        dead_nodes.append(node_id)
        return dead_nodes

    def reroute_layers(self, dead_node_id: int, alive_nodes: list[int]) -> list[dict[str, Any]]:
        if dead_node_id not in self.nodes:
            return []

        dead_status = self.nodes[dead_node_id]
        layers_to_reassign = dead_status.assigned_layers
        reassignments = []

        for i, layer_id in enumerate(layers_to_reassign):
            target_node = alive_nodes[i % len(alive_nodes)] if alive_nodes else 0
            self.nodes[target_node].assigned_layers.append(layer_id)
            reassignments.append({
                "layer_id": layer_id,
                "from_node": dead_node_id,
                "to_node": target_node,
            })

        dead_status.assigned_layers = []
        return reassignments

    def recover_node(self, node_id: int) -> None:
        """Mark a node as recovered without rebalancing. Use recover_and_rebalance for full recovery."""
        if node_id in self.nodes:
            self.nodes[node_id].status = "online"
            self.nodes[node_id].missed_heartbeats = 0

    def recover_and_rebalance(self, node_id: int, max_reclaim: int = 2) -> RecoveryPlan:
        """Mark a node as recovered and reclaim layers from the most-loaded alive nodes.

        After a dead node comes back online, this redistributes some work back to it so
        surviving nodes are not permanently overloaded. Up to `max_reclaim` layers are
        taken from the busiest donor nodes (each donor retains at least one layer).
        """
        if node_id not in self.nodes:
            return RecoveryPlan(
                recovered_node_id=node_id,
                reclaimed_layers=[],
                donor_nodes=[],
            )

        self.nodes[node_id].status = "online"
        self.nodes[node_id].missed_heartbeats = 0

        alive_donors = [
            n for n in self.nodes.values()
            if n.is_alive and n.node_id != node_id and len(n.assigned_layers) > 1
        ]
        # Most-loaded donors first so we rebalance from overloaded nodes
        alive_donors.sort(key=lambda n: len(n.assigned_layers), reverse=True)

        reclaimed_layers: list[int] = []
        donor_records: list[dict[str, Any]] = []

        for donor in alive_donors:
            if len(reclaimed_layers) >= max_reclaim:
                break
            can_give = len(donor.assigned_layers) - 1  # keep at least one layer per donor
            if can_give <= 0:
                continue
            give_count = min(can_give, max_reclaim - len(reclaimed_layers))
            layers_given = donor.assigned_layers[-give_count:]
            donor.assigned_layers = donor.assigned_layers[:-give_count]
            self.nodes[node_id].assigned_layers.extend(layers_given)
            reclaimed_layers.extend(layers_given)
            donor_records.append({
                "node_id": donor.node_id,
                "layers_given_back": layers_given,
            })

        plan = RecoveryPlan(
            recovered_node_id=node_id,
            reclaimed_layers=reclaimed_layers,
            donor_nodes=donor_records,
        )
        self._recovery_history.append(plan)
        return plan

    def get_report(self) -> FaultToleranceReport:
        online = [n for n in self.nodes.values() if n.is_alive]
        dead = [n for n in self.nodes.values() if not n.is_alive]
        recovered = [p.recovered_node_id for p in self._recovery_history]
        return FaultToleranceReport(
            total_nodes=len(self.nodes),
            online_nodes=len(online),
            dead_nodes=[n.node_id for n in dead],
            reassigned_layers=[],
            recovered_nodes=recovered,
            recovery_plans=list(self._recovery_history),
        )
