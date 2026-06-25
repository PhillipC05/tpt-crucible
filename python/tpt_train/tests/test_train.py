"""Tests for tpt-train module."""

import numpy as np
from pathlib import Path

from tpt_train.profile import TptProfile, LayerStats, TptProfileWriter


class TestLayerStats:
    def test_to_dict(self):
        stats = LayerStats(name="layer0", layer_type="Linear", input_min=-1.0, input_max=1.0)
        d = stats.to_dict()
        assert d["name"] == "layer0"
        assert d["input_range"] == [-1.0, 1.0]


class TestTptProfile:
    def test_roundtrip_json(self):
        profile = TptProfile(model_name="test_model", epoch=5)
        profile.layers.append(LayerStats(name="l0", layer_type="Linear", recommended_bits=8))
        json_str = profile.to_json()
        restored = TptProfile.from_json(json_str)
        assert restored.model_name == "test_model"
        assert restored.epoch == 5
        assert len(restored.layers) == 1

    def test_save_and_load(self, tmp_path):
        profile = TptProfile(model_name="test")
        profile.layers.append(LayerStats(name="l0", layer_type="Conv2d"))
        out = tmp_path / "model.tptprofile"
        profile.save(out)
        loaded = TptProfile.from_file(out)
        assert loaded.model_name == "test"


class TestTptProfileWriter:
    def test_record_layer(self):
        writer = TptProfileWriter("test_model")
        input_arr = np.random.randn(1, 64).astype(np.float32)
        weight_arr = np.random.randn(64, 32).astype(np.float32)
        stats = writer.record_layer("fc1", "Linear", input_arr, weight_arr)
        assert stats.name == "fc1"
        assert stats.recommended_bits > 0

    def test_recommend_bits(self):
        writer = TptProfileWriter("test")
        small = np.array([0.001])
        stats = writer.record_layer("tiny", "Linear", small)
        assert stats.recommended_bits == 4

        large = np.array([100.0])
        stats = writer.record_layer("big", "Linear", large)
        assert stats.recommended_bits == 32

    def test_save_profile(self, tmp_path):
        writer = TptProfileWriter("test_model")
        writer.record_layer("l0", "Linear", np.random.randn(1, 16))
        writer.step(10)
        out = tmp_path / "profile.tptprofile"
        writer.save(out)
        assert out.exists()
        loaded = TptProfile.from_file(out)
        assert loaded.epoch == 10
