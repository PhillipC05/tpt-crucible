"""Inter-hardware communication protocol and bridge code generation."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .partition import HardwareTarget


@dataclass
class BridgeConfig:
    """Configuration for inter-hardware communication."""
    fpga_to_swarm_protocol: str = "usb"
    swarm_to_analog_protocol: str = "uart"
    fpga_to_analog_protocol: str = "ethernet"
    baud_rate: int = 115200
    usb_vendor_id: int = 0x303A
    usb_product_id: int = 0x4001


class InterHardwareBridge:
    """Generates glue code for communication between different hardware types."""

    def __init__(self, config: BridgeConfig | None = None):
        self.config = config or BridgeConfig()

    def generate_bridge_code(
        self,
        source: HardwareTarget,
        target: HardwareTarget,
        tensor_name: str,
        data_width: int = 16,
    ) -> str:
        """Generate bridge code for data transfer between hardware types."""
        protocol = self._get_protocol(source, target)

        if protocol == "usb":
            return self._gen_usb_bridge(tensor_name, data_width)
        elif protocol == "uart":
            return self._gen_uart_bridge(tensor_name, data_width)
        elif protocol == "ethernet":
            return self._gen_ethernet_bridge(tensor_name, data_width)
        return f"// No bridge defined for {source.value} → {target.value}"

    def _get_protocol(self, source: HardwareTarget, target: HardwareTarget) -> str:
        if source == HardwareTarget.FPGA and target == HardwareTarget.SWARM:
            return self.config.fpga_to_swarm_protocol
        elif source == HardwareTarget.SWARM and target == HardwareTarget.ANALOG:
            return self.config.swarm_to_analog_protocol
        elif source == HardwareTarget.FPGA and target == HardwareTarget.ANALOG:
            return self.config.fpga_to_analog_protocol
        return "usb"

    def _gen_usb_bridge(self, tensor_name: str, data_width: int) -> str:
        return f"""\
// USB bridge: {tensor_name}
// Data width: {data_width} bits
#include "tpt_usb.h"

void bridge_send_{tensor_name}(const uint{data_width}_t* data, size_t len) {{
    tpt_usb_bulk_write(data, len * sizeof(uint{data_width}_t));
}}

void bridge_recv_{tensor_name}(uint{data_width}_t* data, size_t len) {{
    tpt_usb_bulk_read(data, len * sizeof(uint{data_width}_t));
}}
"""

    def _gen_uart_bridge(self, tensor_name: str, data_width: int) -> str:
        return f"""\
// UART bridge: {tensor_name}
// Baud rate: {self.config.baud_rate}
#include "tpt_uart.h"

void bridge_send_{tensor_name}(const uint{data_width}_t* data, size_t len) {{
    for (size_t i = 0; i < len; i++) {{
        tpt_uart_write_byte((data[i] >> 8) & 0xFF);
        tpt_uart_write_byte(data[i] & 0xFF);
    }}
}}

void bridge_recv_{tensor_name}(uint{data_width}_t* data, size_t len) {{
    for (size_t i = 0; i < len; i++) {{
        uint{data_width}_t hi = tpt_uart_read_byte();
        uint{data_width}_t lo = tpt_uart_read_byte();
        data[i] = (hi << 8) | lo;
    }}
}}
"""

    def _gen_ethernet_bridge(self, tensor_name: str, data_width: int) -> str:
        return f"""\
// Ethernet bridge: {tensor_name}
#include "tpt_eth.h"

void bridge_send_{tensor_name}(const uint{data_width}_t* data, size_t len) {{
    tpt_eth_send(data, len * sizeof(uint{data_width}_t));
}}

void bridge_recv_{tensor_name}(uint{data_width}_t* data, size_t len) {{
    tpt_eth_recv(data, len * sizeof(uint{data_width}_t));
}}
"""
