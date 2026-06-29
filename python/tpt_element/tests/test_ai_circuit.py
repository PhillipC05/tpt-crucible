"""Tests for AI circuit designer, JAX hook, and topology advisor data."""

from pathlib import Path
import json

from tpt_element.ai_circuit import (
    AnalogCircuitDesigner, CircuitSpec, CircuitCandidate,
    CircuitDatasetBuilder, TrainingDataEntry,
)
from tpt_train.jax_hook import TPTJaxHook, JaxProfile, JaxLayerStats


class TestAnalogCircuitDesigner:
    def test_generate_candidates(self):
        designer = AnalogCircuitDesigner()
        spec = CircuitSpec(matrix_rows=4, matrix_cols=4)
        candidates = designer.generate_candidates(spec, num_candidates=3)
        assert len(candidates) == 3
        assert candidates[0].confidence >= candidates[-1].confidence

    def test_candidate_has_components(self):
        designer = AnalogCircuitDesigner()
        spec = CircuitSpec(matrix_rows=2, matrix_cols=2)
        candidates = designer.generate_candidates(spec, num_candidates=1)
        assert len(candidates[0].components) > 0

    def test_iterative_refine(self):
        designer = AnalogCircuitDesigner()
        spec = CircuitSpec(matrix_rows=4, matrix_cols=4)
        best = designer.iterative_refine(spec, max_iterations=3)
        assert best.confidence > 0

    def test_predict_failures(self):
        designer = AnalogCircuitDesigner()
        spec = CircuitSpec(matrix_rows=32, matrix_cols=32, precision="int8")
        candidates = designer.generate_candidates(spec, num_candidates=1)
        assert len(candidates[0].failure_modes) > 0


class TestCircuitDatasetBuilder:
    def test_generate_synthetic(self):
        builder = CircuitDatasetBuilder()
        entries = builder.generate_synthetic(count=10)
        assert len(entries) == 10

    def test_to_json(self):
        builder = CircuitDatasetBuilder()
        builder.generate_synthetic(count=5)
        json_str = builder.to_json()
        data = json.loads(json_str)
        assert len(data) == 5


class TestJaxHook:
    def test_record_layer(self):
        hook = TPTJaxHook("test_model")
        import numpy as np
        stats = hook.record_layer("layer0", params=np.array([0.1, 0.2]))
        assert stats.param_count == 2
        assert stats.recommended_bits == 8

    def test_save_profile(self, tmp_path):
        hook = TPTJaxHook("test_model")
        import numpy as np
        hook.record_layer("l0", params=np.array([0.1]))
        hook.step(5)
        path = tmp_path / "profile.json"
        hook.save(path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["epoch"] == 5

    def test_recommend_bits(self):
        hook = TPTJaxHook("test")
        import numpy as np
        small = np.array([0.001])
        stats = hook.record_layer("tiny", params=small)
        assert stats.recommended_bits == 4
