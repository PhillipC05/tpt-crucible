"""Natural Language Topology — generate topology from text description."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json


@dataclass
class TopologyRequest:
    description: str
    node_count: int = 16
    hardware_preference: str = "auto"
    constraints: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "node_count": self.node_count,
            "hardware_preference": self.hardware_preference,
            "constraints": self.constraints,
        }


@dataclass
class TopologyResponse:
    topology_type: str
    node_count: int
    layers_per_node: list[list[int]]
    confidence: float
    reasoning: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_type": self.topology_type,
            "node_count": self.node_count,
            "layers_per_node": self.layers_per_node,
            "confidence": round(self.confidence, 2),
            "reasoning": self.reasoning,
        }


class NLTopologyGenerator:
    """Generate topology configuration from natural language description."""

    KEYWORD_TOPOLOGY_MAP = {
        "grid": "grid2d",
        "mesh": "mesh",
        "star": "star",
        "ring": "ring",
        "linear": "ring",
        "centralized": "star",
        "distributed": "mesh",
        "regular": "grid2d",
    }

    def generate(self, request: TopologyRequest) -> TopologyResponse:
        topology_type = self._extract_topology_type(request.description)
        node_count = self._extract_node_count(request.description) or request.node_count

        layers_per_node = []
        layers_per_node = [[i] for i in range(node_count)]

        reasoning = self._generate_reasoning(topology_type, node_count, request.description)

        return TopologyResponse(
            topology_type=topology_type,
            node_count=node_count,
            layers_per_node=layers_per_node,
            confidence=0.8 if topology_type != "grid2d" else 0.6,
            reasoning=reasoning,
        )

    def _extract_topology_type(self, description: str) -> str:
        desc_lower = description.lower()
        for keyword, topo_type in self.KEYWORD_TOPOLOGY_MAP.items():
            if keyword in desc_lower:
                return topo_type
        return "grid2d"

    def _extract_node_count(self, description: str) -> int | None:
        words = description.lower().split()
        for i, word in enumerate(words):
            if word in ("nodes", "node", "chips", "mcus", "devices"):
                if i > 0:
                    try:
                        return int(words[i - 1])
                    except ValueError:
                        pass
        return None

    def _generate_reasoning(self, topology_type: str, node_count: int, description: str) -> str:
        reasons = {
            "grid2d": f"Selected 2D grid topology for {node_count} nodes — regular data flow patterns",
            "star": f"Selected star topology for {node_count} nodes — minimal hop count for centralized aggregation",
            "ring": f"Selected ring topology for {node_count} nodes — simple wiring, predictable latency",
            "mesh": f"Selected mesh topology for {node_count} nodes — lowest latency, highest bandwidth",
        }
        return reasons.get(topology_type, f"Default topology for {node_count} nodes")

    def generate_llm_prompt(self, request: TopologyRequest) -> str:
        return (
            f"Generate a swarm topology for the following configuration:\n"
            f"Description: {request.description}\n"
            f"Node count: {request.node_count}\n"
            f"Hardware preference: {request.hardware_preference}\n"
            f"Constraints: {json.dumps(request.constraints)}\n\n"
            f"Respond with JSON: {{\"topology_type\": \"grid2d|star|ring|mesh\", "
            f"\"reasoning\": \"...\", \"predicted_latency_ms\": N, \"predicted_power_mw\": N}}"
        )
