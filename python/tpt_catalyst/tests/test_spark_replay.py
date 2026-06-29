"""Tests for Spark replay, JLCPCB export, and remaining UI components."""

from pathlib import Path
import json

from tpt_catalyst.spark_replay import SparkReplayLoader, SparkConversation
from tpt_drivers.jlcpcb import JlcpcbExporter


class TestSparkReplay:
    def test_load_conversation(self, tmp_path):
        conv_data = {
            "model": "tinyllama",
            "conversations": [
                {"role": "user", "content": "Hello", "tokens_per_second": 50.0},
                {"role": "assistant", "content": "Hi there", "tokens_per_second": 45.0},
            ],
        }
        conv_file = tmp_path / "conv.json"
        conv_file.write_text(json.dumps(conv_data))

        loader = SparkReplayLoader()
        conv = loader.load_conversation(conv_file)
        assert conv is not None
        assert conv.model_name == "tinyllama"
        assert len(conv.turns) == 2
        assert conv.avg_tps > 0

    def test_get_baselines(self, tmp_path):
        conv_data = {"model": "tinyllama", "conversations": [{"role": "user", "content": "Hi", "tokens_per_second": 50.0}]}
        conv_file = tmp_path / "conv.json"
        conv_file.write_text(json.dumps(conv_data))

        loader = SparkReplayLoader()
        loader.load_conversation(conv_file)
        baselines = loader.get_baselines()
        assert "tinyllama" in baselines
        assert baselines["tinyllama"] == 50.0

    def test_compare_with_crucible(self, tmp_path):
        conv_data = {"model": "tinyllama", "conversations": [{"role": "user", "content": "Hi", "tokens_per_second": 50.0}]}
        conv_file = tmp_path / "conv.json"
        conv_file.write_text(json.dumps(conv_data))

        loader = SparkReplayLoader()
        loader.load_conversation(conv_file)
        result = loader.compare_with_crucible("tinyllama", 120.0)
        assert result["speedup"] == 2.4
        assert result["recommendation"] == "crucible"


class TestJlcpcbExporter:
    def test_add_component(self):
        exporter = JlcpcbExporter()
        exporter.add_component("R1", "1K", "0603", 10.0, 20.0)
        assert len(exporter.bom_items) == 1
        assert len(exporter.cpl_items) == 1

    def test_generate_bom_csv(self):
        exporter = JlcpcbExporter()
        exporter.add_component("R1", "1K", "0603", 10.0, 20.0)
        csv = exporter.generate_bom_csv()
        assert "R1" in csv
        assert "1K" in csv

    def test_generate_cpl_csv(self):
        exporter = JlcpcbExporter()
        exporter.add_component("R1", "1K", "0603", 10.0, 20.0)
        csv = exporter.generate_cpl_csv()
        assert "R1" in csv
        assert "10.0000mm" in csv

    def test_save_all(self, tmp_path):
        exporter = JlcpcbExporter()
        exporter.add_component("R1", "1K", "0603", 10.0, 20.0)
        paths = exporter.save_all(tmp_path)
        assert paths["bom"].exists()
        assert paths["cpl"].exists()
