"""AWQ/GPTQ quantized model ingestion — read quantize_config.json from HF repo, extract per-layer bit-width assignments."""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

from .ir import TptIr, OpNode, Edge, ModelMetadata, ComputationalGraph


@dataclass
class QuantLayerConfig:
    """Per-layer quantization configuration."""
    layer_name: str
    bits: int
    group_size: int = 128
    desc_act: bool = False
    static_groups: bool = False
    version: str = "GEMM"  # GEMM or GEMV
    damp_percent: float = 0.01

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer_name": self.layer_name,
            "bits": self.bits,
            "group_size": self.group_size,
            "desc_act": self.desc_act,
            "static_groups": self.static_groups,
            "version": self.version,
            "damp_percent": self.damp_percent,
        }


@dataclass
class AwqConfig:
    """AWQ quantization configuration."""
    bits: int = 4
    group_size: int = 128
    version: str = "GEMM"
    zero_point: bool = True
    lm_head: bool = False
    quant_method: str = "awq"
    per_layer_configs: list[QuantLayerConfig] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bits": self.bits,
            "group_size": self.group_size,
            "version": self.version,
            "zero_point": self.zero_point,
            "lm_head": self.lm_head,
            "quant_method": self.quant_method,
            "per_layer_configs": [c.to_dict() for c in self.per_layer_configs],
        }


@dataclass
class GptqConfig:
    """GPTQ quantization configuration."""
    bits: int = 4
    group_size: int = 128
    damp_percent: float = 0.01
    static_groups: bool = False
    desc_act: bool = False
    sym: bool = True
    true_sequential: bool = True
    quant_method: str = "gptq"
    per_layer_configs: list[QuantLayerConfig] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bits": self.bits,
            "group_size": self.group_size,
            "damp_percent": self.damp_percent,
            "static_groups": self.static_groups,
            "desc_act": self.desc_act,
            "sym": self.sym,
            "true_sequential": self.true_sequential,
            "quant_method": self.quant_method,
            "per_layer_configs": [c.to_dict() for c in self.per_layer_configs],
        }


def detect_quantize_config(path: Path) -> bool:
    """Detect if a directory contains a quantize_config.json (AWQ/GPTQ)."""
    config_path = path / "quantize_config.json" if path.is_dir() else path.parent / "quantize_config.json"
    return config_path.exists()


def parse_quantize_config(config_path: Path) -> AwqConfig | GptqConfig:
    """Parse a quantize_config.json file and return the quantization config."""
    data = json.loads(config_path.read_text())

    quant_method = data.get("quant_method", "").lower()

    if quant_method == "awq":
        return _parse_awq_config(data)
    elif quant_method == "gptq":
        return _parse_gptq_config(data)
    else:
        # Try to infer from fields
        if "zero_point" in data:
            return _parse_awq_config(data)
        else:
            return _parse_gptq_config(data)


def _parse_awq_config(data: dict[str, Any]) -> AwqConfig:
    """Parse AWQ-specific quantization config."""
    config = AwqConfig(
        bits=data.get("bits", 4),
        group_size=data.get("group_size", 128),
        version=data.get("version", "GEMM"),
        zero_point=data.get("zero_point", True),
        lm_head=data.get("lm_head", False),
        quant_method="awq",
    )

    # Extract per-layer configs if available
    if "quant_layer_configs" in data:
        for layer_data in data["quant_layer_configs"]:
            config.per_layer_configs.append(QuantLayerConfig(
                layer_name=layer_data.get("name", "unknown"),
                bits=layer_data.get("bits", config.bits),
                group_size=layer_data.get("group_size", config.group_size),
                desc_act=layer_data.get("desc_act", False),
                static_groups=layer_data.get("static_groups", False),
                version=layer_data.get("version", config.version),
            ))

    return config


def _parse_gptq_config(data: dict[str, Any]) -> GptqConfig:
    """Parse GPTQ-specific quantization config."""
    config = GptqConfig(
        bits=data.get("bits", 4),
        group_size=data.get("group_size", 128),
        damp_percent=data.get("damp_percent", 0.01),
        static_groups=data.get("static_groups", False),
        desc_act=data.get("desc_act", False),
        sym=data.get("sym", True),
        true_sequential=data.get("true_sequential", True),
        quant_method="gptq",
    )

    # Extract per-layer configs if available
    if "quant_layer_configs" in data:
        for layer_data in data["quant_layer_configs"]:
            config.per_layer_configs.append(QuantLayerConfig(
                layer_name=layer_data.get("name", "unknown"),
                bits=layer_data.get("bits", config.bits),
                group_size=layer_data.get("group_size", config.group_size),
                desc_act=layer_data.get("desc_act", config.desc_act),
                static_groups=layer_data.get("static_groups", config.static_groups),
                damp_percent=layer_data.get("damp_percent", config.damp_percent),
            ))

    return config


def ingest_awq_gptq(model_dir: Path) -> TptIr:
    """Ingest an AWQ/GPTQ quantized model from a HuggingFace directory.

    Reads quantize_config.json to extract per-layer bit-width assignments
    and passes them to TPT-IR quantization metadata.
    """
    config_path = model_dir / "quantize_config.json"
    if not config_path.exists():
        return _stub_awq_gptq(model_dir)

    quant_config = parse_quantize_config(config_path)

    # Try to load model config for architecture info
    model_config_path = model_dir / "config.json"
    model_name = model_dir.name
    num_layers = 0
    hidden_size = 0
    num_heads = 0

    if model_config_path.exists():
        model_config = json.loads(model_config_path.read_text())
        model_name = model_config.get("architectures", [model_name])[0] if model_config.get("architectures") else model_name
        num_layers = model_config.get("num_hidden_layers", 0)
        hidden_size = model_config.get("hidden_size", 0)
        num_heads = model_config.get("num_attention_heads", 0)

    # Build TPT-IR with per-layer quantization metadata
    nodes = []
    edges = []

    # If we have per-layer configs, use them directly
    if quant_config.per_layer_configs:
        for i, layer_cfg in enumerate(quant_config.per_layer_configs):
            nodes.append(OpNode(
                id=i,
                op_type="quantized_linear",
                name=layer_cfg.layer_name,
                attributes={
                    "quant_method": quant_config.quant_method,
                    "bits": layer_cfg.bits,
                    "group_size": layer_cfg.group_size,
                    "desc_act": layer_cfg.desc_act,
                    "static_groups": layer_cfg.static_groups,
                    "version": getattr(layer_cfg, 'version', 'GEMM'),
                },
            ))
    else:
        # Generate per-layer configs from model architecture
        for i in range(num_layers):
            # QKV projection
            nodes.append(OpNode(
                id=i * 4,
                op_type="quantized_linear",
                name=f"model.layers.{i}.self_attn.q_proj",
                attributes={
                    "quant_method": quant_config.quant_method,
                    "bits": quant_config.bits,
                    "group_size": quant_config.group_size,
                    "hidden_size": hidden_size,
                    "num_heads": num_heads,
                },
            ))
            # Output projection
            nodes.append(OpNode(
                id=i * 4 + 1,
                op_type="quantized_linear",
                name=f"model.layers.{i}.self_attn.o_proj",
                attributes={
                    "quant_method": quant_config.quant_method,
                    "bits": quant_config.bits,
                    "group_size": quant_config.group_size,
                    "hidden_size": hidden_size,
                },
            ))
            # FFN up
            nodes.append(OpNode(
                id=i * 4 + 2,
                op_type="quantized_linear",
                name=f"model.layers.{i}.mlp.up_proj",
                attributes={
                    "quant_method": quant_config.quant_method,
                    "bits": quant_config.bits,
                    "group_size": quant_config.group_size,
                    "hidden_size": hidden_size,
                },
            ))
            # FFN down
            nodes.append(OpNode(
                id=i * 4 + 3,
                op_type="quantized_linear",
                name=f"model.layers.{i}.mlp.down_proj",
                attributes={
                    "quant_method": quant_config.quant_method,
                    "bits": quant_config.bits,
                    "group_size": quant_config.group_size,
                    "hidden_size": hidden_size,
                },
            ))

    # Create edges between consecutive layers
    for i in range(1, len(nodes)):
        edges.append(Edge(
            from_id=i - 1,
            to_id=i,
            tensor_name=f"{nodes[i-1].name}_to_{nodes[i].name}",
        ))

    # Calculate parameter count
    param_count = 0
    if hidden_size > 0 and num_layers > 0:
        # Approximate: 4 * hidden_size^2 per layer (QKV + O + FFN up + FFN down)
        param_count = num_layers * 4 * hidden_size * hidden_size

    return TptIr(
        version="1.0.0",
        metadata=ModelMetadata(
            name=model_name,
            source_format=f"huggingface_{quant_config.quant_method}",
            parameter_count=param_count,
        ),
        graph=ComputationalGraph(nodes=nodes, edges=edges),
    )


def _stub_awq_gptq(model_dir: Path) -> TptIr:
    """Stub when quantize_config.json is not found."""
    return TptIr(
        version="1.0.0",
        metadata=ModelMetadata(
            name=model_dir.name,
            source_format="huggingface_awq_gptq",
            parameter_count=0,
        ),
        graph=ComputationalGraph(),
    )