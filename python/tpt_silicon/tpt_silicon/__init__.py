"""TPT Silicon — Compute-in-Memory backend for CIM accelerators."""

__version__ = "0.1.0"

from tpt_silicon.weight_packer import CimWeightPacker, PackedArray
from tpt_silicon.array_layout import CimArrayLayout, LayoutConfig
from tpt_silicon.bitline import BitlineOpGenerator
