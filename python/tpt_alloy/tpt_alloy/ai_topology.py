"""AI Swarm Topology Advisor — recommend optimal topology and partitioning strategy for model deployment."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json
import os
from pathlib import Path


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
    partition_strategy: str = "layer"
    """Recommended partition strategy: 'layer', 'head-parallel', or 'hybrid'."""


# Common transformer attention op_type keywords for detection
TRANSFORMER_ATTENTION_KEYWORDS = [
    "attention", "self_attn", "multi_head_attention",
    "mha", "qkv", "attn", "self_attention",
]


def is_transformer_model(op_types: list[str] | None) -> bool:
    """Heuristic: detect if a model is a transformer by checking for attention ops."""
    if op_types is None:
        return False
    lower_types = [t.lower() for t in op_types]
    return any(
        any(kw in t for kw in TRANSFORMER_ATTENTION_KEYWORDS)
        for t in lower_types
    )


def count_attention_layers(op_types: list[str]) -> int:
    """Count how many layers are attention sublayers."""
    lower_types = [t.lower() for t in op_types]
    return sum(
        1 for t in lower_types
        if any(kw in t for kw in TRANSFORMER_ATTENTION_KEYWORDS)
    )


class AITopologyAdvisor:
    """Recommend optimal swarm topology and partition strategy using model profile and constraints."""

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
        op_types: list[str] | None = None,
        num_heads: int = 0,
    ) -> list[TopologyRecommendation]:
        recommendations = []

        is_transformer = is_transformer_model(op_types)
        attn_layer_count = count_attention_layers(op_types) if op_types else 0

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

            # Determine best partition strategy for this topology
            if is_transformer and num_heads > 0 and num_heads >= constraints.node_count:
                # Transformer with enough heads: head-parallel or hybrid
                if attn_layer_count > 0 and layer_count - attn_layer_count > 0:
                    partition_strategy = "hybrid"
                else:
                    partition_strategy = "head-parallel"
                # Head-parallel improves throughput for attention-heavy models
                predicted_latency *= 0.6  # ~40% latency reduction from head parallelism
                confidence = min(confidence + 0.15, 1.0)
            else:
                partition_strategy = "layer"

            score = confidence * (1.0 if latency_ok and power_ok else 0.5)

            reasoning = self._generate_reasoning(
                topo_type, predicted_latency, predicted_power, constraints,
                is_transformer, partition_strategy, num_heads,
            )

            recommendations.append(TopologyRecommendation(
                topology_type=topo_type,
                node_count=constraints.node_count,
                predicted_latency_ms=round(predicted_latency, 2),
                predicted_power_mw=round(predicted_power, 1),
                confidence=round(confidence, 2),
                reasoning=reasoning,
                score=round(score, 3),
                partition_strategy=partition_strategy,
            ))

        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations

    def _generate_reasoning(
        self,
        topo: str,
        latency: float,
        power: float,
        constraints: TopologyConstraints,
        is_transformer: bool,
        partition_strategy: str,
        num_heads: int,
    ) -> str:
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

        if is_transformer:
            if partition_strategy == "head-parallel":
                reasons.append(
                    f"transformer detected — head-parallel recommended "
                    f"({num_heads} heads across {constraints.node_count} nodes)"
                )
            elif partition_strategy == "hybrid":
                reasons.append(
                    f"transformer detected — hybrid recommended "
                    f"(head-parallel for attention, layer-serial for FFN)"
                )

        return "; ".join(reasons)

    def generate_llm_prompt(
        self,
        layer_count: int,
        constraints: TopologyConstraints,
        op_types: list[str] | None = None,
        num_heads: int = 0,
    ) -> str:
        is_transformer = is_transformer_model(op_types)
        strategy_hint = ""
        if is_transformer and num_heads > 0:
            strategy_hint = (
                f"- Model type: transformer ({num_heads} attention heads)\n"
                f"- Recommended strategy: head-parallel or hybrid\n"
            )

        return (
            f"Recommend a swarm topology for neural network deployment:\n"
            f"- Layer count: {layer_count}\n"
            f"- Node count: {constraints.node_count}\n"
            f"- Latency budget: {constraints.latency_budget_ms}ms\n"
            f"- Power budget: {constraints.power_budget_mw}mW\n"
            f"- Form factor: {constraints.form_factor}\n"
            f"{strategy_hint}"
            f"Return JSON: {{\"topology_type\": \"grid2d|star|ring|mesh\", "
            f"\"partition_strategy\": \"layer|head-parallel|hybrid\", "
            f"\"reasoning\": \"...\", \"predicted_latency_ms\": N, \"predicted_power_mw\": N}}"
        )


@dataclass
class SiLRunResult:
    """A single SiL run measurement for topology training data."""
    topology_type: str
    partition_strategy: str
    node_count: int
    layer_count: int
    num_heads: int
    measured_latency_ms: float
    measured_throughput_tps: float
    measured_power_mw: float
    measured_memory_kb: float
    model_name: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_type": self.topology_type,
            "partition_strategy": self.partition_strategy,
            "node_count": self.node_count,
            "layer_count": self.layer_count,
            "num_heads": self.num_heads,
            "measured_latency_ms": self.measured_latency_ms,
            "measured_throughput_tps": self.measured_throughput_tps,
            "measured_power_mw": self.measured_power_mw,
            "measured_memory_kb": self.measured_memory_kb,
            "model_name": self.model_name,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SiLRunResult:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TopologyTrainingData:
    """Accumulated SiL run results for training the topology advisor ML model."""
    results: list[SiLRunResult] = field(default_factory=list)
    data_dir: Path | None = None

    def add(self, result: SiLRunResult) -> None:
        self.results.append(result)
        self._save()

    def _save(self) -> None:
        if self.data_dir is None:
            return
        self.data_dir.mkdir(parents=True, exist_ok=True)
        path = self.data_dir / "topology_training_data.json"
        path.write_text(json.dumps([r.to_dict() for r in self.results], indent=2))

    def load(self) -> None:
        if self.data_dir is None:
            return
        path = self.data_dir / "topology_training_data.json"
        if path.exists():
            try:
                data = json.loads(path.read_text())
                self.results = [SiLRunResult.from_dict(d) for d in data]
            except (json.JSONDecodeError, KeyError):
                self.results = []

    def features_and_labels(self) -> tuple[list[list[float]], list[float]]:
        """Extract feature vectors and latency labels for ML training."""
        features = []
        labels = []
        topo_map = {"grid2d": 0, "star": 1, "ring": 2, "mesh": 3}
        strat_map = {"layer": 0, "head-parallel": 1, "hybrid": 2}
        for r in self.results:
            feat = [
                float(r.node_count),
                float(r.layer_count),
                float(r.num_heads),
                topo_map.get(r.topology_type, 0),
                strat_map.get(r.partition_strategy, 0),
            ]
            features.append(feat)
            labels.append(r.measured_latency_ms)
        return features, labels

    @property
    def size(self) -> int:
        return len(self.results)

    def to_dict(self) -> dict[str, Any]:
        return {"run_count": len(self.results), "results": [r.to_dict() for r in self.results[-10:]]}


class TopologyMLAdvisor:
    """ML-based topology advisor trained on accumulated SiL data.

    Uses a simple ridge regression when enough data is available.
    Falls back to the heuristic advisor when data is insufficient.
    """

    MIN_SAMPLES = 10

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path.home() / ".tpt-crucible" / "topology-training"
        self.training_data = TopologyTrainingData(data_dir=self.data_dir)
        self.training_data.load()
        self._weights: list[list[float]] | None = None
        self._intercept: float = 0.0
        self._trained = False

    def train(self) -> bool:
        """Train the ML model on accumulated SiL data.

        Returns True if training succeeded, False if insufficient data.
        """
        if self.training_data.size < self.MIN_SAMPLES:
            return False

        features, labels = self.training_data.features_and_labels()
        self._weights, self._intercept = self._ridge_regression(features, labels)
        self._trained = True

        checkpoint = {
            "weights": self._weights,
            "intercept": self._intercept,
            "samples": self.training_data.size,
        }
        ckpt_path = self.data_dir / "topology_model.json"
        ckpt_path.write_text(json.dumps(checkpoint, indent=2))
        return True

    def predict_latency(
        self,
        node_count: int,
        layer_count: int,
        num_heads: int,
        topology_type: str,
        partition_strategy: str,
    ) -> float:
        """Predict latency for a given topology configuration."""
        if not self._trained:
            self._load_checkpoint()

        if self._weights is None:
            return 0.0

        topo_map = {"grid2d": 0, "star": 1, "ring": 2, "mesh": 3}
        strat_map = {"layer": 0, "head-parallel": 1, "hybrid": 2}

        feat = [
            float(node_count),
            float(layer_count),
            float(num_heads),
            float(topo_map.get(topology_type, 0)),
            float(strat_map.get(partition_strategy, 0)),
        ]

        pred = self._intercept
        for i, w in enumerate(self._weights):
            if i < len(feat):
                pred += w[0] * feat[i]
        return max(pred, 0.1)

    def _load_checkpoint(self) -> None:
        ckpt_path = self.data_dir / "topology_model.json"
        if ckpt_path.exists():
            try:
                ckpt = json.loads(ckpt_path.read_text())
                self._weights = ckpt["weights"]
                self._intercept = ckpt["intercept"]
                self._trained = True
            except (json.JSONDecodeError, KeyError):
                pass

    @staticmethod
    def _ridge_regression(
        features: list[list[float]],
        labels: list[float],
        alpha: float = 1.0,
    ) -> tuple[list[list[float]], float]:
        """Simple ridge regression without numpy dependency."""
        n = len(features)
        if n == 0:
            return [], 0.0
        d = len(features[0])

        mean_x = [0.0] * d
        mean_y = 0.0
        for i in range(n):
            for j in range(d):
                mean_x[j] += features[i][j]
            mean_y += labels[i]
        mean_x = [m / n for m in mean_x]
        mean_y /= n

        centered_x = [[features[i][j] - mean_x[j] for j in range(d)] for i in range(n)]
        centered_y = [labels[i] - mean_y for i in range(n)]

        weights = [0.0] * d
        for j in range(d):
            dot_xx = sum(centered_x[i][j] ** 2 for i in range(n)) + alpha
            dot_xy = sum(centered_x[i][j] * centered_y[i] for i in range(n))
            weights[j] = dot_xy / dot_xx

        intercept = mean_y - sum(weights[j] * mean_x[j] for j in range(d))
        return [[w] for w in weights], intercept
