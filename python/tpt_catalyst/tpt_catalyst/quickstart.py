"""Quickstart guide — one-line bootstrap for TPT Crucible."""

from __future__ import annotations
from pathlib import Path
import subprocess
import sys


QUICKSTART_STEPS = [
    {
        "title": "Install TPT Crucible",
        "command": "pip install tpt-crucible",
        "description": "Install the core compiler and SiL emulator",
    },
    {
        "title": "Download TinyLlama",
        "command": "tpt-catalyst ingest --spark-model tinyllama",
        "description": "Fetch TinyLlama 1.1B from Spark model library",
    },
    {
        "title": "Check compatibility",
        "command": "tpt-catalyst check model.tptir --target alloy",
        "description": "Verify model works with swarm hardware",
    },
    {
        "title": "Compile for swarm",
        "command": "tpt-catalyst pack model.tptir --targets alloy",
        "description": "Generate .tptpkg for ESP32 swarm deployment",
    },
    {
        "title": "Run SiL emulator",
        "command": "tpt-emulate model.tptpkg --hardware alloy --nodes 16",
        "description": "Test in software-in-the-loop environment",
    },
]


def print_quickstart() -> None:
    print("\n" + "=" * 60)
    print("  TPT CRUCIBLE — Quick Start Guide")
    print("=" * 60 + "\n")

    for i, step in enumerate(QUICKSTART_STEPS, 1):
        print(f"  Step {i}: {step['title']}")
        print(f"    {step['description']}")
        print(f"    $ {step['command']}")
        print()

    print("=" * 60)
    print("  For more info: https://github.com/tpt-solutions/tpt-crucible")
    print("=" * 60 + "\n")


def check_prerequisites() -> dict[str, bool]:
    prereqs = {}
    for cmd, name in [("python", "Python"), ("cargo", "Rust"), ("go", "Go"), ("node", "Node.js")]:
        try:
            result = subprocess.run([cmd, "--version"], capture_output=True, timeout=5)
            prereqs[name] = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            prereqs[name] = False
    return prereqs


def install_extras(extras: list[str]) -> bool:
    cmd = [sys.executable, "-m", "pip", "install", "tpt-crucible"]
    for extra in extras:
        cmd[0] = sys.executable
        cmd = [sys.executable, "-m", "pip", "install", f"tpt-crucible[{extra}]"]

    for extra in extras:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", f"tpt-crucible[{extra}]"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"Failed to install extra '{extra}': {result.stderr}")
            return False
    return True
