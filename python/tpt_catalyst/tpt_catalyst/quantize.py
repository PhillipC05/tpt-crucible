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


@dataclass
class LayerQuantDecision:
    layer_name: str
    weight_bits: int
    activation_bits: int
    sensitivity: float
    promoted: bool = False


@dataclass
class MixedPrecisionResult:
    decisions: list[LayerQuantDecision]
    accuracy_budget: float
    estimated_accuracy_loss: float
    avg_weight_bits: float
    compression_ratio: float

    @property
    def budget_met(self) -> bool:
        return self.estimated_accuracy_loss <= self.accuracy_budget

    def to_dict(self) -> dict[str, Any]:
        return {
            "accuracy_budget": self.accuracy_budget,
            "estimated_accuracy_loss": round(self.estimated_accuracy_loss, 6),
            "avg_weight_bits": round(self.avg_weight_bits, 2),
            "compression_ratio": round(self.compression_ratio, 2),
            "budget_met": self.budget_met,
            "layers": [
                {
                    "name": d.layer_name,
                    "weight_bits": d.weight_bits,
                    "activation_bits": d.activation_bits,
                    "sensitivity": round(d.sensitivity, 4),
                    "promoted": d.promoted,
                }
                for d in self.decisions
            ],
        }


def mixed_precision_search(
    ir: TptIr,
    hardware_target: str = "fusion",
    accuracy_budget: float = 0.05,
    profile_path: Any | None = None,
) -> MixedPrecisionResult:
    """Per-layer mixed-precision quantization search.

    Starts all layers at INT4, then greedily promotes the most fragile
    layers to INT8 until the accuracy budget is met.

    Uses .tptprofile sensitivity scores if available; falls back to
    gradient-free sensitivity estimation based on weight statistics.
    """
    layer_sensitivities = _compute_sensitivities(ir, profile_path)

    base_bits = 4
    promoted_bits = 8
    layers = list(ir.graph.nodes)
    base_accuracy_loss = 0.0

    decisions = []
    for node in layers:
        sens = layer_sensitivities.get(node.name, 0.5)
        loss_at_4bit = _estimate_loss_at_bits(node, base_bits, sens)
        decisions.append(LayerQuantDecision(
            layer_name=node.name,
            weight_bits=base_bits,
            activation_bits=promoted_bits,
            sensitivity=sens,
        ))
        base_accuracy_loss += loss_at_4bit

    total_loss = base_accuracy_loss / max(len(layers), 1)

    if total_loss > accuracy_budget:
        sorted_by_sensitivity = sorted(
            enumerate(decisions),
            key=lambda x: x[1].sensitivity,
            reverse=True,
        )
        for idx, decision in sorted_by_sensitivity:
            if total_loss <= accuracy_budget:
                break
            loss_before = _estimate_loss_at_bits(layers[idx], base_bits, decision.sensitivity)
            loss_after = _estimate_loss_at_bits(layers[idx], promoted_bits, decision.sensitivity)
            improvement = loss_before - loss_after

            if improvement > 0:
                decision.weight_bits = promoted_bits
                decision.promoted = True
                total_loss -= improvement / max(len(layers), 1)

    avg_bits = sum(d.weight_bits for d in decisions) / max(len(decisions), 1)
    compression = 32.0 / avg_bits if avg_bits > 0 else 1.0

    return MixedPrecisionResult(
        decisions=decisions,
        accuracy_budget=accuracy_budget,
        estimated_accuracy_loss=total_loss,
        avg_weight_bits=avg_bits,
        compression_ratio=compression,
    )


def apply_mixed_precision(ir: TptIr, result: MixedPrecisionResult) -> TptIr:
    """Apply per-layer mixed-precision decisions to TPT-IR."""
    decision_map = {d.layer_name: d for d in result.decisions}
    new_nodes = []
    for node in ir.graph.nodes:
        d = decision_map.get(node.name)
        if d:
            attrs = dict(node.attributes)
            attrs["quant_weight_bits"] = d.weight_bits
            attrs["quant_activation_bits"] = d.activation_bits
            attrs["quant_sensitivity"] = d.sensitivity
            attrs["quant_promoted"] = d.promoted
            attrs["quant_profile"] = f"mixed-{d.weight_bits}bit"
            new_nodes.append(OpNode(
                id=node.id,
                op_type=node.op_type,
                name=node.name,
                attributes=attrs,
            ))
        else:
            new_nodes.append(node)
    ir.graph.nodes = new_nodes
    return ir


def _compute_sensitivities(
    ir: TptIr,
    profile_path: Any | None = None,
) -> dict[str, float]:
    """Compute per-layer sensitivity scores.

    If a .tptprofile is provided, use its activation_sparsity or
    activation range data. Otherwise, estimate from weight statistics.
    """
    sensitivities: dict[str, float] = {}

    if profile_path is not None:
        try:
            from pathlib import Path
            p = Path(profile_path)
            if p.exists():
                import json
                data = json.loads(p.read_text())
                for layer in data.get("layers", []):
                    name = layer.get("name", "")
                    range_val = layer.get("activation_range", layer.get("max_activation", 1.0))
                    if isinstance(range_val, (int, float)) and range_val > 0:
                        sensitivities[name] = min(range_val / 10.0, 1.0)
        except Exception:
            pass

    for node in ir.graph.nodes:
        if node.name not in sensitivities:
            sensitivities[node.name] = _gradient_free_sensitivity(node)

    return sensitivities


def _gradient_free_sensitivity(node: OpNode) -> float:
    """Estimate sensitivity from weight statistics when no profile is available.

    Layers with wider weight distributions or higher variance are more
    sensitive to quantization.
    """
    variance = node.attributes.get("weight_variance", 0.0)
    range_val = node.attributes.get("weight_range", 0.0)
    param_count = node.attributes.get("param_count", 0)

    if variance > 0:
        return min(variance * 2.0, 1.0)
    if range_val > 0:
        return min(range_val / 5.0, 1.0)
    if param_count > 1000000:
        return 0.7
    return 0.5


def _estimate_loss_at_bits(node: OpNode, bits: int, sensitivity: float) -> float:
    """Estimate accuracy loss for quantizing a layer to given bit-width."""
    base_loss_per_bit = 0.02
    quant_error = 1.0 / (2 ** bits)
    return quant_error * sensitivity * base_loss_per_bit * 100.0
