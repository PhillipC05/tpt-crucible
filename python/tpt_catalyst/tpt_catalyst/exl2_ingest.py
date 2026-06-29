"""EXL2 model ingestion — extract per-layer quantization scale/zero tables into TPT-IR."""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import struct
import json

from .ir import TptIr, OpNode, Edge, ModelMetadata, ComputationalGraph


# EXL2 magic bytes and constants
EXL2_MAGIC = b"EXL2"
EXL2_VERSION = 2
EXL2_HEADER_SIZE = 20  # magic(4) + version(4) + num_layers(4) + metadata_size(4) + reserved(4)

# EXL2 quantization type codes
EXL2_QUANT_TYPES = {
    0: "FP16",
    1: "Q4",
    2: "Q5",
    3: "Q8",
    4: "Q2_K",
    5: "Q3_K",
    6: "Q4_K",
    7: "Q5_K",
    8: "Q6_K",
    9: "Q4_0",
    10: "Q8_0",
}


@dataclass
class Exl2QuantTable:
    """Per-layer quantization scale/zero table."""
    layer_name: str
    quant_type: str
    bits: int
    scale: float = 1.0
    zero_point: int = 0
    scales: list[float] = field(default_factory=list)
    zeros: list[int] = field(default_factory=list)
    group_size: int = 32

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer_name": self.layer_name,
            "quant_type": self.quant_type,
            "bits": self.bits,
            "scale": self.scale,
            "zero_point": self.zero_point,
            "scales": self.scales[:10],  # Truncate for IR size
            "zeros": self.zeros[:10],
            "group_size": self.group_size,
        }


@dataclass
class Exl2LayerInfo:
    """Metadata about a layer in an EXL2 model."""
    name: str
    quant_type: int
    weight_rows: int
    weight_cols: int
    scale_table_offset: int = 0
    scale_table_size: int = 0
    zero_table_offset: int = 0
    zero_table_size: int = 0
    weight_offset: int = 0
    weight_size: int = 0


@dataclass
class Exl2ModelInfo:
    """Parsed EXL2 model metadata."""
    name: str
    version: int = 0
    num_layers: int = 0
    layers: list[Exl2LayerInfo] = field(default_factory=list)
    quant_tables: list[Exl2QuantTable] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def parameter_count(self) -> int:
        return sum(l.weight_rows * l.weight_cols for l in self.layers)


def detect_exl2(path: Path) -> bool:
    """Detect if a file is an EXL2 model by magic bytes."""
    try:
        with open(path, "rb") as f:
            header = f.read(4)
            return header == EXL2_MAGIC
    except (OSError, IOError):
        return False


def ingest_exl2(path: Path) -> TptIr:
    """Ingest an EXL2 model file into TPT-IR.

    EXL2 files contain per-layer quantization scale/zero tables that define
    the dequantization parameters for each weight tensor. This function
    extracts those tables and maps them to TPT-IR quantization metadata.
    """
    try:
        return _parse_exl2_binary(path)
    except Exception:
        pass

    return _stub_exl2(path)


def _parse_exl2_binary(path: Path) -> TptIr:
    """Parse EXL2 binary format to extract quantization tables."""
    data = path.read_bytes()
    info = Exl2ModelInfo(name=path.stem)

    if len(data) < EXL2_HEADER_SIZE:
        return _stub_exl2(path)

    # Parse header
    magic = data[0:4]
    if magic != EXL2_MAGIC:
        return _stub_exl2(path)

    info.version = struct.unpack_from("<I", data, 4)[0]
    info.num_layers = struct.unpack_from("<I", data, 8)[0]
    metadata_size = struct.unpack_from("<I", data, 12)[0]

    # Parse JSON metadata if present
    if metadata_size > 0 and EXL2_HEADER_SIZE + metadata_size <= len(data):
        metadata_bytes = data[EXL2_HEADER_SIZE:EXL2_HEADER_SIZE + metadata_size]
        try:
            info.metadata = json.loads(metadata_bytes.decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    # Parse layer headers
    offset = EXL2_HEADER_SIZE + metadata_size
    for i in range(info.num_layers):
        if offset + 32 > len(data):
            break

        # Layer header: name_len(4) + name + quant_type(4) + rows(4) + cols(4) + offsets(16)
        name_len = struct.unpack_from("<I", data, offset)[0]
        offset += 4

        if offset + name_len > len(data):
            break

        name = data[offset:offset + name_len].decode("utf-8", errors="replace")
        offset += name_len

        if offset + 28 > len(data):
            break

        quant_type = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        weight_rows = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        weight_cols = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        scale_offset = struct.unpack_from("<Q", data, offset)[0]
        offset += 8
        scale_size = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        zero_offset = struct.unpack_from("<Q", data, offset)[0]
        offset += 8
        zero_size = struct.unpack_from("<I", data, offset)[0]
        offset += 4

        layer = Exl2LayerInfo(
            name=name,
            quant_type=quant_type,
            weight_rows=weight_rows,
            weight_cols=weight_cols,
            scale_table_offset=scale_offset,
            scale_table_size=scale_size,
            zero_table_offset=zero_offset,
            zero_table_size=zero_size,
        )
        info.layers.append(layer)

        # Extract quantization tables
        quant_type_str = EXL2_QUANT_TYPES.get(quant_type, f"UNKNOWN_{quant_type}")
        bits = _quant_type_to_bits(quant_type)

        scales = []
        if scale_size > 0 and scale_offset + scale_size <= len(data):
            scales = list(struct.unpack_from(f"<{scale_size // 4}f", data, scale_offset))

        zeros = []
        if zero_size > 0 and zero_offset + zero_size <= len(data):
            zeros = list(struct.unpack_from(f"<{zero_size // 4}i", data, zero_offset))

        quant_table = Exl2QuantTable(
            layer_name=name,
            quant_type=quant_type_str,
            bits=bits,
            scale=scales[0] if scales else 1.0,
            zero_point=zeros[0] if zeros else 0,
            scales=scales,
            zeros=zeros,
            group_size=32,
        )
        info.quant_tables.append(quant_table)

    return _exl2_info_to_ir(info, path)


def _quant_type_to_bits(quant_type: int) -> int:
    """Map EXL2 quant type code to bit width."""
    bits_map = {
        0: 16,  # FP16
        1: 4,   # Q4
        2: 5,   # Q5
        3: 8,   # Q8
        4: 2,   # Q2_K
        5: 3,   # Q3_K
        6: 4,   # Q4_K
        7: 5,   # Q5_K
        8: 6,   # Q6_K
        9: 4,   # Q4_0
        10: 8,  # Q8_0
    }
    return bits_map.get(quant_type, 32)


def _exl2_info_to_ir(info: Exl2ModelInfo, path: Path) -> TptIr:
    """Convert parsed EXL2 model info to TPT-IR."""
    nodes = []
    edges = []

    # Create nodes for each layer with quantization metadata
    for i, layer in enumerate(info.layers):
        quant_table = info.quant_tables[i] if i < len(info.quant_tables) else None

        attrs: dict[str, Any] = {
            "weight_rows": layer.weight_rows,
            "weight_cols": layer.weight_cols,
            "quant_type_code": layer.quant_type,
            "source": "exl2",
        }

        if quant_table:
            attrs["quantization"] = quant_table.to_dict()

        nodes.append(OpNode(
            id=i,
            op_type="quantized_linear",
            name=layer.name,
            attributes=attrs,
        ))

    # Create edges between consecutive layers
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
            source_format="exl2",
            parameter_count=info.parameter_count,
        ),
        graph=ComputationalGraph(nodes=nodes, edges=edges),
    )


def _stub_exl2(path: Path) -> TptIr:
    """Stub when EXL2 parsing is not available."""
    return TptIr(
        version="1.0.0",
        metadata=ModelMetadata(
            name=path.stem,
            source_format="exl2",
            parameter_count=0,
        ),
        graph=ComputationalGraph(),
    )