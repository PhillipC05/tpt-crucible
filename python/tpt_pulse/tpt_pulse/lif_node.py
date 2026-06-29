"""LIF Neuron and SNN Graph for neuromorphic computing."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json


@dataclass
class LifNeuron:
    threshold: float = 1.0
    decay: float = 0.9
    reset_mode: str = "subtract"
    bias: float = 0.0
    spike_count: int = 0

    def update(self, input_current: float) -> bool:
        self.bias += input_current
        if self.bias >= self.threshold:
            self.spike_count += 1
            if self.reset_mode == "subtract":
                self.bias -= self.threshold
            else:
                self.bias = 0.0
            return True
        self.bias *= self.decay
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold": self.threshold,
            "decay": self.decay,
            "reset_mode": self.reset_mode,
            "bias": self.bias,
        }


@dataclass
class SpikeEdge:
    from_neuron: int
    to_neuron: int
    weight: float
    delay: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_neuron": self.from_neuron,
            "to_neuron": self.to_neuron,
            "weight": self.weight,
            "delay": self.delay,
        }


@dataclass
class SnnGraph:
    neurons: list[LifNeuron] = field(default_factory=list)
    edges: list[SpikeEdge] = field(default_factory=list)

    def add_neuron(self, neuron: LifNeuron) -> int:
        idx = len(self.neurons)
        self.neurons.append(neuron)
        return idx

    def add_edge(self, edge: SpikeEdge) -> None:
        self.edges.append(edge)

    def simulate_step(self) -> list[int]:
        spikes = []
        for i, neuron in enumerate(self.neurons):
            input_current = sum(
                e.weight for e in self.edges if e.to_neuron == i
            )
            if neuron.update(input_current):
                spikes.append(i)
        return spikes

    def to_dict(self) -> dict[str, Any]:
        return {
            "neuron_count": len(self.neurons),
            "edge_count": len(self.edges),
            "neurons": [n.to_dict() for n in self.neurons],
            "edges": [e.to_dict() for e in self.edges],
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2))
