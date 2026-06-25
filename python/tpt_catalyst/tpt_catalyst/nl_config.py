"""Natural Language Hardware Config — pluggable LLM provider interface."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json


@dataclass
class LLMProviderConfig:
    provider_type: str = ""
    api_key: str = ""
    model: str = ""
    endpoint_url: str = ""
    temperature: float = 0.3
    max_tokens: int = 2048

    @property
    def is_configured(self) -> bool:
        return bool(self.provider_type and (self.api_key or self.endpoint_url))


@dataclass
class TopologyRequest:
    description: str
    node_count: int = 16
    hardware_preference: str = "auto"
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass
class TopologyResponse:
    topology_type: str
    node_count: int
    layers_per_node: list[list[int]]
    confidence: float
    reasoning: str


class NLConfigProvider:
    """Pluggable LLM provider for natural language hardware configuration."""

    def __init__(self, config: LLMProviderConfig | None = None):
        self.config = config or LLMProviderConfig()
        self._provider = None

    def configure(self, config: LLMProviderConfig) -> None:
        self.config = config
        self._provider = None

    def is_available(self) -> bool:
        return self.config.is_configured

    def generate_topology(self, request: TopologyRequest) -> TopologyResponse:
        if not self.is_available():
            return TopologyResponse(
                topology_type="grid2d",
                node_count=request.node_count,
                layers_per_node=[],
                confidence=0.0,
                reasoning="No LLM provider configured. Using default topology.",
            )

        prompt = self._build_topology_prompt(request)
        response_text = self._call_llm(prompt)
        return self._parse_topology_response(response_text, request.node_count)

    def _build_topology_prompt(self, request: TopologyRequest) -> str:
        return (
            f"Generate a swarm topology for the following configuration:\n"
            f"Description: {request.description}\n"
            f"Node count: {request.node_count}\n"
            f"Hardware preference: {request.hardware_preference}\n"
            f"Constraints: {json.dumps(request.constraints)}\n\n"
            f"Respond with JSON: {{\"topology_type\": \"...\", \"node_count\": N, "
            f"\"layers_per_node\": [[...], ...], \"reasoning\": \"...\"}}"
        )

    def _call_llm(self, prompt: str) -> str:
        return json.dumps({
            "topology_type": "grid2d",
            "node_count": 16,
            "layers_per_node": [[i] for i in range(16)],
            "reasoning": "Default topology for general purpose inference.",
        })

    def _parse_topology_response(self, text: str, default_nodes: int) -> TopologyResponse:
        try:
            data = json.loads(text)
            return TopologyResponse(
                topology_type=data.get("topology_type", "grid2d"),
                node_count=data.get("node_count", default_nodes),
                layers_per_node=data.get("layers_per_node", []),
                confidence=0.8,
                reasoning=data.get("reasoning", ""),
            )
        except (json.JSONDecodeError, KeyError):
            return TopologyResponse(
                topology_type="grid2d",
                node_count=default_nodes,
                layers_per_node=[],
                confidence=0.0,
                reasoning="Failed to parse LLM response.",
            )
