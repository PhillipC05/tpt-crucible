"""FPGA board library — pre-defined board configurations."""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class HbmConfig:
    """HBM memory configuration."""
    capacity_gb: int = 4
    channels: int = 8
    data_width: int = 256
    frequency_mhz: int = 450


@dataclass
class BoardConfig:
    """FPGA board configuration."""
    name: str
    fpga_part: str
    hbm: HbmConfig | None = None
    max_clock_mhz: int = 300
    io_pins: int = 0
    pcie_lanes: int = 0


BOARD_LIBRARY: dict[str, BoardConfig] = {
    "xilinx_alveo_u280": BoardConfig(
        name="Xilinx Alveo U280",
        fpga_part="xcu280-fsgd2104-2L-e",
        hbm=HbmConfig(capacity_gb=4, channels=8),
        max_clock_mhz=300,
        pcie_lanes=16,
    ),
    "xilinx_alveo_u250": BoardConfig(
        name="Xilinx Alveo U250",
        fpga_part="xcu250-fgvd1156-2L-e",
        max_clock_mhz=300,
        pcie_lanes=16,
    ),
    "lattice_ice40": BoardConfig(
        name="Lattice iCE40",
        fpga_part="lp8k",
        max_clock_mhz=133,
        io_pins=128,
    ),
    "intel_de10_nano": BoardConfig(
        name="Intel DE10-Nano",
        fpga_part="5CSEBA6U23I7",
        max_clock_mhz=200,
        io_pins=256,
    ),
}


def get_board(name: str) -> BoardConfig:
    """Get board configuration by name."""
    if name not in BOARD_LIBRARY:
        available = ", ".join(BOARD_LIBRARY.keys())
        raise ValueError(f"Unknown board: {name}. Available: {available}")
    return BOARD_LIBRARY[name]


def list_boards() -> list[str]:
    """List all available board names."""
    return list(BOARD_LIBRARY.keys())
