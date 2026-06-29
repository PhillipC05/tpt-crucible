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
    source_file: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "tokens_per_second": round(self.tokens_per_second, 2),
            "hardware": self.hardware,
            "quantization": self.quantization,
        }


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


class SparkBenchmark:
    """Compare Spark GPU/CPU performance against Crucible custom hardware."""

    def __init__(self, spark_model_dir: Path | None = None):
        self.spark_model_dir = spark_model_dir or Path.home() / ".tpt-spark"
        self._baselines: dict[str, SparkBaseline] = {}

    def load_baselines(self) -> dict[str, SparkBaseline]:
        conversations_dir = self.spark_model_dir / "conversations"
        if not conversations_dir.exists():
            return {}

        for f in conversations_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                model_name = data.get("model", f.stem)
                tps = data.get("tokens_per_second", 0)
                if tps > 0:
                    self._baselines[model_name] = SparkBaseline(
                        model_name=model_name,
                        tokens_per_second=tps,
                        hardware=data.get("hardware", "CPU"),
                        source_file=str(f),
                    )
            except (json.JSONDecodeError, KeyError):
                pass

        return self._baselines

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
