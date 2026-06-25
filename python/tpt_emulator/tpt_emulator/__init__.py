"""TPT Emulator — Software-in-the-Loop simulation for all hardware types."""

__version__ = "0.1.0"

from tpt_emulator.interface import EmulatorInterface, EmulatorResult
from tpt_emulator.alloy_sil import AlloySil
from tpt_emulator.fusion_sil import FusionSil
from tpt_emulator.element_sil import ElementSil
