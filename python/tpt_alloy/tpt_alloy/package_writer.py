"""Write Alloy artifacts into .tptpkg structure."""

from __future__ import annotations
import json
import shutil
from pathlib import Path
from .partition import Partition
from .firmware import FirmwareTarget, generate_firmware


def write_alloy_artifacts(
    partitions: list[Partition],
    target: FirmwareTarget,
    pkg_dir: Path,
    prev_pkg_dir: Path | None = None,
) -> dict[str, str]:
    """Write firmware, topology, and flash script into the package.

    If prev_pkg_dir is provided, copies previous firmware binaries into
    targets/alloy/firmware/prev/ for rollback support.
    """
    artifacts = {}
    firmware_dir = pkg_dir / "targets" / "alloy"
    firmware_dir.mkdir(parents=True, exist_ok=True)

    if prev_pkg_dir is not None:
        prev_firmware = prev_pkg_dir / "targets" / "alloy"
        if prev_firmware.exists():
            prev_dir = firmware_dir / "prev"
            prev_dir.mkdir(exist_ok=True)
            for fw_file in prev_firmware.glob("node_*.c"):
                shutil.copy2(fw_file, prev_dir / fw_file.name)
            for cfg_file in prev_firmware.glob("node_*.json"):
                shutil.copy2(cfg_file, prev_dir / cfg_file.name)

    for p in partitions:
        bundle = generate_firmware(p, target)
        fw_path = firmware_dir / f"node_{bundle.node_id}.c"
        fw_path.write_text(bundle.source_code)
        artifacts[f"alloy/node_{bundle.node_id}.c"] = str(fw_path)

        cfg_path = firmware_dir / f"node_{bundle.node_id}.json"
        cfg_path.write_text(bundle.config_json)

    topology = {
        "node_count": len(partitions),
        "target": target.value,
        "layers_per_node": {
            str(p.node_id): p.assigned_layers for p in partitions
        },
    }
    topo_path = firmware_dir / "topology.json"
    topo_path.write_text(json.dumps(topology, indent=2))
    artifacts["alloy/topology.json"] = str(topo_path)

    flash_lines = ["#!/usr/bin/env bash", "set -euo pipefail", ""]
    for i, p in enumerate(partitions):
        port = f"/dev/ttyUSB{i}"
        flash_lines.extend([
            f'echo "Flashing node {p.node_id} on {port}..."',
            f"platformio run -t upload -e {target.value} --upload-port {port}",
            "",
        ])
    flash_path = firmware_dir / "flash.sh"
    flash_path.write_text("\n".join(flash_lines))
    artifacts["alloy/flash.sh"] = str(flash_path)

    return artifacts
