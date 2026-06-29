"""OTA Update CLI — incremental firmware updates for swarm nodes."""

from __future__ import annotations
from pathlib import Path
from typing import Any
import json


def generate_ota_command(
    new_pkg: Path,
    prev_pkg: Path,
    topology_path: Path,
    output_dir: Path | None = None,
) -> str:
    """Generate OTA update script for swarm nodes."""
    output = output_dir or Path("ota_output")
    output.mkdir(parents=True, exist_ok=True)

    script_lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        f"# OTA Update Script",
        f"# New package: {new_pkg}",
        f"# Previous package: {prev_pkg}",
        f"# Topology: {topology_path}",
        "",
        "echo 'Computing firmware diff...'",
        "",
    ]

    topology = {}
    if topology_path.exists():
        try:
            topology = json.loads(topology_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    node_count = topology.get("node_count", 16)

    for i in range(node_count):
        script_lines.extend([
            f"# Node {i}",
            f"echo 'Updating node {i}...'",
            f"tpt-alloy flash-node --node {i} --firmware {new_pkg}/targets/alloy/node_{i}.c",
            "",
        ])

    script_lines.extend([
        "echo 'OTA update complete'",
        "",
    ])

    script_path = output / "ota_update.sh"
    script_path.write_text("\n".join(script_lines))
    try:
        script_path.chmod(0o755)
    except (OSError, PermissionError):
        pass

    return str(script_path)
