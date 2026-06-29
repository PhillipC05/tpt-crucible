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

# Zephyr RTOS config for RISC-V targets (SiFive HiFive1 Rev B as reference)
ZEPHYR_RISCV_CONFIG = PlatformIOConfig(
    board="hifive1-revb",
    framework="zephyr",
    platform="sifive",
    monitor_speed=115200,
)


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


def generate_zephyr_platformio_ini(project_dir: Path, board: str = "hifive1-revb") -> Path:
    """Generate a platformio.ini for a Zephyr RTOS RISC-V project."""
    ini_content = f"""\
[env:riscv_zephyr]
platform = sifive
board = {board}
framework = zephyr
monitor_speed = 115200
build_flags =
    -DTPT_NODE_ID=${{env.TPT_NODE_ID}}
    -DCONFIG_MAIN_STACK_SIZE=4096
"""
    ini_path = project_dir / "platformio.ini"
    ini_path.write_text(ini_content)
    return ini_path


def generate_zephyr_cmake(project_dir: Path, node_id: int) -> Path:
    """Generate CMakeLists.txt for a Zephyr RTOS RISC-V project."""
    cmake_content = f"""\
cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS ${{ZEPHYR_BASE}})
project(tpt_alloy_node_{node_id})
target_sources(app PRIVATE src/main.c)
"""
    cmake_path = project_dir / "CMakeLists.txt"
    cmake_path.parent.mkdir(parents=True, exist_ok=True)
    cmake_path.write_text(cmake_content)
    return cmake_path


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
