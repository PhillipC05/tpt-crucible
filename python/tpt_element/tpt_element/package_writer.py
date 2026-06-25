"""Write Element artifacts into .tptpkg structure."""

from __future__ import annotations
import json
from pathlib import Path
from .spice import SpiceNetlistGenerator
from .weight_map import WeightMapper, PhysicalComponent
import numpy as np


def write_element_artifacts(
    weights: np.ndarray,
    pkg_dir: Path,
    tolerance: float = 0.05,
) -> dict[str, str]:
    """Write netlist, confidence score, and component data into the package."""
    artifacts = {}
    element_dir = pkg_dir / "targets" / "element"
    element_dir.mkdir(parents=True, exist_ok=True)

    mapper = WeightMapper(tolerance=tolerance)
    components = mapper.map_weights(weights)
    confidence = mapper.compute_confidence_score(components)

    gen = SpiceNetlistGenerator()
    for c in components:
        gen.add_component(c)
    sim = gen.full_simulation()

    netlist_path = element_dir / "netlist.spice"
    gen.save_netlist(netlist_path)
    artifacts["element/netlist.spice"] = str(netlist_path)

    confidence_data = {
        "score": confidence,
        "component_count": len(components),
        "tolerance": tolerance,
        "thermal_noise": sim.thermal_noise[:5],
        "voltage_drift": sim.voltage_drift[:5],
    }
    conf_path = element_dir / "confidence.json"
    conf_path.write_text(json.dumps(confidence_data, indent=2))
    artifacts["element/confidence.json"] = str(conf_path)

    return artifacts
