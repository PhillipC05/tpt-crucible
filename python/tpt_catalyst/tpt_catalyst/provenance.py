"""Model Lineage & Provenance Graph — audit trail of every compilation decision."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any


class StepType(Enum):
    INGEST = "ingest"
    OPTIMIZE = "optimize"
    PREFLIGHT_FIX = "preflight_fix"
    QUANTIZE = "quantize"
    SPARSITY = "sparsity"
    INTERMITTENT = "intermittent"
    PACK = "pack"
    CACHE_HIT = "cache_hit"
    OTA_UPDATE = "ota_update"
    ADAPTIVE_RECOMPILE = "adaptive_recompile"
    CUSTOM = "custom"


@dataclass
class ProvenanceNode:
    step_id: str
    step_type: str
    params: dict[str, Any]
    timestamp: str
    triggered_by: str  # "user", "system", "adaptive", "ci", etc.
    accuracy_delta: float = 0.0
    notes: str = ""
    parent_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class ProvenanceGraph:
    """
    Directed acyclic graph recording every transformation applied to a model
    from raw weights through to a compiled .tptpkg.

    Serialized to `provenance/lineage.json` inside the package.
    """

    model_sha256: str
    nodes: list[ProvenanceNode] = field(default_factory=list)

    def append_step(
        self,
        step_type: StepType | str,
        params: dict[str, Any],
        triggered_by: str = "user",
        accuracy_delta: float = 0.0,
        notes: str = "",
        parent_ids: list[str] | None = None,
    ) -> ProvenanceNode:
        step_id = _make_step_id(step_type, params)
        node = ProvenanceNode(
            step_id=step_id,
            step_type=step_type.value if isinstance(step_type, StepType) else step_type,
            params=params,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            triggered_by=triggered_by,
            accuracy_delta=accuracy_delta,
            notes=notes,
            parent_ids=parent_ids or ([self.nodes[-1].step_id] if self.nodes else []),
        )
        self.nodes.append(node)
        return node

    @property
    def total_accuracy_delta(self) -> float:
        return sum(n.accuracy_delta for n in self.nodes)

    @property
    def root_sha(self) -> str:
        return self.model_sha256

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_sha256": self.model_sha256,
            "nodes": [n.to_dict() for n in self.nodes],
            "total_accuracy_delta": round(self.total_accuracy_delta, 6),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, raw: str) -> "ProvenanceGraph":
        data = json.loads(raw)
        graph = cls(model_sha256=data["model_sha256"])
        for nd in data.get("nodes", []):
            node = ProvenanceNode(
                step_id=nd["step_id"],
                step_type=nd["step_type"],
                params=nd.get("params", {}),
                timestamp=nd.get("timestamp", ""),
                triggered_by=nd.get("triggered_by", "unknown"),
                accuracy_delta=nd.get("accuracy_delta", 0.0),
                notes=nd.get("notes", ""),
                parent_ids=nd.get("parent_ids", []),
            )
            graph.nodes.append(node)
        return graph

    @classmethod
    def from_file(cls, path: Path | str) -> "ProvenanceGraph":
        return cls.from_json(Path(path).read_text())

    def save(self, path: Path | str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json())

    def print_tree(self, *, indent: int = 2) -> None:
        print(f"Provenance for model {self.model_sha256[:12]}…")
        pad = " " * indent
        for i, node in enumerate(self.nodes):
            arrow = "└─" if i == len(self.nodes) - 1 else "├─"
            delta_str = (
                f"  Δacc={node.accuracy_delta:+.3%}" if node.accuracy_delta else ""
            )
            print(f"{pad}{arrow} [{node.step_type}] {node.step_id[:8]}… ({node.triggered_by}){delta_str}")
            for k, v in node.params.items():
                print(f"{pad}   {k}: {v}")

    def diff(self, other: "ProvenanceGraph") -> list[dict[str, Any]]:
        """Return steps present in other but not in self (by step_id)."""
        self_ids = {n.step_id for n in self.nodes}
        return [n.to_dict() for n in other.nodes if n.step_id not in self_ids]


def _make_step_id(step_type: StepType | str, params: dict[str, Any]) -> str:
    key = f"{step_type}:{json.dumps(params, sort_keys=True)}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def graph_for_model(model_path: Path | str) -> ProvenanceGraph:
    """Create a new ProvenanceGraph seeded with the source model SHA-256."""
    p = Path(model_path)
    sha = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "unknown"
    graph = ProvenanceGraph(model_sha256=sha)
    graph.append_step(
        StepType.INGEST,
        params={"source": str(p), "format": p.suffix.lstrip(".")},
        triggered_by="user",
        notes=f"Source model ingested from {p.name}",
    )
    return graph
