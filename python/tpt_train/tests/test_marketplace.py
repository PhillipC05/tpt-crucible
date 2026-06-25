"""Tests for marketplace, quickstart, and HW-in-loop training."""

from pathlib import Path
import json

from tpt_train.hardware_aware import (
    LayerDeviation, DeviationProfile, TPTHardwareAwareCallback,
)
from tpt_catalyst.marketplace import Marketplace, MarketplacePackage, BUILTIN_PACKAGES
from tpt_catalyst.quickstart import print_quickstart, check_prerequisites


class TestLayerDeviation:
    def test_mse_computation(self):
        dev = LayerDeviation(
            layer_name="layer0",
            hardware_output=[1.0, 2.0, 3.0],
            reference_output=[1.1, 2.1, 3.1],
        )
        assert dev.mse > 0
        assert dev.cosine_similarity > 0.9

    def test_perfect_match(self):
        dev = LayerDeviation(
            layer_name="layer0",
            hardware_output=[1.0, 2.0],
            reference_output=[1.0, 2.0],
        )
        assert dev.mse == 0.0
        assert dev.cosine_similarity > 0.999


class TestDeviationProfile:
    def test_to_dict_roundtrip(self):
        profile = DeviationProfile(
            model_name="test",
            hardware_target="alloy",
            layer_deviations=[
                LayerDeviation("l0", [1.0], [1.1]),
                LayerDeviation("l1", [2.0], [2.2]),
            ],
        )
        d = profile.to_dict()
        assert d["total_mse"] > 0
        assert d["avg_cosine"] > 0

    def test_save_and_load(self, tmp_path):
        profile = DeviationProfile(
            model_name="test", hardware_target="alloy",
            layer_deviations=[LayerDeviation("l0", [1.0], [1.1])],
        )
        path = tmp_path / "deviation.json"
        profile.save(path)
        loaded = DeviationProfile.load(path)
        assert loaded.model_name == "test"


class TestHardwareAwareCallback:
    def test_suggest_focus_layers(self):
        profile = DeviationProfile(
            model_name="test", hardware_target="alloy",
            layer_deviations=[
                LayerDeviation("l0", [1.0], [5.0]),
                LayerDeviation("l1", [1.0], [1.1]),
                LayerDeviation("l2", [1.0], [10.0]),
            ],
        )
        callback = TPTHardwareAwareCallback(profile)
        focus = callback.suggest_focus_layers(top_n=2)
        assert "l2" in focus
        assert "l0" in focus

    def test_layer_importance(self):
        profile = DeviationProfile(
            model_name="test", hardware_target="alloy",
            layer_deviations=[
                LayerDeviation("l0", [1.0], [5.0]),
                LayerDeviation("l1", [1.0], [1.1]),
            ],
        )
        callback = TPTHardwareAwareCallback(profile)
        importance = callback.get_layer_importance()
        assert importance["l0"] > importance["l1"]


class TestMarketplace:
    def test_list_packages(self):
        mp = Marketplace(cache_dir=Path("/tmp/test_mp"))
        packages = mp.list_packages()
        assert len(packages) >= 3

    def test_search(self):
        mp = Marketplace(cache_dir=Path("/tmp/test_mp"))
        results = mp.search("tinyllama")
        assert len(results) >= 1

    def test_get_package(self):
        mp = Marketplace(cache_dir=Path("/tmp/test_mp"))
        pkg = mp.get_package("tinyllama-q4-esp32x16")
        assert pkg is not None
        assert pkg.hardware_target == "alloy"

    def test_get_popular(self):
        mp = Marketplace(cache_dir=Path("/tmp/test_mp"))
        popular = mp.get_popular(limit=2)
        assert len(popular) == 2
        assert popular[0].downloads >= popular[1].downloads

    def test_builtin_packages(self):
        assert len(BUILTIN_PACKAGES) >= 3


class TestQuickstart:
    def test_print_quickstart(self, capsys):
        print_quickstart()
        captured = capsys.readouterr()
        assert "TPT CRUCIBLE" in captured.out
        assert "Step 1" in captured.out

    def test_check_prerequisites(self):
        prereqs = check_prerequisites()
        assert "Python" in prereqs
        assert prereqs["Python"] is True
