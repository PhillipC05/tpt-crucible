"""Tests for auto-quantization advisor."""

from tpt_catalyst.ir import TptIr, OpNode, Edge, ComputationalGraph, ModelMetadata
from tpt_catalyst.quantize import (
    recommend_quantization,
    apply_quantization,
    QUANT_PROFILES,
    QuantTarget,
)


def _make_test_ir() -> TptIr:
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


class TestQuantProfiles:
    def test_all_profiles_exist(self):
        assert len(QUANT_PROFILES) == 4
        assert QuantTarget.FUSION_INT8 in QUANT_PROFILES
        assert QuantTarget.ELEMENT_FLOAT in QUANT_PROFILES

    def test_int8_profile(self):
        p = QUANT_PROFILES[QuantTarget.FUSION_INT8]
        assert p.weight_bits == 8
        assert p.estimated_accuracy_loss < 0.05


class TestRecommendQuantization:
    def test_fusion_recommends_int8(self):
        ir = _make_test_ir()
        rec = recommend_quantization(ir, "fusion")
        assert rec.recommended_profile.target == QuantTarget.FUSION_INT8
        assert "INT8" in rec.reason

    def test_alloy_recommends_int8(self):
        ir = _make_test_ir()
        rec = recommend_quantization(ir, "alloy")
        assert rec.recommended_profile.target == QuantTarget.ALLOY_INT8

    def test_element_recommends_float(self):
        ir = _make_test_ir()
        rec = recommend_quantization(ir, "element")
        assert rec.recommended_profile.target == QuantTarget.ELEMENT_FLOAT


class TestApplyQuantization:
    def test_applies_metadata(self):
        ir = _make_test_ir()
        profile = QUANT_PROFILES[QuantTarget.FUSION_INT8]
        result = apply_quantization(ir, profile)
        assert result.graph.nodes[0].attributes.get("quant_weight_bits") == 8
        assert result.graph.nodes[0].attributes.get("quant_profile") == "FPGA INT8"
