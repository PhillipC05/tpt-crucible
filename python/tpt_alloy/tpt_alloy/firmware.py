"""Firmware generation for swarm nodes."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from .partition import Partition


class FirmwareTarget(Enum):
    ESP32 = "esp32"
    RP2040 = "rp2040"
    RISCV = "riscv"


@dataclass
class FirmwareBundle:
    node_id: int
    target: FirmwareTarget
    source_code: str
    config_json: str


def generate_firmware(partition: Partition, target: FirmwareTarget) -> FirmwareBundle:
    """Generate firmware for a partition on a given target."""
    if target == FirmwareTarget.ESP32:
        source = _gen_esp32(partition)
    elif target == FirmwareTarget.RP2040:
        source = _gen_rp2040(partition)
    else:
        source = _gen_riscv(partition)

    import json
    config = json.dumps({
        "node_id": partition.node_id,
        "layers": partition.assigned_layers,
        "cross_edges": len(partition.cross_node_edges),
    }, indent=2)

    return FirmwareBundle(
        node_id=partition.node_id,
        target=target,
        source_code=source,
        config_json=config,
    )


def _gen_esp32(p: Partition) -> str:
    return f"""\
// Auto-generated ESP32 firmware for node {p.node_id}
// Layers: {p.assigned_layers}
#include <Arduino.h>

void setup() {{
    Serial.begin(115200);
    Serial.println("TPT Alloy node {p.node_id} starting");
}}

void loop() {{
    delay(100);
}}
"""


def _gen_rp2040(p: Partition) -> str:
    return f"""\
// Auto-generated RP2040 firmware for node {p.node_id}
// Layers: {p.assigned_layers}
#include "pico/stdlib.h"

int main() {{
    stdio_init_all();
    printf("TPT Alloy node {p.node_id} starting\\n");
    while (true) {{
        sleep_ms(100);
    }}
    return 0;
}}
"""


def _gen_riscv(p: Partition) -> str:
    return f"""\
// Auto-generated RISC-V firmware for node {p.node_id}
// Layers: {p.assigned_layers}
#include <stdio.h>

int main() {{
    printf("TPT Alloy node {p.node_id} starting\\n");
    while (1) {{ }}
    return 0;
}}
"""
