"""Tests for Reality Check ML model."""

import numpy as np
from pathlib import Path

from tpt_element.reality_check import (
    RealityCheckModel,
    CircuitFeatures,
    DriftPrediction,
    generate_training_data,
)


class TestRealityCheckModel:
    def test_untrained_returns_default(self):
        model = RealityCheckModel()
        features = CircuitFeatures(
            resistance_values=[1000.0, 2000.0],
            tolerance=0.05,
            temperature_k=300.0,
            voltage_v=3.3,
            component_count=2,
        )
        pred = model.predict(features)
        assert pred.confidence == 0.0

    def test_train_and_predict(self):
        features_list, drifts = generate_training_data(200)
        model = RealityCheckModel()
        model.train(features_list, drifts)

        test_features = CircuitFeatures(
            resistance_values=[1000.0, 2000.0, 500.0],
            tolerance=0.05,
            temperature_k=310.0,
            voltage_v=3.3,
            component_count=3,
        )
        pred = model.predict(test_features)
        assert pred.confidence > 0
        assert pred.failure_probability >= 0
        assert len(pred.mitigations) > 0

    def test_save_and_load(self, tmp_path):
        features_list, drifts = generate_training_data(100)
        model = RealityCheckModel()
        model.train(features_list, drifts)

        model_path = tmp_path / "model.npz"
        model.save(model_path)
        assert model_path.exists()

        loaded = RealityCheckModel()
        loaded.load(model_path)
        features = CircuitFeatures(
            resistance_values=[1000.0],
            tolerance=0.05,
            temperature_k=300.0,
            voltage_v=3.3,
            component_count=1,
        )
        pred = loaded.predict(features)
        assert pred.confidence > 0


class TestGenerateTrainingData:
    def test_generates_correct_count(self):
        features, drifts = generate_training_data(50)
        assert len(features) == 50
        assert len(drifts) == 50

    def test_features_have_valid_data(self):
        features, _ = generate_training_data(10)
        for f in features:
            assert len(f.resistance_values) >= 4
            assert f.tolerance in (0.01, 0.05, 0.10)
            assert 273 <= f.temperature_k <= 373
