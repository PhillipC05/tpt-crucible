"""TPT Mosaic — Hybrid cross-hardware deployment orchestrator."""

__version__ = "0.1.0"

from tpt_mosaic.partition import LayerAssignment, PartitionPlan
from tpt_mosaic.orchestrator import MosaicOrchestrator
from tpt_mosaic.bridge import InterHardwareBridge, BridgeConfig
