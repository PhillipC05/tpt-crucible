"""TPT Catalyst — Core IR compiler for AI model ingestion."""

__version__ = "0.1.0"

from tpt_catalyst.ir import TptIr, OpNode, Edge, ComputationalGraph
from tpt_catalyst.ingest import ingest_model
from tpt_catalyst.optimizer import optimize_graph, get_optimization_report
from tpt_catalyst.compat import check_compatibility, CompatibilityReport, HardwareTarget
from tpt_catalyst.quantize import recommend_quantization, apply_quantization
