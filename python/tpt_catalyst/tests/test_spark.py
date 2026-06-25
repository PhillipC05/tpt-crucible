"""Tests for TPT Spark integration."""

from pathlib import Path
from tpt_catalyst.spark_integration import SparkDetector, SparkHandoff, SparkModel


class TestSparkDetector:
    def test_no_spark_dir(self, tmp_path):
        detector = SparkDetector(spark_model_dir=tmp_path / "nonexistent")
        assert detector.list_models() == []

    def test_detect_gguf_models(self, tmp_path):
        (tmp_path / "llama3-8b.gguf").write_bytes(b"")
        (tmp_path / "tinyllama.gguf").write_bytes(b"")
        detector = SparkDetector(spark_model_dir=tmp_path)
        models = detector.list_models()
        assert len(models) == 2
        assert any(m.model_id == "llama3-8b" for m in models)

    def test_get_model(self, tmp_path):
        (tmp_path / "model.gguf").write_bytes(b"")
        detector = SparkDetector(spark_model_dir=tmp_path)
        m = detector.get_model("model")
        assert m is not None
        assert m.format == "gguf"


class TestSparkHandoff:
    def test_prepare_model(self, tmp_path):
        src = tmp_path / "src" / "model.gguf"
        src.parent.mkdir()
        src.write_bytes(b"test data")
        spark_model = SparkModel(model_id="model", name="Model", path=src, format="gguf")

        handoff = SparkHandoff(tmp_path / "output")
        target = handoff.prepare_model(spark_model)
        assert target.exists()
        assert target.read_bytes() == b"test data"

    def test_create_manifest(self, tmp_path):
        src = tmp_path / "model.gguf"
        src.write_bytes(b"")
        spark_model = SparkModel(model_id="model", name="Model", path=src, format="gguf")

        handoff = SparkHandoff(tmp_path / "output")
        manifest_path = handoff.create_handoff_manifest(spark_model, src)
        assert manifest_path.exists()
        import json
        data = json.loads(manifest_path.read_text())
        assert data["source"] == "tpt-spark"
