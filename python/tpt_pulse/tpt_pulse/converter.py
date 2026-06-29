"""SNN Converter — convert ANN layers to spiking neural network."""

from __future__ import annotations
from typing import Any
from .lif_node import LifNeuron, SnnGraph, SpikeEdge


class SnnConverter:
    """Convert ANN operator patterns to SNN graphs."""

    def __init__(self):
        self._neuron_map: dict[int, int] = {}

    def convert(
        self,
        layer_count: int,
        neurons_per_layer: int = 64,
        threshold: float = 1.0,
        decay: float = 0.9,
    ) -> SnnGraph:
        graph = SnnGraph()

        for layer in range(layer_count):
            for n in range(neurons_per_layer):
                neuron = LifNeuron(
                    threshold=threshold,
                    decay=decay,
                    reset_mode="subtract",
                )
                neuron_id = graph.add_neuron(neuron)
                self._neuron_map[f"{layer}_{n}"] = neuron_id

        for layer in range(layer_count - 1):
            for src in range(neurons_per_layer):
                for dst in range(neurons_per_layer):
                    weight = 0.1
                    edge = SpikeEdge(
                        from_neuron=self._neuron_map[f"{layer}_{src}"],
                        to_neuron=self._neuron_map[f"{layer + 1}_{dst}"],
                        weight=weight,
                        delay=1,
                    )
                    graph.add_edge(edge)

        return graph

    def replace_relu_with_lif(self, graph: SnnGraph, threshold: float = 1.0) -> SnnGraph:
        for neuron in graph.neurons:
            neuron.threshold = threshold
        return graph

    def normalize_thresholds(
        self,
        graph: SnnGraph,
        max_activation: float = 1.0,
    ) -> SnnGraph:
        for neuron in graph.neurons:
            neuron.threshold = max_activation * 0.8
        return graph
