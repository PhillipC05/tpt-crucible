"""TPT Spark Benchmark — compare Spark vs Crucible performance."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json
from pathlib import Path


@dataclass
class SparkBaseline:
    model_name: str
    tokens_per_second: float
    hardware: str
    quantization: str = ""
    date: str = ""
    time_to_first_token_ms: float = 0.0
    source_file: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "tokens_per_second": round(self.tokens_per_second, 2),
            "hardware": self.hardware,
            "quantization": self.quantization,
            "date": self.date,
            "time_to_first_token_ms": round(self.time_to_first_token_ms, 2),
        }

    def display_label(self) -> str:
        """Human-readable source label for Observer benchmark panel."""
        parts = ["GPU reference: TPT Spark"]
        if self.date:
            parts.append(self.date)
        if self.hardware:
            parts.append(self.hardware)
        parts.append(f"{self.tokens_per_second:.1f} tok/s")
        return ", ".join(parts)


@dataclass
class BenchmarkComparison:
    spark: SparkBaseline
    crucible: SparkBaseline
    speedup: float = 0.0
    efficiency: float = 0.0

    def __post_init__(self):
        if self.spark.tokens_per_second > 0:
            self.speedup = self.crucible.tokens_per_second / self.spark.tokens_per_second
            self.efficiency = self.speedup / (self.crucible.hardware != "GPU")

    def to_dict(self) -> dict[str, Any]:
        return {
            "spark": self.spark.to_dict(),
            "crucible": self.crucible.to_dict(),
            "speedup": round(self.speedup, 2),
        }


# Shared benchmark directory written by TPT Spark.
BENCHMARKS_DIR = Path.home() / ".tpt" / "benchmarks"


class SparkBenchmark:
    """Compare Spark GPU/CPU performance against Crucible custom hardware."""

    def __init__(self, spark_model_dir: Path | None = None):
        self.spark_model_dir = spark_model_dir or Path.home() / ".tpt-spark"
        self._baselines: dict[str, SparkBaseline] = {}

    # ------------------------------------------------------------------
    # Primary path: ~/.tpt/benchmarks/spark-{date}.json
    # ------------------------------------------------------------------

    def load_baselines_from_benchmarks_dir(self, benchmarks_dir: Path | None = None) -> dict[str, SparkBaseline]:
        """Scan ~/.tpt/benchmarks/spark-{date}.json files.

        For each model, keeps only the most recent record (latest date suffix).
        Falls back gracefully when the directory doesn't exist.
        """
        directory = benchmarks_dir or BENCHMARKS_DIR
        if not directory.exists():
            return {}

        # Collect all spark-*.json files, sort by name (date is in the name).
        files = sorted(directory.glob("spark-*.json"))
        baselines: dict[str, SparkBaseline] = {}

        for f in files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                # File may contain a single record or a list of records.
                records = data if isinstance(data, list) else [data]
                for record in records:
                    model_name = record.get("model_name") or record.get("model", f.stem)
                    tps = float(record.get("tokens_per_second", 0))
                    ttft = float(record.get("time_to_first_token_ms", 0))
                    if tps > 0:
                        baselines[model_name] = SparkBaseline(
                            model_name=model_name,
                            tokens_per_second=tps,
                            hardware=record.get("hardware", record.get("gpu", "GPU")),
                            quantization=record.get("quantization", ""),
                            date=record.get("date", _date_from_filename(f.name)),
                            time_to_first_token_ms=ttft,
                            source_file=str(f),
                        )
            except (json.JSONDecodeError, OSError, KeyError, ValueError):
                continue

        self._baselines.update(baselines)
        return baselines

    # ------------------------------------------------------------------
    # Legacy path: ~/.tpt-spark/conversations/*.json
    # ------------------------------------------------------------------

    def load_baselines(self) -> dict[str, SparkBaseline]:
        """Load baselines from Spark's legacy conversation JSON directory."""
        conversations_dir = self.spark_model_dir / "conversations"
        if not conversations_dir.exists():
            return {}

        for f in conversations_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                model_name = data.get("model", f.stem)
                tps = float(data.get("tokens_per_second", 0))
                if tps > 0:
                    self._baselines[model_name] = SparkBaseline(
                        model_name=model_name,
                        tokens_per_second=tps,
                        hardware=data.get("hardware", "CPU"),
                        source_file=str(f),
                    )
            except (json.JSONDecodeError, KeyError, ValueError):
                pass

        return self._baselines

    # ------------------------------------------------------------------
    # Auto-load: tries benchmarks dir first, falls back to conversations
    # ------------------------------------------------------------------

    def load_all_baselines(self) -> dict[str, SparkBaseline]:
        """Load from ~/.tpt/benchmarks/ first; fall back to conversations dir."""
        result = self.load_baselines_from_benchmarks_dir()
        if not result:
            result = self.load_baselines()
        return result

    def get_baseline(self, model_name: str) -> SparkBaseline | None:
        """Return the most recent baseline for model_name, or None."""
        return self._baselines.get(model_name)

    def compare(
        self,
        model_name: str,
        crucible_tps: float,
        crucible_hardware: str,
    ) -> BenchmarkComparison | None:
        spark = self._baselines.get(model_name)
        if not spark:
            return None

        crucible = SparkBaseline(
            model_name=model_name,
            tokens_per_second=crucible_tps,
            hardware=crucible_hardware,
        )
        return BenchmarkComparison(spark=spark, crucible=crucible)

    def get_all_comparisons(self, crucible_tps: float, crucible_hardware: str) -> list[BenchmarkComparison]:
        comparisons = []
        for name, spark in self._baselines.items():
            crucible = SparkBaseline(
                model_name=name,
                tokens_per_second=crucible_tps,
                hardware=crucible_hardware,
            )
            comparisons.append(BenchmarkComparison(spark=spark, crucible=crucible))
        return comparisons


def _date_from_filename(filename: str) -> str:
    """Extract date string from 'spark-2026-06-29.json' → '2026-06-29'."""
    stem = filename.removesuffix(".json")
    parts = stem.split("-", 1)
    return parts[1] if len(parts) == 2 else ""


def load_spark_baseline(model_name: str) -> SparkBaseline | None:
    """Convenience function: load most recent Spark baseline for a model.

    Used by the emulator on startup to set a reference baseline without
    requiring manual user input.
    """
    bench = SparkBenchmark()
    bench.load_all_baselines()
    return bench.get_baseline(model_name)
