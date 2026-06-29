"""KV Cache Distribution — shard attention cache across swarm nodes."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json


@dataclass
class KvAllocation:
    node_id: int
    layer_ids: list[int]
    kv_heads: int
    memory_bytes: int
    max_tokens: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "layer_ids": self.layer_ids,
            "kv_heads": self.kv_heads,
            "memory_bytes": self.memory_bytes,
            "max_tokens": self.max_tokens,
        }


@dataclass
class KvCachePlan:
    total_layers: int
    total_kv_heads: int
    node_count: int
    allocations: list[KvAllocation]
    total_memory_bytes: int = 0

    def __post_init__(self):
        self.total_memory_bytes = sum(a.memory_bytes for a in self.allocations)

    @property
    def memory_per_node_bytes(self) -> float:
        return self.total_memory_bytes / max(self.node_count, 1)

    @property
    def total_max_tokens(self) -> int:
        return min(a.max_tokens for a in self.allocations) if self.allocations else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_layers": self.total_layers,
            "total_kv_heads": self.total_kv_heads,
            "node_count": self.node_count,
            "total_memory_bytes": self.total_memory_bytes,
            "memory_per_node_mb": round(self.memory_per_node_bytes / 1024 / 1024, 2),
            "max_generation_tokens": self.total_max_tokens,
            "allocations": [a.to_dict() for a in self.allocations],
        }


class KvCachePlanner:
    """Plan KV cache distribution across swarm nodes."""

    def __init__(self, bytes_per_head: int = 2048, tokens_per_layer: int = 128):
        self.bytes_per_head = bytes_per_head
        self.tokens_per_layer = tokens_per_layer

    def plan(
        self,
        total_layers: int,
        kv_heads: int,
        node_count: int,
        memory_per_node_bytes: int = 524288,
    ) -> KvCachePlan:
        allocations = []
        layers_per_node = (total_layers + node_count - 1) // node_count
        heads_per_node = (kv_heads + node_count - 1) // node_count

        for i in range(node_count):
            layer_start = i * layers_per_node
            layer_end = min((i + 1) * layers_per_node, total_layers)
            assigned_layers = list(range(layer_start, layer_end))

            memory_needed = len(assigned_layers) * heads_per_node * self.bytes_per_head * self.tokens_per_layer
            max_tokens = memory_per_node_bytes // (len(assigned_layers) * heads_per_node * self.bytes_per_head) if assigned_layers else 0

            allocations.append(KvAllocation(
                node_id=i,
                layer_ids=assigned_layers,
                kv_heads=min(heads_per_node, kv_heads),
                memory_bytes=min(memory_needed, memory_per_node_bytes),
                max_tokens=min(max_tokens, self.tokens_per_layer),
            ))

        return KvCachePlan(
            total_layers=total_layers,
            total_kv_heads=kv_heads,
            node_count=node_count,
            allocations=allocations,
        )

    def validate_no_oom(self, plan: KvCachePlan, memory_per_node_bytes: int = 524288) -> list[dict[str, Any]]:
        warnings = []
        for alloc in plan.allocations:
            if alloc.memory_bytes > memory_per_node_bytes:
                warnings.append({
                    "node_id": alloc.node_id,
                    "issue": "OOM_RISK",
                    "message": f"Node {alloc.node_id}: {alloc.memory_bytes} bytes needed, {memory_per_node_bytes} available",
                })
        return warnings
