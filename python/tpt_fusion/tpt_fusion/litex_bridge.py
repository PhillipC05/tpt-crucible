"""LiteX/LiteDRAM bridge for HBM controller generation."""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LiteXConfig:
    """LiteX SoC configuration."""
    cpu_type: str = "vexriscv"
    sys_clk_freq: int = 100_000_000
    bus_data_width: int = 64
    bus_address_width: int = 32
    with_uart: bool = True
    with_timer: bool = True


class LiteXBridge:
    """Generates LiteX SoC configuration for HBM controller integration.

    LiteX provides the memory controller infrastructure. TPT Fusion
    generates the compute arrays and connects them to LiteX's HBM interface.
    """

    def __init__(self, config: LiteXConfig | None = None):
        self.config = config or LiteXConfig()

    def generate_soC(self, output_dir: Path) -> Path:
        """Generate a LiteX SoC Python file."""
        cfg = self.config
        output_dir.mkdir(parents=True, exist_ok=True)

        soc_code = f"""\
# Auto-generated LiteX SoC configuration for TPT Fusion
# CPU: {cfg.cpu_type}, Clock: {cfg.sys_clk_freq // 1_000_000} MHz

from migen import *
from litex.gen import *
from litex_boards.platforms import xilinx_alveo_u280
from litex.soc.interconnect import wishbone
from litex.soc.cores import uart, timer
from litedram.frontend import wishbone as litedram_wb


class TptSoC(LiteXModule):
    def __init__(self, platform):
        sys_clk_freq = {cfg.sys_clk_freq}

        # Clock and reset
        self.clock_domains.cd_sys = ClockDomain("sys")
        self.comb += self.cd_sys.clk.eq(platform.request("clk100"))
        self.comb += self.cd_sys.rst.eq(0)

        # UART
        {"self.uart = uart.UARTPhy(platform.request('uart'))" if cfg.with_uart else "# UART disabled"}

        # Timer
        {"self.timer = timer.Timer()" if cfg.with_timer else "# Timer disabled"}

        # HBM memory controller (via LiteDRAM)
        # TPT Fusion connects MAC arrays to this interface
        self.hbm_wb = wishbone.Interface(data_width=256, adr_width=32)


platform = xilinx_alveo_u280.Platform()
soc = TptSoC(platform)
builder = Builder(soc, output_dir="build")
builder.build()
"""

        soc_path = output_dir / "tpt_soc.py"
        soc_path.write_text(soc_code)
        return soc_path

    def generate_build_script(self, output_dir: Path) -> Path:
        """Generate a build script for LiteX."""
        script = f"""\
#!/usr/bin/env bash
# Auto-generated LiteX build script for TPT Fusion
set -euo pipefail

echo "Building TPT Fusion SoC..."
python tpt_soc.py

echo "Synthesizing with Yosys..."
yosys -p "read_verilog build/*.v; synth_xilinx -blif build/tpt.blif"

echo "Place and route with Nextpnr..."
nextpnr-xilinx --blif build/tpt.blif --board xcu280 --output build/tpt.bit

echo "Bitstream generated: build/tpt.bit"
"""
        script_path = output_dir / "build.sh"
        script_path.write_text(script)
        try:
            script_path.chmod(0o755)
        except (OSError, PermissionError):
            pass
        return script_path
