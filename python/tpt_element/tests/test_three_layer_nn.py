"""End-to-end test: 3-layer analog neural network through the full Element pipeline.

Topology: 4 → 8 → 4 → 2  (input → hidden1 → hidden2 → output)
Pipeline: WeightMapper → SpiceNetlistGenerator → RealityCheckModel → KiCadExporter
"""

from __future__ import annotations
import tempfile
from pathlib import Path

import numpy as np
import pytest

from tpt_element.weight_map import WeightMapper, ComponentType
from tpt_element.spice import SpiceNetlistGenerator
from tpt_element.reality_check import RealityCheckModel, CircuitFeatures, generate_training_data
from tpt_element.kicad import KiCadExporter


LAYER_SHAPES = [(4, 8), (8, 4), (4, 2)]
LAYER_NAMES = ["input_to_hidden1", "hidden1_to_hidden2", "hidden2_to_output"]

RNG = np.random.default_rng(0)


def build_three_layer_weights() -> list[np.ndarray]:
    return [RNG.standard_normal(shape) * 0.1 for shape in LAYER_SHAPES]


class TestThreeLayerWeightMapping:
    def test_all_layers_mapped(self):
        mapper = WeightMapper(tolerance=0.01)
        all_weights = build_three_layer_weights()
        for weights, (rows, cols) in zip(all_weights, LAYER_SHAPES):
            components = mapper.map_weights(weights)
            assert len(components) == rows * cols

    def test_component_types_are_resistors(self):
        mapper = WeightMapper()
        for weights in build_three_layer_weights():
            components = mapper.map_weights(weights)
            assert all(c.component_type == ComponentType.RESISTOR for c in components)

    def test_positions_are_valid(self):
        mapper = WeightMapper()
        all_weights = build_three_layer_weights()
        for weights, (rows, cols) in zip(all_weights, LAYER_SHAPES):
            components = mapper.map_weights(weights)
            for c in components:
                assert 0 <= c.position[0] < rows
                assert 0 <= c.position[1] < cols

    def test_total_component_count(self):
        mapper = WeightMapper(tolerance=0.05)
        total_expected = sum(r * c for r, c in LAYER_SHAPES)
        total = sum(
            len(mapper.map_weights(w)) for w in build_three_layer_weights()
        )
        assert total == total_expected  # 32 + 32 + 8 = 72

    def test_confidence_score_range(self):
        mapper = WeightMapper(tolerance=0.01)
        for weights in build_three_layer_weights():
            components = mapper.map_weights(weights)
            score = mapper.compute_confidence_score(components)
            assert 0.0 <= score <= 1.0

    def test_tight_tolerance_higher_confidence(self):
        mapper_tight = WeightMapper(tolerance=0.01)
        mapper_loose = WeightMapper(tolerance=0.10)
        weights = build_three_layer_weights()[0]
        tight_score = mapper_tight.compute_confidence_score(mapper_tight.map_weights(weights))
        loose_score = mapper_loose.compute_confidence_score(mapper_loose.map_weights(weights))
        assert tight_score > loose_score


class TestThreeLayerSpiceSimulation:
    def _build_generator(self, tolerance: float = 0.05) -> SpiceNetlistGenerator:
        mapper = WeightMapper(tolerance=tolerance)
        gen = SpiceNetlistGenerator()
        for weights in build_three_layer_weights():
            for comp in mapper.map_weights(weights):
                gen.add_component(comp)
        return gen

    def test_netlist_contains_all_components(self):
        gen = self._build_generator()
        total = sum(r * c for r, c in LAYER_SHAPES)
        assert len(gen.nodes) == total

    def test_netlist_text_valid(self):
        gen = self._build_generator()
        netlist = gen.generate_netlist()
        assert ".title TPT_Analog_NN" in netlist
        assert ".end" in netlist
        assert netlist.count("\nR") == len(gen.nodes)

    def test_thermal_noise_all_nodes(self):
        gen = self._build_generator()
        noise_results = gen.inject_thermal_noise(temperature_k=300.0)
        assert len(noise_results) == len(gen.nodes)
        assert all(r["thermal_noise_uV"] > 0 for r in noise_results)

    def test_thermal_noise_increases_with_temperature(self):
        gen = self._build_generator()
        cool = gen.inject_thermal_noise(temperature_k=200.0)
        hot = gen.inject_thermal_noise(temperature_k=400.0)
        cool_avg = np.mean([r["thermal_noise_uV"] for r in cool])
        hot_avg = np.mean([r["thermal_noise_uV"] for r in hot])
        assert hot_avg > cool_avg

    def test_voltage_drift_all_nodes(self):
        gen = self._build_generator()
        drift = gen.simulate_voltage_drift(hours=24.0, temp_c=25.0)
        assert len(drift) == len(gen.nodes)
        assert all(r["drift_pct"] > 0 for r in drift)

    def test_voltage_drift_increases_over_time(self):
        gen = self._build_generator()
        short = gen.simulate_voltage_drift(hours=1.0)
        long = gen.simulate_voltage_drift(hours=100.0)
        assert np.mean([r["drift_pct"] for r in long]) > np.mean([r["drift_pct"] for r in short])

    def test_tolerance_impact_all_nodes(self):
        gen = self._build_generator(tolerance=0.05)
        tol = gen.simulate_tolerance_impact()
        assert len(tol) == len(gen.nodes)
        assert all(r["snr_penalty_db"] > 0 for r in tol)

    def test_full_simulation_returns_result(self):
        gen = self._build_generator()
        result = gen.full_simulation(temperature_k=300.0, hours=24.0)
        assert len(result.thermal_noise) == len(gen.nodes)
        assert len(result.voltage_drift) == len(gen.nodes)
        assert len(result.tolerance_impact) == len(gen.nodes)
        assert 0.0 <= result.confidence_score <= 1.0

    def test_mitigations_generated(self):
        gen = self._build_generator(tolerance=0.10)
        result = gen.full_simulation(temperature_k=360.0, hours=48.0)
        mitigations = gen.generate_mitigations(result)
        assert len(mitigations) > 0
        assert all(isinstance(m, str) and len(m) > 0 for m in mitigations)

    def test_netlist_saved_to_disk(self, tmp_path):
        gen = self._build_generator()
        out = tmp_path / "three_layer.spice"
        gen.save_netlist(out)
        assert out.exists()
        content = out.read_text()
        assert ".end" in content


class TestThreeLayerRealityCheck:
    def test_trained_model_predicts_for_all_layers(self):
        model = RealityCheckModel()
        features, labels = generate_training_data(n_samples=200)
        model.train(features, labels)

        mapper = WeightMapper(tolerance=0.05)
        for weights, (rows, cols) in zip(build_three_layer_weights(), LAYER_SHAPES):
            components = mapper.map_weights(weights)
            resistances = [c.value for c in components]
            feat = CircuitFeatures(
                resistance_values=resistances,
                tolerance=0.05,
                temperature_k=310.0,
                voltage_v=3.3,
                component_count=len(components),
            )
            pred = model.predict(feat)
            assert 0.0 <= pred.confidence <= 1.0
            assert 0.0 <= pred.failure_probability <= 1.0
            assert len(pred.mitigations) > 0

    def test_higher_temperature_increases_failure_probability(self):
        model = RealityCheckModel()
        features, labels = generate_training_data(n_samples=300)
        model.train(features, labels)

        mapper = WeightMapper(tolerance=0.05)
        resistances = [c.value for c in mapper.map_weights(build_three_layer_weights()[0])]
        base = CircuitFeatures(
            resistance_values=resistances, tolerance=0.05,
            temperature_k=300.0, voltage_v=3.3, component_count=len(resistances),
        )
        hot = CircuitFeatures(
            resistance_values=resistances, tolerance=0.05,
            temperature_k=370.0, voltage_v=3.3, component_count=len(resistances),
        )
        assert model.predict(hot).failure_probability >= model.predict(base).failure_probability


class TestThreeLayerKiCadExport:
    def _build_exporter(self, tolerance: float = 0.05) -> KiCadExporter:
        mapper = WeightMapper(tolerance=tolerance)
        exporter = KiCadExporter(board_width_mm=160.0, board_height_mm=100.0)
        for weights in build_three_layer_weights():
            exporter.add_components(mapper.map_weights(weights))
        return exporter

    def test_component_count_matches(self):
        exporter = self._build_exporter()
        total = sum(r * c for r, c in LAYER_SHAPES)
        assert len(exporter.components) == total

    def test_pcb_text_valid(self):
        exporter = self._build_exporter()
        pcb = exporter.generate_kicad_pcb()
        assert "kicad_pcb" in pcb
        assert "tpt-element" in pcb
        assert pcb.count('(footprint') == len(exporter.components)

    def test_schematic_text_valid(self):
        exporter = self._build_exporter()
        sch = exporter.generate_schematic()
        assert "kicad_sch" in sch
        assert "tpt-element" in sch

    def test_files_saved_to_disk(self, tmp_path):
        exporter = self._build_exporter()
        paths = exporter.save(tmp_path)
        assert paths["pcb"].exists()
        assert paths["schematic"].exists()
        assert paths["pcb"].suffix == ".kicad_pcb"
        assert paths["schematic"].suffix == ".kicad_sch"

    def test_all_references_unique(self):
        exporter = self._build_exporter()
        refs = [c.reference for c in exporter.components]
        assert len(refs) == len(set(refs))

    def test_components_within_board_bounds(self):
        exporter = self._build_exporter()
        for c in exporter.components:
            assert 0 <= c.x <= exporter.board_width
            assert 0 <= c.y <= exporter.board_height


class TestPhase3MilestoneDemo:
    """Full end-to-end pipeline: 3-layer NN → drift simulation → KiCad PCB."""

    def test_full_pipeline(self, tmp_path):
        # 1. Define 3-layer NN weights
        layer_weights = build_three_layer_weights()

        # 2. Map all layers to physical components
        mapper = WeightMapper(tolerance=0.01)
        all_components = []
        for weights in layer_weights:
            all_components.extend(mapper.map_weights(weights))
        assert len(all_components) == 72

        # 3. Build SPICE netlist and run thermal drift simulation
        gen = SpiceNetlistGenerator(vdd=3.3)
        for comp in all_components:
            gen.add_component(comp)
        sim_result = gen.full_simulation(temperature_k=330.0, hours=24.0)
        assert sim_result.confidence_score > 0.0

        # 4. Reality Check: train and predict for each layer
        rc_model = RealityCheckModel()
        rc_features, rc_labels = generate_training_data(n_samples=500)
        rc_model.train(rc_features, rc_labels)
        for weights in layer_weights:
            comps = mapper.map_weights(weights)
            pred = rc_model.predict(CircuitFeatures(
                resistance_values=[c.value for c in comps],
                tolerance=0.01,
                temperature_k=330.0,
                voltage_v=3.3,
                component_count=len(comps),
            ))
            assert pred.confidence >= 0.0

        # 5. Generate mitigations
        mitigations = gen.generate_mitigations(sim_result)
        assert len(mitigations) > 0

        # 6. Export KiCad PCB
        exporter = KiCadExporter(board_width_mm=200.0, board_height_mm=150.0)
        exporter.add_components(all_components)
        saved = exporter.save(tmp_path / "kicad")
        assert saved["pcb"].exists()
        assert saved["schematic"].exists()

        # 7. Save SPICE netlist
        netlist_path = tmp_path / "three_layer_nn.spice"
        gen.save_netlist(netlist_path)
        assert netlist_path.exists()
        assert ".end" in netlist_path.read_text()
