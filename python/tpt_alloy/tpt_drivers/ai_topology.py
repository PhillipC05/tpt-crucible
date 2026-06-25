"""AI Swarm Topology Advisor — recommend optimal topology for model deployment."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json


@dataclass
class TopologyConstraints:
    node_count: int = 16
    latency_budget_ms: float = 10.0
    power_budget_mw: float = 5000.0
    form_factor: str = "desktop"
    bandwidth_gbs: float = 1.0


@dataclass
class TopologyRecommendation:
    topology_type: str
    node_count: int
    predicted_latency_ms: float
    predicted_power_mw: float
    confidence: float
    reasoning: str
    score: float = 0.0


class AITopologyAdvisor:
    """Recommend optimal swarm topology using model profile and constraints."""

    def __init__(self):
        self._topology_templates = {
            "grid2d": {"latency_factor": 1.0, "power_factor": 1.0, "bandwidth_factor": 0.8},
            "star": {"latency_factor": 0.6, "power_factor": 1.2, "bandwidth_factor": 1.0},
            "ring": {"latency_factor": 1.5, "power_factor": 0.9, "bandwidth_factor": 0.6},
            "mesh": {"latency_factor": 0.4, "power_factor": 1.5, "bandwidth_factor": 1.2},
        }

    def recommend(
        self,
        layer_count: int,
        tensor_shapes: list[list[int]],
        constraints: TopologyConstraints,
    ) -> list[TopologyRecommendation]:
        recommendations = []

        for topo_type, template in self._topology_templates.items():
            base_latency = (layer_count / constraints.node_count) * 2.0
            predicted_latency = base_latency * template["latency_factor"]
            predicted_power = constraints.node_count * 150 * template["power_factor"]

            latency_ok = predicted_latency <= constraints.latency_budget_ms
            power_ok = predicted_power <= constraints.power_budget_mw

            confidence = 0.5
            if latency_ok:
                confidence += 0.25
            if power_ok:
                confidence += 0.25

            score = confidence * (1.0 if latency_ok and power_ok else 0.5)

            reasoning = self._generate_reasoning(topo_type, predicted_latency, predicted_power, constraints)

            recommendations.append(TopologyRecommendation(
                topology_type=topo_type,
                node_count=constraints.node_count,
                predicted_latency_ms=round(predicted_latency, 2),
                predicted_power_mw=round(predicted_power, 1),
                confidence=round(confidence, 2),
                reasoning=reasoning,
                score=round(score, 3),
            ))

        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations

    def _generate_reasoning(self, topo: str, latency: float, power: float, constraints: TopologyConstraints) -> str:
        reasons = []
        if latency <= constraints.latency_budget_ms * 0.5:
            reasons.append("well within latency budget")
        elif latency <= constraints.latency_budget_ms:
            reasons.append("meets latency budget")
        else:
            reasons.append("exceeds latency budget")

        if power <= constraints.power_budget_mw * 0.5:
            reasons.append("low power consumption")
        elif power <= constraints.power_budget_mw:
            reasons.append("within power budget")
        else:
            reasons.append("exceeds power budget")

        topo_benefits = {
            "grid2d": "good for regular data flow patterns",
            "star": "minimal hop count for centralized aggregation",
            "ring": "simple wiring, predictable latency",
            "mesh": "lowest latency, highest bandwidth",
        }
        reasons.append(topo_benefits.get(topo, ""))

        return "; ".join(reasons)

    def generate_llm_prompt(self, layer_count: int, constraints: TopologyConstraints) -> str:
        return (
            f"Recommend a swarm topology for neural network deployment:\n"
            f"- Layer count: {layer_count}\n"
            f"- Node count: {constraints.node_count}\n"
            f"- Latency budget: {constraints.latency_budget_ms}ms\n"
            f"- Power budget: {constraints.power_budget_mw}mW\n"
            f"- Form factor: {constraints.form_factor}\n\n"
            f"Return JSON: {{\"topology_type\": \"grid2d|star|ring|mesh\", "
            f"\"reasoning\": \"...\", \"predicted_latency_ms\": N, \"predicted_power_mw\": N}}"
        )
