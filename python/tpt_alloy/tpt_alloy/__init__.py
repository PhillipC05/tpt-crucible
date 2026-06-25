"""TPT Alloy — Swarm partitioning and firmware generation."""

__version__ = "0.1.0"

from tpt_alloy.topology import Topology
from tpt_alloy.partition import PartitionConfig, partition_model, GraphData, build_graph_from_nodes
from tpt_alloy.firmware import FirmwareTarget, generate_firmware
