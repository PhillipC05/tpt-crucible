"""TPT Intermediate Representation data structures."""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json


@dataclass
class OpNode:
    id: int
    op_type: str
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    from_id: int
    to_id: int
    tensor_name: str


@dataclass
class ComputationalGraph:
    nodes: list[OpNode] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)


@dataclass
class ModelMetadata:
    name: str
    source_format: str
    parameter_count: int = 0


@dataclass
class TptIr:
    version: str = "1.0.0"
    metadata: ModelMetadata = field(default_factory=lambda: ModelMetadata("", ""))
    graph: ComputationalGraph = field(default_factory=ComputationalGraph)

    def to_json(self) -> str:
        return json.dumps(self._to_dict(), indent=2)

    def save(self, path: Path) -> None:
        path.write_text(self.to_json())

    @classmethod
    def from_json(cls, json_str: str) -> TptIr:
        data = json.loads(json_str)
        metadata = ModelMetadata(**data["metadata"])
        graph = ComputationalGraph(
            nodes=[OpNode(**n) for n in data["graph"]["nodes"]],
            edges=[Edge(from_id=e["from_id"], to_id=e["to_id"], tensor_name=e["tensor_name"]) for e in data["graph"]["edges"]],
        )
        return cls(version=data["version"], metadata=metadata, graph=graph)

    def _to_dict(self) -> dict:
        return {
            "version": self.version,
            "metadata": {
                "name": self.metadata.name,
                "source_format": self.metadata.source_format,
                "parameter_count": self.metadata.parameter_count,
            },
            "graph": {
                "nodes": [
                    {"id": n.id, "op_type": n.op_type, "name": n.name, "attributes": n.attributes}
                    for n in self.graph.nodes
                ],
                "edges": [
                    {"from_id": e.from_id, "to_id": e.to_id, "tensor_name": e.tensor_name}
                    for e in self.graph.edges
                ],
            },
        }
