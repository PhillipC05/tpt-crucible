"""Write neuromorphic / SNN artifacts into .tptpkg structure."""

from __future__ import annotations
import json
from pathlib import Path

from .lif_node import SnnGraph
from .converter import SnnConverter
from .sim_export import LifSimulator


def write_pulse_artifacts(
    graph: SnnGraph,
    target: str = "sim",
    accuracy_estimate: float | None = None,
    pkg_dir: Path | None = None,
) -> dict[str, str]:
    """Write neuromorphic target artifacts into the package.

    Produces:
        targets/pulse/snn_graph.json         — LIF neuron graph + spike edges
        targets/pulse/config.json            — backend target + neuron count
        targets/pulse/accuracy_estimate.json — predicted accuracy
    """
    artifacts = {}
    pulse_dir = (pkg_dir / "targets" / "pulse") if pkg_dir else Path("targets/pulse")
    pulse_dir.mkdir(parents=True, exist_ok=True)

    graph_path = pulse_dir / "snn_graph.json"
    graph.save(graph_path)
    artifacts["pulse/snn_graph.json"] = str(graph_path)

    config = {
        "target": target,
        "neuron_count": len(graph.neurons),
        "edge_count": len(graph.edges),
        "synapse_count": len(graph.edges),
    }
    config_path = pulse_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2))
    artifacts["pulse/config.json"] = str(config_path)

    if accuracy_estimate is not None:
        acc = {
            "estimated_accuracy": accuracy_estimate,
            "method": "spike_rate_similarity",
            "target_backend": target,
        }
    else:
        acc = {
            "estimated_accuracy": 0.0,
            "method": "not_computed",
            "target_backend": target,
        }

    acc_path = pulse_dir / "accuracy_estimate.json"
    acc_path.write_text(json.dumps(acc, indent=2))
    artifacts["pulse/accuracy_estimate.json"] = str(acc_path)

    return artifacts


def estimate_accuracy(graph: SnnGraph, timesteps: int = 100) -> float:
    """Run a quick SiL simulation to estimate accuracy."""
    simulator = LifSimulator()
    input_spikes = list(range(min(len(graph.neurons), 8)))
    result = simulator.simulate(graph, input_spikes=input_spikes, timesteps=timesteps)
    output = result.to_dict()
    spike_counts = output.get("spike_counts", [])
    if not spike_counts:
        return 0.0
    total_spikes = sum(spike_counts)
    max_possible = len(spike_counts) * timesteps
    return total_spikes / max_possible if max_possible > 0 else 0.0
