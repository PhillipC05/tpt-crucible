"""Tests for TPT Element module."""

import numpy as np

from tpt_element.weight_map import WeightMapper, ComponentType, PhysicalComponent
from tpt_element.spice import SpiceNetlistGenerator, SimulationResult


class TestWeightMapper:
    def test_map_weights(self):
        mapper = WeightMapper(tolerance=0.05)
        weights = np.array([[0.1, 0.2], [0.3, 0.4]])
        components = mapper.map_weights(weights)
        assert len(components) == 4
        assert all(c.component_type == ComponentType.RESISTOR for c in components)

    def test_weight_to_resistance(self):
        mapper = WeightMapper()
        r = mapper._weight_to_resistance(1.0)
        assert r == 1000.0

    def test_zero_weight_infinite_resistance(self):
        mapper = WeightMapper()
        r = mapper._weight_to_resistance(0.0)
        assert r == 1e12

    def test_confidence_score(self):
        mapper = WeightMapper(tolerance=0.05)
        weights = np.array([[0.1, 0.2]])
        components = mapper.map_weights(weights)
        score = mapper.compute_confidence_score(components)
        assert 0.0 <= score <= 1.0


class TestSpiceNetlist:
    def test_generate_netlist(self):
        gen = SpiceNetlistGenerator()
        gen.add_component(PhysicalComponent(
            component_type=ComponentType.RESISTOR,
            value=1000.0,
            unit="ohm",
            tolerance=0.05,
            position=(0, 0),
        ))
        netlist = gen.generate_netlist()
        assert "TPT Element" in netlist
        assert ".end" in netlist

    def test_thermal_noise(self):
        gen = SpiceNetlistGenerator()
        gen.add_component(PhysicalComponent(
            component_type=ComponentType.RESISTOR,
            value=1000.0,
            unit="ohm",
            tolerance=0.05,
            position=(0, 0),
        ))
        results = gen.inject_thermal_noise(300.0)
        assert len(results) == 1
        assert results[0]["thermal_noise_uV"] > 0

    def test_voltage_drift(self):
        gen = SpiceNetlistGenerator()
        gen.add_component(PhysicalComponent(
            component_type=ComponentType.RESISTOR,
            value=1000.0,
            unit="ohm",
            tolerance=0.05,
            position=(0, 0),
        ))
        results = gen.simulate_voltage_drift(hours=24)
        assert len(results) == 1
        assert results[0]["drift_pct"] > 0

    def test_tolerance_impact(self):
        gen = SpiceNetlistGenerator()
        gen.add_component(PhysicalComponent(
            component_type=ComponentType.RESISTOR,
            value=1000.0,
            unit="ohm",
            tolerance=0.05,
            position=(0, 0),
        ))
        results = gen.simulate_tolerance_impact()
        assert len(results) == 1
        assert results[0]["snr_penalty_db"] > 0

    def test_confidence_score(self):
        gen = SpiceNetlistGenerator()
        gen.add_component(PhysicalComponent(
            component_type=ComponentType.RESISTOR,
            value=1000.0,
            unit="ohm",
            tolerance=0.05,
            position=(0, 0),
        ))
        score = gen.compute_confidence_score()
        assert 0.0 <= score <= 1.0

    def test_full_simulation(self):
        gen = SpiceNetlistGenerator()
        gen.add_component(PhysicalComponent(
            component_type=ComponentType.RESISTOR,
            value=1000.0,
            unit="ohm",
            tolerance=0.05,
            position=(0, 0),
        ))
        result = gen.full_simulation()
        assert isinstance(result, SimulationResult)
        assert len(result.thermal_noise) == 1
        assert result.confidence_score > 0

    def test_mitigations(self):
        gen = SpiceNetlistGenerator()
        gen.add_component(PhysicalComponent(
            component_type=ComponentType.RESISTOR,
            value=1000.0,
            unit="ohm",
            tolerance=0.10,
            position=(0, 0),
        ))
        result = gen.full_simulation()
        mitigations = gen.generate_mitigations(result)
        assert len(mitigations) > 0
