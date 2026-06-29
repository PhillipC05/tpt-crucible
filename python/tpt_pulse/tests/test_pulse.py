"""Tests for TPT Pulse neuromorphic module."""

from tpt_pulse.lif_node import LifNeuron, SnnGraph, SpikeEdge
from tpt_pulse.converter import SnnConverter
from tpt_pulse.sim_export import LifSimulator, SimulationResult


class TestLifNeuron:
    def test_no_spike_below_threshold(self):
        neuron = LifNeuron(threshold=1.0)
        fired = neuron.update(0.5)
        assert fired is False

    def test_spike_above_threshold(self):
        neuron = LifNeuron(threshold=1.0)
        fired = neuron.update(1.5)
        assert fired is True
        assert neuron.spike_count == 1

    def test_subtract_reset(self):
        neuron = LifNeuron(threshold=1.0, reset_mode="subtract")
        neuron.update(1.5)
        assert neuron.bias == 0.5

    def test_zero_reset(self):
        neuron = LifNeuron(threshold=1.0, reset_mode="zero")
        neuron.update(1.5)
        assert neuron.bias == 0.0


class TestSnnGraph:
    def test_add_neuron(self):
        graph = SnnGraph()
        idx = graph.add_neuron(LifNeuron())
        assert idx == 0
        assert len(graph.neurons) == 1

    def test_add_edge(self):
        graph = SnnGraph()
        graph.add_neuron(LifNeuron())
        graph.add_neuron(LifNeuron())
        graph.add_edge(SpikeEdge(from_neuron=0, to_neuron=1, weight=0.5))
        assert len(graph.edges) == 1

    def test_simulate_step(self):
        graph = SnnGraph()
        graph.add_neuron(LifNeuron(threshold=0.5))
        graph.add_edge(SpikeEdge(from_neuron=0, to_neuron=0, weight=1.0))
        spikes = graph.simulate_step()
        assert len(spikes) >= 0

    def test_to_dict(self):
        graph = SnnGraph()
        graph.add_neuron(LifNeuron())
        d = graph.to_dict()
        assert d["neuron_count"] == 1


class TestSnnConverter:
    def test_convert(self):
        converter = SnnConverter()
        graph = converter.convert(layer_count=3, neurons_per_layer=16)
        assert len(graph.neurons) == 48
        assert len(graph.edges) > 0

    def test_replace_relu(self):
        converter = SnnConverter()
        graph = converter.convert(layer_count=2, neurons_per_layer=4)
        graph = converter.replace_relu_with_lif(graph, threshold=2.0)
        for n in graph.neurons:
            assert n.threshold == 2.0


class TestLifSimulator:
    def test_simulate(self):
        converter = SnnConverter()
        graph = converter.convert(layer_count=2, neurons_per_layer=8)
        simulator = LifSimulator()
        result = simulator.simulate(graph, input_spikes=[0, 1, 2], timesteps=50)
        assert result.timesteps == 50
        assert result.total_spikes >= 0

    def test_to_dict(self):
        result = SimulationResult(timesteps=10, total_spikes=5, spike_rate=0.05, per_neuron_spikes={0: 2})
        d = result.to_dict()
        assert d["timesteps"] == 10
        assert d["total_spikes"] == 5
