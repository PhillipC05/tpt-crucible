"""Write pre-flight, quantization, and partition reports into .tptpkg structure."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .compat import CompatibilityReport
from .quantize import QuantizationProfile


def write_preflight_report(report: CompatibilityReport, pkg_dir: Path) -> Path:
    """Write pre-flight compatibility report into compat/preflight.json."""
    compat_dir = pkg_dir / "compat"
    compat_dir.mkdir(parents=True, exist_ok=True)
    report_path = compat_dir / "preflight.json"
    report_path.write_text(json.dumps(report.to_dict(), indent=2))
    return report_path


def write_quant_profile(profile: QuantizationProfile, pkg_dir: Path) -> Path:
    """Write quantization profile into quant/quant_profile.json."""
    quant_dir = pkg_dir / "quant"
    quant_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "name": profile.name,
        "target": profile.target.value,
        "weight_bits": profile.weight_bits,
        "activation_bits": profile.activation_bits,
        "accumulator_bits": profile.accumulator_bits,
        "estimated_accuracy_loss": profile.estimated_accuracy_loss,
        "estimated_speedup": profile.estimated_speedup,
        "memory_reduction": profile.memory_reduction,
    }
    profile_path = quant_dir / "quant_profile.json"
    profile_path.write_text(json.dumps(data, indent=2))
    return profile_path


def write_mosaic_partition(plan_data: dict[str, Any], pkg_dir: Path) -> Path:
    """Write Mosaic partition plan into mosaic/partition.json."""
    mosaic_dir = pkg_dir / "mosaic"
    mosaic_dir.mkdir(parents=True, exist_ok=True)
    partition_path = mosaic_dir / "partition.json"
    partition_path.write_text(json.dumps(plan_data, indent=2))
    return partition_path
