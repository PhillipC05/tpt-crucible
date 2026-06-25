"""PlatformIO build integration for swarm firmware."""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .firmware import FirmwareTarget, FirmwareBundle


@dataclass
class PlatformIOConfig:
    board: str
    framework: str
    platform: str
    monitor_speed: int = 115200


PLATFORM_IO_BOARDS = {
    FirmwareTarget.ESP32: PlatformIOConfig(
        board="esp32dev",
        framework="arduino",
        platform="espressif32",
    ),
    FirmwareTarget.RP2040: PlatformIOConfig(
        board="rpipicow",
        framework="arduino",
        platform="raspberrypi",
    ),
    FirmwareTarget.RISCV: PlatformIOConfig(
        board="native",
        framework="none",
        platform="linux",
    ),
}


def generate_platformio_ini(target: FirmwareTarget, project_dir: Path) -> Path:
    """Generate a platformio.ini file for the target platform."""
    config = PLATFORM_IO_BOARDS[target]
    ini_content = f"""\
[env:{target.value}]
platform = {config.platform}
board = {config.board}
framework = {config.framework}
monitor_speed = {config.monitor_speed}
build_flags = -DTPT_NODE_ID=${{env.TPT_NODE_ID}}
"""
    ini_path = project_dir / "platformio.ini"
    ini_path.write_text(ini_content)
    return ini_path


def generate_flash_script(
    bundles: list[FirmwareBundle],
    output_path: Path,
    serial_ports: list[str] | None = None,
) -> Path:
    """Generate a master flashing script that flashes all nodes."""
    target = bundles[0].target if bundles else FirmwareTarget.ESP32
    script_lines = ["#!/usr/bin/env bash", "set -euo pipefail", ""]

    for i, bundle in enumerate(bundles):
        port = serial_ports[i] if serial_ports and i < len(serial_ports) else f"/dev/ttyUSB{i}"
        script_lines.extend([
            f'echo "Flashing node {bundle.node_id} on {port}..."',
            f"export TPT_NODE_ID={bundle.node_id}",
            f"platformio run -t upload -e {target.value} --upload-port {port}",
            "",
        ])

    script_lines.extend([
        'echo "All nodes flashed successfully"',
        "",
    ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(script_lines))

    try:
        output_path.chmod(0o755)
    except (OSError, PermissionError):
        pass

    return output_path
