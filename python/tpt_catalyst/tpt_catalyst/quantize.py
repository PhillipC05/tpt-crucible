"""Auto-quantization advisor — recommend quantization schemes per hardware target."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .ir import TptIr, OpNode, ComputationalGraph


class QuantTarget(Enum):
    FUSION_INT8 = "fusion_int8"
    FUSION_INT4 = "fusion_int4"
    ALLOY_INT8 = "alloy_int8"
    ELEMENT_FLOAT = "element_float"


@dataclass
class QuantizationProfile:
    name: str
    target: QuantTarget
    weight_bits: int
    activation_bits: int
    accumulator_bits: int
    estimated_accuracy_loss: float
    estimated_speedup: float
    memory_reduction: float


QUANT_PROFILES: dict[QuantTarget, QuantizationProfile] = {
    QuantTarget.FUSION_INT8: QuantizationProfile(
        name="FPGA INT8",
        target=QuantTarget.FUSION_INT8,
        weight_bits=8,
        activation_bits=8,
        accumulator_bits=32,
        estimated_accuracy_loss=0.01,
        estimated_speedup=4.0,
        memory_reduction=0.25,
    ),
    QuantTarget.FUSION_INT4: QuantizationProfile(
        name="FPGA INT4",
        target=QuantTarget.FUSION_INT4,
        weight_bits=4,
        activation_bits=8,
        accumulator_bits=32,
        estimated_accuracy_loss=0.05,
        estimated_speedup=8.0,
        memory_reduction=0.125,
    ),
    QuantTarget.ALLOY_INT8: QuantizationProfile(
        name="Swarm INT8",
        target=QuantTarget.ALLOY_INT8,
        weight_bits=8,
        activation_bits=8,
        accumulator_bits=16,
        estimated_accuracy_loss=0.01,
        estimated_speedup=2.0,
        memory_reduction=0.25,
    ),
    QuantTarget.ELEMENT_FLOAT: QuantizationProfile(
        name="Analog Float",
        target=QuantTarget.ELEMENT_FLOAT,
        weight_bits=32,
        activation_bits=32,
        accumulator_bits=32,
        estimated_accuracy_loss=0.0,
        estimated_speedup=1.0,
        memory_reduction=1.0,
    ),
}


@dataclass
class QuantizationRecommendation:
    recommended_profile: QuantizationProfile
    reason: str
    tradeoff_summary: str


def recommend_quantization(ir: TptIr, hardware_target: str) -> QuantizationRecommendation:
    """Recommend a quantization scheme based on the model and target hardware."""
    profile_map = {
        "fusion": QuantTarget.FUSION_INT8,
        "alloy": QuantTarget.ALLOY_INT8,
        "element": QuantTarget.ELEMENT_FLOAT,
    }

    target = profile_map.get(hardware_target, QuantTarget.FUSION_INT8)
    profile = QUANT_PROFILES[target]

    if hardware_target == "fusion":
        reason = "FPGA benefits most from INT8 quantization for optimal DSP utilization"
        tradeoff = f"INT8 reduces memory by {1-profile.memory_reduction:.0%} with <{profile.estimated_accuracy_loss:.0%} accuracy loss"
    elif hardware_target == "alloy":
        reason = "Microcontroller swarm limited by memory and compute; INT8 balances both"
        tradeoff = f"INT8 fits within ESP32 520KB SRAM constraint with {profile.estimated_speedup:.0f}x speedup"
    else:
        reason = "Analog compute is inherently analog — no quantization benefit"
        tradeoff = "Keep full floating-point weights for analog resistive compute"

    return QuantizationRecommendation(
        recommended_profile=profile,
        reason=reason,
        tradeoff_summary=tradeoff,
    )


def apply_quantization(ir: TptIr, profile: QuantizationProfile) -> TptIr:
    """Apply quantization metadata to TPT-IR (metadata-only, no weight rewriting)."""
    new_nodes = []
    for node in ir.graph.nodes:
        attrs = dict(node.attributes)
        attrs["quant_weight_bits"] = profile.weight_bits
        attrs["quant_activation_bits"] = profile.activation_bits
        attrs["quant_accumulator_bits"] = profile.accumulator_bits
        attrs["quant_profile"] = profile.name
        new_nodes.append(OpNode(
            id=node.id,
            op_type=node.op_type,
            name=node.name,
            attributes=attrs,
        ))

    ir.graph.nodes = new_nodes
    return ir
