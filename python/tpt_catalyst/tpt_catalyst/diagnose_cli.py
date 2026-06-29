"""Diagnostics CLI — run hardware diagnostics and report status."""

from __future__ import annotations
from pathlib import Path
import json


def run_diagnostics(
    pkg_path: Path,
    hardware: str = "alloy",
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Run diagnostics for specified hardware type."""
    from tpt_catalyst.diagnostics import run_diagnostics as run_hw_diag

    report = run_hw_diag(hardware)
    result = {
        "package": str(pkg_path),
        "hardware": hardware,
        "score": report.score,
        "status": report.overall_status,
        "results": [r.to_dict() for r in report.results],
    }

    if output_path:
        output_path.write_text(json.dumps(result, indent=2))

    return result
