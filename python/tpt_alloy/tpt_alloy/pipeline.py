"""Pipeline Parallelism — rolling token window across the node chain."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json
from pathlib import Path

from .partition import Partition, PartitionConfig, partition_model


@dataclass
class PipelineStage:
    node_id: int
    layers: list[int]
    stage_index: int
    buffer_size: int = 1
    kv_memory_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "stage_index": self.stage_index,
            "layers": self.layers,
            "buffer_size": self.buffer_size,
            "kv_memory_bytes": self.kv_memory_bytes,
        }


@dataclass
class PipelineConfig:
    pipeline_depth: int = 4
    """Number of in-flight tokens simultaneously buffered across stages."""
    chunk_size: int = 1
    """Tokens processed per stage per cycle."""

    @property
    def default_depth(self) -> int:
        return self.pipeline_depth


@dataclass
class PipelineSchedule:
    stages: list[PipelineStage]
    depth: int
    total_tokens: int = 0
    bubble_cycles: int = 0

    @property
    def utilization(self) -> float:
        if self.total_tokens == 0:
            return 0.0
        active = self.total_tokens - self.bubble_cycles
        return active / self.total_tokens if self.total_tokens > 0 else 0.0

    @property
    def pipeline_bubble_pct(self) -> float:
        return (1.0 - self.utilization) * 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "depth": self.depth,
            "stage_count": len(self.stages),
            "stages": [s.to_dict() for s in self.stages],
            "utilization": round(self.utilization, 4),
            "pipeline_bubble_pct": round(self.pipeline_bubble_pct, 2),
            "total_tokens": self.total_tokens,
        }


def build_pipeline_schedule(
    partitions: list[Partition],
    config: PipelineConfig | None = None,
    kv_bytes_per_token: int = 128,
) -> PipelineSchedule:
    """Build a pipeline schedule from partitions.

    Assigns stages in order of node_id. The pipeline depth defaults to
    min(node_count, 4) if not specified.
    """
    config = config or PipelineConfig()
    depth = min(config.pipeline_depth, len(partitions))

    stages = []
    for i, p in enumerate(partitions):
        stages.append(PipelineStage(
            node_id=p.node_id,
            layers=p.assigned_layers,
            stage_index=i,
            buffer_size=depth,
            kv_memory_bytes=depth * kv_bytes_per_token * 1024,
        ))

    num_layers = sum(len(p.assigned_layers) for p in partitions)
    total_tokens = num_layers * config.chunk_size
    bubble = max(0, depth - 1)

    return PipelineSchedule(
        stages=stages,
        depth=depth,
        total_tokens=total_tokens,
        bubble_cycles=bubble,
    )


def save_pipeline_config(schedule: PipelineSchedule, path: Path) -> None:
    """Save pipeline config into topology.json-compatible format."""
    data = schedule.to_dict()
    path.write_text(json.dumps(data, indent=2))


def estimate_psram_usage(
    schedule: PipelineSchedule,
    model_hidden_size: int = 2048,
    num_kv_heads: int = 8,
    head_dim: int = 64,
) -> dict[str, Any]:
    """Estimate PSRAM usage per node for pipeline state buffering."""
    kv_per_token = num_kv_heads * head_dim * 2 * 4  # K + V, float32
    per_node: list[dict[str, Any]] = []

    for stage in schedule.stages:
        kv_bytes = schedule.depth * kv_per_token * 1024
        per_node.append({
            "node_id": stage.node_id,
            "kv_buffer_bytes": kv_bytes,
            "kv_buffer_kb": kv_bytes / 1024,
            "activation_bytes": model_hidden_size * 4 * schedule.depth,
            "activation_kb": (model_hidden_size * 4 * schedule.depth) / 1024,
        })

    return {
        "pipeline_depth": schedule.depth,
        "per_node": per_node,
        "total_kv_bytes": sum(n["kv_buffer_bytes"] for n in per_node),
    }
