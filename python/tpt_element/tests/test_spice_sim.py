"""Tests for SPICE simulator integration."""

from pathlib import Path

from tpt_element.spice_sim import SpiceSimulator, SpiceConfig, SpiceRunResult
from tpt_element.spice import SpiceNetlistGenerator
from tpt_element.weight_map import PhysicalComponent, ComponentType


class TestSpiceSimulator:
    def test_detect_backend_none(self):
        sim = SpiceSimulator(SpiceConfig(xyce_path="nonexistent_xyce", ngspice_path="nonexistent_ngspice"))
        backend = sim.detect_backend()
        assert backend == "none"

    def test_simulate_without_backend(self):
        sim = SpiceSimulator(SpiceConfig(xyce_path="nonexistent_xyce", ngspice_path="nonexistent_ngspice"))
        result = sim.simulate_netlist(Path("fake.spice"))
        assert not result.success
        assert result.backend_used == "none"

    def test_simulate_circuit(self):
        sim = SpiceSimulator(SpiceConfig(xyce_path="nonexistent_xyce", ngspice_path="nonexistent_ngspice"))
        gen = SpiceNetlistGenerator()
        gen.add_component(PhysicalComponent(
            component_type=ComponentType.RESISTOR,
            value=1000.0, unit="ohm", tolerance=0.05, position=(0, 0),
        ))
        result = sim.simulate_circuit(gen)
        assert hasattr(result, "thermal_noise")


class TestSpiceConfig:
    def test_default_config(self):
        config = SpiceConfig()
        assert config.backend == "auto"
        assert config.timeout_seconds == 300
