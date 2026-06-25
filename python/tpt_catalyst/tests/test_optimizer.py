"""Tests for graph optimization passes."""

from tpt_catalyst.ir import TptIr, OpNode, Edge, ComputationalGraph, ModelMetadata
from tpt_catalyst.optimizer import optimize_graph, get_optimization_report


class TestOptimizer:
    def _make_matmul_relu_ir(self):
        return TptIr(
            version="1.0.0",
            metadata=ModelMetadata(name="test", source_format="pytorch"),
            graph=ComputationalGraph(
                nodes=[
                    OpNode(id=0, op_type="matmul", name="layer0"),
                    OpNode(id=1, op_type="relu", name="act0"),
                ],
                edges=[Edge(from_id=0, to_id=1, tensor_name="x")],
            ),
        )

    def test_fuse_matmul_relu(self):
        ir = self._make_matmul_relu_ir()
        result = optimize_graph(ir)
        assert len(result.graph.nodes) == 1
        assert result.graph.nodes[0].op_type == "fused_matmul_relu"

    def test_fuse_matmul_gelu(self):
        ir = TptIr(
            version="1.0.0",
            metadata=ModelMetadata(name="test", source_format="pytorch"),
            graph=ComputationalGraph(
                nodes=[
                    OpNode(id=0, op_type="matmul", name="layer0"),
                    OpNode(id=1, op_type="gelu", name="act0"),
                ],
                edges=[Edge(from_id=0, to_id=1, tensor_name="x")],
            ),
        )
        result = optimize_graph(ir)
        assert len(result.graph.nodes) == 1
        assert result.graph.nodes[0].op_type == "fused_matmul_gelu"

    def test_eliminate_identity(self):
        ir = TptIr(
            version="1.0.0",
            metadata=ModelMetadata(name="test", source_format="pytorch"),
            graph=ComputationalGraph(
                nodes=[
                    OpNode(id=0, op_type="identity", name="noop"),
                    OpNode(id=1, op_type="relu", name="act0"),
                ],
                edges=[Edge(from_id=0, to_id=1, tensor_name="x")],
            ),
        )
        result = optimize_graph(ir)
        assert all(n.op_type != "identity" for n in result.graph.nodes)

    def test_optimization_report(self):
        ir = self._make_matmul_relu_ir()
        result = optimize_graph(ir)
        report = get_optimization_report(result)
        assert report["fused_nodes"] == 1
        assert "tvm_available" in report
