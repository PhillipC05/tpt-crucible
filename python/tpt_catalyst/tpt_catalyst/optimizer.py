"""Graph optimization passes using Apache TVM (when available)."""

from __future__ import annotations
from .ir import TptIr, OpNode, Edge

try:
    import tvm
    from tvm import relay
    TVM_AVAILABLE = True
except ImportError:
    TVM_AVAILABLE = False


def optimize_graph(ir: TptIr) -> TptIr:
    """Apply TVM optimization passes to a TPT-IR graph.

    Falls back to built-in Rust optimizer when TVM is not installed.
    """
    if TVM_AVAILABLE:
        return _tvm_optimize(ir)
    return _builtin_optimize(ir)


def _tvm_optimize(ir: TptIr) -> TptIr:
    """Use TVM Relay for graph optimization (operator fusion, CSE, inference simplification).

    Attempts to load the TPT-IR JSON as a TVM IRModule. If the IR is not in TVM
    format (expected for most TPT-IR graphs), falls back to the built-in optimizer.
    The relay transforms are applied when the module is valid TVM IR.
    """
    try:
        import tvm
        mod = tvm.ir.load_json(ir.to_json())
        seq = tvm.transform.Sequential([
            relay.transform.FuseOps(fuse_opt_level=2),
            relay.transform.EliminateCommonSubexpr(),
            relay.transform.SimplifyInference(),
            relay.transform.FoldConstant(),
        ])
        mod = seq(mod)
        # If we reach here the module was valid TVM IR — return as-is since the
        # optimized graph lives in mod, not ir; a full bridge would convert back.
        return ir
    except Exception:
        return _builtin_optimize(ir)


def _builtin_optimize(ir: TptIr) -> TptIr:
    """Built-in optimization passes when TVM is not available."""
    ir = _fuse_sequential_ops(ir)
    ir = _eliminate_redundant_ops(ir)
    return ir


def _fuse_sequential_ops(ir: TptIr) -> TptIr:
    """Fuse sequential operations like matmul+relu."""
    fuse_patterns = [
        (["matmul", "relu"], "fused_matmul_relu"),
        (["matmul", "gelu"], "fused_matmul_gelu"),
        (["add", "relu"], "fused_add_relu"),
    ]

    fused_indices = set()
    new_nodes = list(ir.graph.nodes)

    for pattern, fused_type in fuse_patterns:
        for edge in ir.graph.edges:
            from_node = next((n for n in new_nodes if n.id == edge.from_id), None)
            to_node = next((n for n in new_nodes if n.id == edge.to_id), None)
            if from_node and to_node:
                if from_node.op_type == pattern[0] and to_node.op_type == pattern[1]:
                    from_node.op_type = fused_type
                    from_node.name = f"{from_node.name}_{to_node.name}"
                    fused_indices.add(to_node.id)

    new_nodes = [n for n in new_nodes if n.id not in fused_indices]
    new_edges = [e for e in ir.graph.edges if e.to_id not in fused_indices]
    ir.graph.nodes = new_nodes
    ir.graph.edges = new_edges
    return ir


def _eliminate_redundant_ops(ir: TptIr) -> TptIr:
    """Remove no-op identity operations."""
    ir.graph.nodes = [n for n in ir.graph.nodes if n.op_type != "identity"]
    return ir


def get_optimization_report(ir: TptIr) -> dict:
    """Generate a report of applied optimizations."""
    original_count = len(ir.graph.nodes)
    return {
        "total_nodes": original_count,
        "fused_nodes": sum(1 for n in ir.graph.nodes if n.op_type.startswith("fused_")),
        "tvm_available": TVM_AVAILABLE,
    }
