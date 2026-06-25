"""SPICE netlist generation and simulation."""

from __future__ import annotations
import math
from pathlib import Path
from dataclasses import dataclass, field
from .weight_map import PhysicalComponent, ComponentType


@dataclass
class SpiceNode:
    id: str
    component: PhysicalComponent


@dataclass
class SimulationResult:
    thermal_noise: list[dict] = field(default_factory=list)
    voltage_drift: list[dict] = field(default_factory=list)
    tolerance_impact: list[dict] = field(default_factory=list)
    confidence_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "thermal_noise": self.thermal_noise,
            "voltage_drift": self.voltage_drift,
            "tolerance_impact": self.tolerance_impact,
            "confidence_score": self.confidence_score,
        }


class SpiceNetlistGenerator:
    def __init__(self, vdd: float = 3.3, gnd: float = 0.0):
        self.vdd = vdd
        self.gnd = gnd
        self.nodes: list[SpiceNode] = []

    def add_component(self, component: PhysicalComponent) -> None:
        node_id = f"n{len(self.nodes)}"
        self.nodes.append(SpiceNode(id=node_id, component=component))

    def generate_netlist(self) -> str:
        lines = [
            "* TPT Element — Auto-generated SPICE netlist",
            ".title TPT_Analog_NN",
            f"* VDD = {self.vdd}V",
            "",
        ]
        for i, node in enumerate(self.nodes):
            c = node.component
            if c.component_type == ComponentType.RESISTOR:
                lines.append(f"R{i} n{i-1 if i > 0 else 'in'} {node.id} {c.value:.6e}")
            elif c.component_type == ComponentType.OPAMP_GAIN:
                lines.append(f"E{i} {node.id} 0 n{i-1 if i > 0 else 'in'} 0 {c.value:.6e}")
        lines.append("")
        lines.append(f"VDD vdd 0 DC {self.vdd}")
        lines.append(".end")
        return "\n".join(lines)

    def save_netlist(self, path: Path) -> None:
        path.write_text(self.generate_netlist())

    def inject_thermal_noise(self, temperature_k: float = 300.0) -> list[dict]:
        k_boltzmann = 1.380649e-23
        results = []
        for node in self.nodes:
            noise_voltage = math.sqrt(4 * k_boltzmann * temperature_k * node.component.value * 1e3)
            results.append({
                "node": node.id,
                "thermal_noise_uV": noise_voltage * 1e6,
                "temperature_k": temperature_k,
            })
        return results

    def simulate_voltage_drift(self, hours: float = 24.0, temp_c: float = 25.0) -> list[dict]:
        """Simulate voltage drift over time due to temperature and component aging."""
        results = []
        for node in self.nodes:
            c = node.component
            drift_coefficient = 50e-6 if c.component_type == ComponentType.RESISTOR else 10e-6
            temperature_factor = 1.0 + (temp_c - 25.0) * 0.001
            drift_pct = drift_coefficient * hours * temperature_factor * 100
            drift_voltage = self.vdd * drift_pct / 100
            results.append({
                "node": node.id,
                "drift_pct": round(drift_pct, 4),
                "drift_voltage_mV": round(drift_voltage * 1000, 4),
                "hours": hours,
                "temperature_c": temp_c,
            })
        return results

    def simulate_tolerance_impact(self) -> list[dict]:
        """Simulate impact of component tolerance on circuit behavior."""
        results = []
        for node in self.nodes:
            c = node.component
            tolerance = c.tolerance
            max_deviation = c.value * tolerance
            snr_penalty_db = 20 * math.log10(1.0 / (1.0 - tolerance)) if tolerance < 1.0 else float('inf')
            results.append({
                "node": node.id,
                "nominal_value": c.value,
                "tolerance_pct": tolerance * 100,
                "max_deviation": max_deviation,
                "snr_penalty_db": round(snr_penalty_db, 2),
            })
        return results

    def compute_confidence_score(
        self,
        temperature_k: float = 300.0,
        hours: float = 24.0,
    ) -> float:
        """Compute overall confidence score for the analog design."""
        if not self.nodes:
            return 0.0

        thermal = self.inject_thermal_noise(temperature_k)
        drift = self.simulate_voltage_drift(hours)
        tolerance = self.simulate_tolerance_impact()

        max_noise = max(r["thermal_noise_uV"] for r in thermal) if thermal else 0
        max_drift = max(r["drift_pct"] for r in drift) if drift else 0
        max_snr_penalty = max(r["snr_penalty_db"] for r in tolerance) if tolerance else 0

        noise_score = max(0, 1.0 - max_noise / 1000)
        drift_score = max(0, 1.0 - max_drift / 10)
        tolerance_score = max(0, 1.0 - max_snr_penalty / 10)

        confidence = (noise_score * 0.3 + drift_score * 0.3 + tolerance_score * 0.4)
        return round(confidence, 4)

    def full_simulation(
        self,
        temperature_k: float = 300.0,
        hours: float = 24.0,
    ) -> SimulationResult:
        """Run full simulation suite and return combined results."""
        return SimulationResult(
            thermal_noise=self.inject_thermal_noise(temperature_k),
            voltage_drift=self.simulate_voltage_drift(hours),
            tolerance_impact=self.simulate_tolerance_impact(),
            confidence_score=self.compute_confidence_score(temperature_k, hours),
        )

    def generate_mitigations(self, sim_result: SimulationResult) -> list[str]:
        """Generate human-readable mitigation suggestions."""
        mitigations = []

        for noise in sim_result.thermal_noise:
            if noise["thermal_noise_uV"] > 100:
                mitigations.append(
                    f"Node {noise['node']}: High thermal noise ({noise['thermal_noise_uV']:.1f} µV). "
                    f"Consider adding a heatsink or reducing temperature."
                )

        for drift in sim_result.voltage_drift:
            if drift["drift_pct"] > 0.5:
                mitigations.append(
                    f"Node {drift['node']}: Significant voltage drift ({drift['drift_pct']:.2f}% over {drift['hours']}h). "
                    f"Use precision resistors or add voltage regulation."
                )

        for tol in sim_result.tolerance_impact:
            if tol["snr_penalty_db"] > 2:
                mitigations.append(
                    f"Node {tol['node']}: High tolerance penalty ({tol['snr_penalty_db']:.1f} dB SNR loss). "
                    f"Upgrade to 1% tolerance components."
                )

        if not mitigations:
            mitigations.append("No critical issues found. Design appears robust.")

        return mitigations
