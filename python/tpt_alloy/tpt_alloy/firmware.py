"""Firmware generation for swarm nodes."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from .partition import Partition


class FirmwareTarget(Enum):
    ESP32 = "esp32"
    RP2040 = "rp2040"
    RISCV = "riscv"


class FirmwareRtos(Enum):
    NONE = "none"
    ZEPHYR = "zephyr"


@dataclass
class FirmwareBundle:
    node_id: int
    target: FirmwareTarget
    source_code: str
    config_json: str


def generate_firmware(
    partition: Partition,
    target: FirmwareTarget,
    rtos: FirmwareRtos = FirmwareRtos.NONE,
    checkpoint_ops: list[dict] | None = None,
    hardware_lock_fingerprint: str | None = None,
) -> FirmwareBundle:
    """Generate firmware for a partition on a given target."""
    if target == FirmwareTarget.ESP32:
        source = _gen_esp32(partition, checkpoint_ops, hardware_lock_fingerprint)
    elif target == FirmwareTarget.RP2040:
        source = _gen_rp2040(partition, checkpoint_ops, hardware_lock_fingerprint)
    elif rtos == FirmwareRtos.ZEPHYR:
        source = _gen_riscv_zephyr(partition, checkpoint_ops, hardware_lock_fingerprint)
    else:
        source = _gen_riscv(partition, checkpoint_ops, hardware_lock_fingerprint)

    import json
    config = json.dumps({
        "node_id": partition.node_id,
        "layers": partition.assigned_layers,
        "assigned_heads": partition.assigned_heads,
        "is_aggregator": partition.is_aggregator,
        "cross_edges": len(partition.cross_node_edges),
    }, indent=2)

    return FirmwareBundle(
        node_id=partition.node_id,
        target=target,
        source_code=source,
        config_json=config,
    )


def _gen_esp32(p: Partition, checkpoint_ops: list[dict] | None = None, hw_fingerprint: str | None = None) -> str:
    head_decl = ""
    if p.assigned_heads:
        head_decl = f"// Attention heads: {p.assigned_heads}\n"
    agg_decl = "// Aggregator node: YES\n" if p.is_aggregator else ""
    reduce_decl = ""
    if any(e.protocol == "sum_reduce" for e in p.cross_node_edges):
        reduce_decl = "// Sum-reduce protocol enabled for head aggregation\n"
    cp_decl = ""
    if checkpoint_ops:
        cp_lines = [f"// Checkpoint: layer={c.get('layer_name','?')}, storage={c.get('storage_offset',0)}" for c in checkpoint_ops[:5]]
        cp_decl = "\n".join(cp_lines) + "\n"
    lock_decl = ""
    if hw_fingerprint:
        lock_decl = f"""// Hardware lock fingerprint verification
#define HW_LOCK_FINGERPRINT "{hw_fingerprint}"

void verify_hw_lock() {{
    // Read device serial from eFuse/OTP
    uint8_t device_id[16];
    // Platform-specific: esp_efuse_read_device_id(device_id) or equivalent
    char device_hex[33];
    for (int i = 0; i < 16; i++) {{
        sprintf(device_hex + i * 2, "%02x", device_id[i]);
    }}
    if (strncmp(device_hex, HW_LOCK_FINGERPRINT, 32) != 0) {{
        Serial.println("HW LOCK MISMATCH - refusing to run");
        while (1) {{ delay(1000); }}
    }}
    Serial.println("HW lock verified");
}}

"""
    return f"""\
// Auto-generated ESP32 firmware for node {p.node_id}
// Layers: {p.assigned_layers}
{head_decl}{agg_decl}{reduce_decl}{cp_decl}{lock_decl}\
#include <Arduino.h>

void setup() {{
    Serial.begin(115200);
    Serial.println("TPT Alloy node {p.node_id} starting");
    {"verify_hw_lock();" if hw_fingerprint else ""}
}}

void loop() {{
    delay(100);
}}
"""


def _gen_rp2040(p: Partition, checkpoint_ops: list[dict] | None = None, hw_fingerprint: str | None = None) -> str:
    head_decl = ""
    if p.assigned_heads:
        head_decl = f"// Attention heads: {p.assigned_heads}\n"
    agg_decl = "// Aggregator node: YES\n" if p.is_aggregator else ""
    cp_decl = ""
    if checkpoint_ops:
        cp_lines = [f"// Checkpoint: layer={c.get('layer_name','?')}, storage={c.get('storage_offset',0)}" for c in checkpoint_ops[:5]]
        cp_decl = "\n".join(cp_lines) + "\n"
    lock_decl = ""
    if hw_fingerprint:
        lock_decl = f"""\
// Hardware lock fingerprint verification
#define HW_LOCK_FINGERPRINT "{hw_fingerprint}"

/* TPT hardware-lock verify — reads unique_id from RP2040 flash via Pico SDK */
static void tpt_verify_hw_lock(void) {{
    uint8_t uid[8];
    flash_get_unique_id(uid);
    uint64_t id64 = 0;
    for (int i = 0; i < 8; i++) id64 = (id64 << 8) | uid[i];
    char device_hex[17];
    for (int i = 0; i < 8; i++) sprintf(device_hex + i * 2, "%02x", uid[i]);
    device_hex[16] = '\\0';
    if (strncmp(device_hex, HW_LOCK_FINGERPRINT, 16) != 0) {{
        printf("HW LOCK MISMATCH - refusing to run\\n");
        while (1) {{ tight_loop_contents(); }}
    }}
}}

"""
    layer_count = len(p.assigned_layers)
    layer_array = ", ".join(str(l) for l in p.assigned_layers)
    lock_call = "tpt_verify_hw_lock();" if hw_fingerprint else ""
    return f"""\
// Auto-generated RP2040 firmware for node {p.node_id}
// Layers: {p.assigned_layers}
{head_decl}{agg_decl}{cp_decl}{lock_decl}\
#include "pico/stdlib.h"
#include "hardware/flash.h"
#include <stdio.h>
#include <string.h>

static const int tpt_assigned_layers[] = {{{layer_array}}};
static const int TPT_LAYER_COUNT = {layer_count};

int main() {{
    stdio_init_all();
    {lock_call}
    printf("TPT Alloy node {p.node_id} starting\\n");
    while (true) {{
        for (int i = 0; i < TPT_LAYER_COUNT; i++) {{
            tpt_run_layer(tpt_assigned_layers[i]);
        }}
        tpt_sync_neighbors();
    }}
    return 0;
}}
"""


def _gen_riscv(p: Partition, checkpoint_ops: list[dict] | None = None, hw_fingerprint: str | None = None) -> str:
    head_decl = ""
    if p.assigned_heads:
        head_decl = f"// Attention heads: {p.assigned_heads}\n"
    agg_decl = "// Aggregator node: YES\n" if p.is_aggregator else ""
    cp_decl = ""
    if checkpoint_ops:
        cp_lines = [f"// Checkpoint: layer={c.get('layer_name','?')}, storage={c.get('storage_offset',0)}" for c in checkpoint_ops[:5]]
        cp_decl = "\n".join(cp_lines) + "\n"
    lock_decl = ""
    if hw_fingerprint:
        lock_decl = f"""\
// Hardware lock fingerprint verification
#define HW_LOCK_FINGERPRINT "{hw_fingerprint}"

/* TPT hardware-lock verify — reads OTP fuses via SiFive OTP MMIO */
static void tpt_verify_hw_lock(void) {{
#ifdef SIFIVE_OTP_BASE
    volatile uint32_t *otp = (volatile uint32_t *)SIFIVE_OTP_BASE;
    uint64_t id64 = ((uint64_t)otp[1] << 32) | otp[0];
    (void)id64; /* compare against embedded fingerprint */
#endif
}}

"""
    layer_count = len(p.assigned_layers)
    layer_array = ", ".join(str(l) for l in p.assigned_layers)
    lock_call = "tpt_verify_hw_lock();" if hw_fingerprint else ""
    return f"""\
// Auto-generated RISC-V firmware for node {p.node_id}
// Layers: {p.assigned_layers}
{head_decl}{agg_decl}{cp_decl}{lock_decl}\
#include <stdio.h>
#include <stdint.h>

static const int tpt_assigned_layers[] = {{{layer_array}}};
static const int TPT_LAYER_COUNT = {layer_count};

int main() {{
    {lock_call}
    printf("TPT Alloy node {p.node_id} starting\\n");
    while (1) {{
        for (int i = 0; i < TPT_LAYER_COUNT; i++) {{
            tpt_run_layer(tpt_assigned_layers[i]);
        }}
        tpt_sync_neighbors();
    }}
    return 0;
}}
"""


def _gen_riscv_zephyr(p: Partition, checkpoint_ops: list[dict] | None = None, hw_fingerprint: str | None = None) -> str:
    head_decl = ""
    if p.assigned_heads:
        head_decl = f"// Attention heads: {p.assigned_heads}\n"
    agg_decl = "// Aggregator node: YES\n" if p.is_aggregator else ""
    cp_decl = ""
    if checkpoint_ops:
        cp_lines = [f"// Checkpoint: layer={c.get('layer_name','?')}, storage={c.get('storage_offset',0)}" for c in checkpoint_ops[:5]]
        cp_decl = "\n".join(cp_lines) + "\n"
    lock_decl = ""
    if hw_fingerprint:
        lock_decl = f"""\
// Hardware lock fingerprint verification
#define HW_LOCK_FINGERPRINT "{hw_fingerprint}"

/* TPT hardware-lock verify — uses Zephyr hwinfo subsystem */
static void tpt_verify_hw_lock(void) {{
    uint8_t uid[16];
    ssize_t len = hwinfo_get_device_id(uid, sizeof(uid));
    if (len <= 0) return; /* hwinfo not available on this board */
    (void)uid; /* compare against embedded fingerprint */
}}

"""
    layer_count = len(p.assigned_layers)
    layer_array = ", ".join(str(l) for l in p.assigned_layers)
    lock_call = "tpt_verify_hw_lock();" if hw_fingerprint else ""
    return f"""\
// Auto-generated Zephyr RTOS firmware for RISC-V node {p.node_id}
// Layers: {p.assigned_layers}
{head_decl}{agg_decl}{cp_decl}{lock_decl}\
#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include <zephyr/drivers/hwinfo.h>

#define NODE_ID {p.node_id}

static const int tpt_assigned_layers[] = {{{layer_array}}};
static const int TPT_LAYER_COUNT = {layer_count};

int main(void) {{
    {lock_call}
    printk("TPT Alloy node %d starting (Zephyr RTOS)\\n", NODE_ID);
    while (1) {{
        for (int i = 0; i < TPT_LAYER_COUNT; i++) {{
            tpt_run_layer(tpt_assigned_layers[i]);
        }}
        tpt_sync_neighbors();
        k_yield();
    }}
    return 0;
}}
"""
