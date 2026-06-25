"""TPT Fusion — FPGA synthesis and HBM auto-routing."""

__version__ = "0.1.0"

from tpt_fusion.mac_array import MacArray, MacConfig
from tpt_fusion.board import BoardConfig, BOARD_LIBRARY
from tpt_fusion.rtl import RtlGenerator
from tpt_fusion.toolchain import YosysRunner, NextpnrRunner
