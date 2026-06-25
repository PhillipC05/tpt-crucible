"""Tests for pre-flight compatibility analyzer."""

from tpt_catalyst.ir import TptIr, OpNode, Edge, ComputationalGraph, ModelMetadata
from tpt_catalyst.compat import (
    check_compatibility,
    CompatibilityReport,
    HardwareTarget,
    Severity,
)


def _make_ir_with_ops(ops: list[str]) -> TptIr:
    nodes = [OpNode(id=i, op_type=op, name=f"{op}_{i}") for i, op in enumerate(ops)]
    edges = [Edge(from_id=i, to_id=i + 1, tensor_name=f"x_{i}") for i in range(len(nodes) - 1)]
    return TptIr(
        version="1.0.0",
        metadata=ModelMetadata(name="test", source_format="pytorch"),
        graph=ComputationalGraph(nodes=nodes, edges=edges),
    )


class TestCompatibilityReport:
    def test_empty_report_score(self):
        report = CompatibilityReport()
        assert report.score == 1.0

    def test_all_pass_score(self):
        report = CompatibilityReport()
        report.results = [
            _compat("matmul", Severity.PASS),
            _compat("relu", Severity.PASS),
        ]
        assert report.score == 1.0
        assert not report.has_failures

    def test_mixed_severity_score(self):
        report = CompatibilityReport()
        report.results = [
            _compat("matmul", Severity.PASS),
            _compat("softmax", Severity.FAIL),
        ]
        assert report.score == 0.5
        assert report.has_failures


def _compat(op_type: str, severity: Severity):
    from tpt_catalyst.compat import OpCompatibility
    return OpCompatibility(
        op_type=op_type,
        target=HardwareTarget.FUSION,
        severity=severity,
        message=f"{op_type} is {severity.value}",
    )


class TestCheckCompatibility:
    def test_fusion_all_supported(self):
        ir = _make_ir_with_ops(["matmul", "relu", "conv2d"])
        report = check_compatibility(ir, HardwareTarget.FUSION)
        assert report.score == 1.0

    def test_fusion_softmax_warns(self):
        ir = _make_ir_with_ops(["softmax"])
        report = check_compatibility(ir, HardwareTarget.FUSION)
        assert report.has_failures

    def test_alloy_supports_more(self):
        ir = _make_ir_with_ops(["attention", "softmax", "gelu"])
        report = check_compatibility(ir, HardwareTarget.ALLOY)
        assert report.score > 0

    def test_element_strict(self):
        ir = _make_ir_with_ops(["conv2d", "softmax", "dropout"])
        report = check_compatibility(ir, HardwareTarget.ELEMENT)
        assert report.has_failures

    def test_to_dict(self):
        ir = _make_ir_with_ops(["matmul"])
        report = check_compatibility(ir, HardwareTarget.FUSION)
        d = report.to_dict()
        assert "score" in d
        assert "details" in d
