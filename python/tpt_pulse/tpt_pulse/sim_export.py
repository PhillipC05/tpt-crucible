"""Pure-Python LIF simulation for SiL testing."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import json

from .lif_node import SnnGraph


@dataclass
class SimulationResult:
    timesteps: int
    total_spikes: int
    spike_rate: float
    per_neuron_spikes: dict[int, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timesteps": self.timesteps,
            "total_spikes": self.total_spikes,
            "spike_rate": round(self.spike_rate, 4),
            "neuron_spikes": self.per_neuron_spikes,
        }


class LifSimulator:
    """Simulate SNN inference using pure Python."""

    def __init__(self):
        self.results: list[dict[str, Any]] = []

    def simulate(
        self,
        graph: SnnGraph,
        input_spikes: list[int],
        timesteps: int = 100,
    ) -> SimulationResult:
        neuron_spikes: dict[int, int] = {i: 0 for i in range(len(graph.neurons))}
        total_spikes = 0

        for t in range(timesteps):
            for neuron_id in input_spikes:
                if neuron_id < len(graph.neurons):
                    graph.neurons[neuron_id].bias += 1.0

            spikes = graph.simulate_step()
            for spike in spikes:
                neuron_spikes[spike] = neuron_spikes.get(spike, 0) + 1
                total_spikes += 1

            self.results.append({
                "timestep": t,
                "spikes": spikes,
                "spike_count": len(spikes),
            })

        spike_rate = total_spikes / max(timesteps * len(graph.neurons), 1)

        return SimulationResult(
            timesteps=timesteps,
            total_spikes=total_spikes,
            spike_rate=spike_rate,
            per_neuron_spikes=neuron_spikes,
        )

    def get_results(self) -> list[dict[str, Any]]:
        return self.results
