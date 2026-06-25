"""GGUF model ingestion — quantization-preserving format for llama.cpp models."""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import gguf
    GGUF_AVAILABLE = True
except ImportError:
    GGUF_AVAILABLE = False

from .ir import TptIr, OpNode, Edge, ModelMetadata, ComputationalGraph


@dataclass
class QuantizationMetadata:
    """Quantization type and parameters for a tensor."""
    quant_type: str
    bits: int
    group_size: int = 32
    block_size: int = 32

    @property
    def bytes_per_element(self) -> float:
        if self.quant_type in ("F16", "F32"):
            return 2.0 if self.quant_type == "F16" else 4.0
        return self.bits / 8.0


@dataclass
class TensorInfo:
    """Metadata about a tensor in a GGUF model."""
    name: str
    shape: list[int]
    dtype: str
    offset: int
    size: int
    quantization: QuantizationMetadata | None = None


@dataclass
class GgufModelInfo:
    """Parsed GGUF model metadata."""
    name: str
    architecture: str
    quant_type: str
    tensors: list[TensorInfo] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def parameter_count(self) -> int:
        return sum(
            t.quantization.bits if t.quantization else 32
            for t in self.tensors
        )


def ingest_gguf(path: Path) -> TptIr:
    """Ingest a GGUF model file into TPT-IR.

    GGUF files are quantized at the source. TPT-IR preserves quantization
    metadata so that backends (Alloy, Fusion) can generate hardware-appropriate
    compute (e.g., INT4 MAC arrays for Q4 models).
    """
    if not GGUF_AVAILABLE:
        return _stub_gguf(path)

    reader = gguf.GGUFReader(str(path))
    model_info = _parse_gguf_reader(reader, path)
    return _model_info_to_ir(model_info)


def _stub_gguf(path: Path) -> TptIr:
    """Stub when gguf package is not available."""
    return TptIr(
        version="1.0.0",
        metadata=ModelMetadata(
            name=path.stem,
            source_format="gguf",
            parameter_count=0,
        ),
        graph=ComputationalGraph(),
    )


def _parse_gguf_reader(reader: Any, path: Path) -> GgufModelInfo:
    """Parse GGUF metadata and tensor info."""
    arch = ""
    quant_type = "F32"
    name = path.stem
    tensors = []

    for field_obj in reader.fields.values():
        key = field_obj.name
        if key == "general.architecture":
            arch = str(field_obj.parts[field_obj.data][0], errors="replace")
        elif key == "general.name":
            name = str(field_obj.parts[field_obj.data][0], errors="replace")

    for tensor in reader.tensors:
        dtype_str = _tensor_dtype_to_str(tensor)
        quant_info = _extract_quantization(dtype_str, tensor)
        tensors.append(TensorInfo(
            name=tensor.name,
            shape=list(tensor.shape),
            dtype=dtype_str,
            offset=0,
            size=tensor.n_elements * (quant_info.bits / 8 if quant_info else 4),
            quantization=quant_info,
        ))

        if quant_info and not quant_type.startswith("Q"):
            quant_type = quant_info.quant_type

    return GgufModelInfo(
        name=name,
        architecture=arch,
        quant_type=quant_type,
        tensors=tensors,
    )


def _tensor_dtype_to_str(tensor) -> str:
    """Convert GGUF tensor dtype to string."""
    dtype_map = {
        0: "F32",
        1: "F16",
        2: "Q4_0",
        3: "Q4_1",
        7: "Q8_0",
        8: "Q8_1",
        10: "Q2_K",
        11: "Q3_K_S",
        12: "Q3_K_M",
        13: "Q3_K_L",
        14: "Q4_K_S",
        15: "Q4_K_M",
        16: "Q5_K_S",
        17: "Q5_K_M",
        18: "Q6_K",
    }
    return dtype_map.get(tensor.data_type, "F32")


def _extract_quantization(dtype_str: str, tensor) -> QuantizationMetadata | None:
    """Extract quantization parameters from dtype string."""
    quant_info_map = {
        "Q4_0": QuantizationMetadata(quant_type="Q4_0", bits=4, block_size=32),
        "Q4_1": QuantizationMetadata(quant_type="Q4_1", bits=4.5, block_size=32),
        "Q8_0": QuantizationMetadata(quant_type="Q8_0", bits=8, block_size=32),
        "Q8_1": QuantizationMetadata(quant_type="Q8_1", bits=8.5, block_size=32),
        "Q2_K": QuantizationMetadata(quant_type="Q2_K", bits=2, group_size=256),
        "Q3_K_S": QuantizationMetadata(quant_type="Q3_K_S", bits=3, group_size=256),
        "Q3_K_M": QuantizationMetadata(quant_type="Q3_K_M", bits=3, group_size=256),
        "Q3_K_L": QuantizationMetadata(quant_type="Q3_K_L", bits=3, group_size=256),
        "Q4_K_S": QuantizationMetadata(quant_type="Q4_K_S", bits=4, group_size=256),
        "Q4_K_M": QuantizationMetadata(quant_type="Q4_K_M", bits=4, group_size=256),
        "Q5_K_S": QuantizationMetadata(quant_type="Q5_K_S", bits=5, group_size=256),
        "Q5_K_M": QuantizationMetadata(quant_type="Q5_K_M", bits=5, group_size=256),
        "Q6_K": QuantizationMetadata(quant_type="Q6_K", bits=6, group_size=256),
    }
    return quant_info_map.get(dtype_str)


def _model_info_to_ir(info: GgufModelInfo) -> TptIr:
    """Convert parsed GGUF model info to TPT-IR."""
    nodes = []
    edges = []

    for i, tensor in enumerate(info.tensors):
        attrs = {
            "shape": tensor.shape,
            "dtype": tensor.dtype,
            "size_bytes": tensor.size,
        }
        if tensor.quantization:
            attrs["quant_type"] = tensor.quantization.quant_type
            attrs["quant_bits"] = tensor.quantization.bits
            attrs["quant_group_size"] = tensor.quantization.group_size

        nodes.append(OpNode(
            id=i,
            op_type="tensor",
            name=tensor.name,
            attributes=attrs,
        ))

    for i in range(1, len(nodes)):
        edges.append(Edge(
            from_id=i - 1,
            to_id=i,
            tensor_name=f"{nodes[i-1].name}_to_{nodes[i].name}",
        ))

    return TptIr(
        version="1.0.0",
        metadata=ModelMetadata(
            name=info.name,
            source_format="gguf",
            parameter_count=info.parameter_count,
        ),
        graph=ComputationalGraph(nodes=nodes, edges=edges),
    )
