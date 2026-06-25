"""TPT Spark integration — detect Spark models and enable handoff."""

from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SparkModel:
    model_id: str
    name: str
    path: Path
    format: str
    parameter_count: int = 0


class SparkDetector:
    """Detect and list models from TPT Spark's local model library."""

    def __init__(self, spark_model_dir: Path | None = None):
        self.spark_model_dir = spark_model_dir or self._find_spark_dir()

    def _find_spark_dir(self) -> Path | None:
        candidates = [
            Path.home() / ".tpt-spark" / "models",
            Path.home() / "AppData" / "Roaming" / "tpt-spark" / "models",
            Path.home() / ".config" / "tpt-spark" / "models",
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    def list_models(self) -> list[SparkModel]:
        if not self.spark_model_dir or not self.spark_model_dir.exists():
            return []

        models = []
        for p in self.spark_model_dir.iterdir():
            if p.is_file() and p.suffix in (".gguf", ".bin"):
                models.append(SparkModel(
                    model_id=p.stem,
                    name=p.stem,
                    path=p,
                    format=p.suffix.lstrip("."),
                ))
            elif p.is_dir():
                meta = p / "model.json"
                if meta.exists():
                    try:
                        data = json.loads(meta.read_text())
                        models.append(SparkModel(
                            model_id=data.get("id", p.name),
                            name=data.get("name", p.name),
                            path=p,
                            format=data.get("format", "unknown"),
                            parameter_count=data.get("parameter_count", 0),
                        ))
                    except (json.JSONDecodeError, KeyError):
                        pass
        return models

    def get_model(self, model_id: str) -> SparkModel | None:
        for m in self.list_models():
            if m.model_id == model_id:
                return m
        return None


class SparkHandoff:
    """Handle Spark -> Crucible model handoff."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def prepare_model(self, spark_model: SparkModel) -> Path:
        """Prepare a Spark model for Crucible ingestion.

        Returns the path to the model file ready for tpt-catalyst ingest.
        """
        target = self.output_dir / f"{spark_model.model_id}{spark_model.path.suffix}"
        if spark_model.path.is_file():
            import shutil
            shutil.copy2(spark_model.path, target)
        return target

    def create_handoff_manifest(self, spark_model: SparkModel, model_path: Path) -> Path:
        """Create a manifest for the handoff."""
        manifest = {
            "source": "tpt-spark",
            "model_id": spark_model.model_id,
            "model_name": spark_model.name,
            "source_path": str(spark_model.path),
            "prepared_path": str(model_path),
            "format": spark_model.format,
            "parameter_count": spark_model.parameter_count,
        }
        manifest_path = self.output_dir / f"{spark_model.model_id}_handoff.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        return manifest_path
