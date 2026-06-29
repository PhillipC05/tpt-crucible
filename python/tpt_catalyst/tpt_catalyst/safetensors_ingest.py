"""SafeTensors and HuggingFace model ingestion."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json
from pathlib import Path

from .ir import TptIr, OpNode, Edge, ComputationalGraph, ModelMetadata


@dataclass
class SafeTensorInfo:
    name: str
    dtype: str
    shape: list[int]
    data_offsets: tuple[int, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "dtype": self.dtype,
            "shape": self.shape,
            "data_offsets": list(self.data_offsets),
        }


class SafeTensorsIngester:
    """Ingest SafeTensors format models."""

    def __init__(self):
        self._available = False
        try:
            import safetensors
            self._available = True
        except ImportError:
            pass

    def ingest(self, path: Path) -> TptIr:
        if self._available:
            return self._ingest_with_library(path)
        return self._ingest_stub(path)

    def _ingest_with_library(self, path: Path) -> TptIr:
        try:
            from safetensors import safe_open
            with safe_open(str(path), framework="numpy") as f:
                tensors = f.keys()
                nodes = []
                for i, name in enumerate(tensors):
                    info = f.get_tensor(name)
                    nodes.append(OpNode(
                        id=i,
                        op_type="tensor",
                        name=name,
                        attributes={
                            "dtype": str(info.dtype),
                            "shape": list(info.shape),
                            "size_bytes": info.nbytes,
                        },
                    ))
                return TptIr(
                    version="1.0.0",
                    metadata=ModelMetadata(name=path.stem, source_format="safetensors"),
                    graph=ComputationalGraph(nodes=nodes),
                )
        except Exception:
            return self._ingest_stub(path)

    def _ingest_stub(self, path: Path) -> TptIr:
        return TptIr(
            version="1.0.0",
            metadata=ModelMetadata(name=path.stem, source_format="safetensors"),
            graph=ComputationalGraph(),
        )


class HuggingFaceIngester:
    """Ingest HuggingFace model directories."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or Path.home() / ".cache" / "tpt-crucible" / "hf"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def ingest(self, path: Path) -> TptIr:
        config_path = path / "config.json"
        if config_path.exists():
            return self._ingest_from_config(path, config_path)
        return self._ingest_from_weights(path)

    def _ingest_from_config(self, model_dir: Path, config_path: Path) -> TptIr:
        config = json.loads(config_path.read_text())
        model_type = config.get("model_type", "unknown")
        hidden_size = config.get("hidden_size", 0)
        num_layers = config.get("num_hidden_layers", 0)
        num_heads = config.get("num_attention_heads", 0)

        nodes = []
        for i in range(num_layers):
            nodes.append(OpNode(
                id=i * 3,
                op_type="matmul",
                name=f"layer_{i}_q_proj",
                attributes={"hidden_size": hidden_size, "num_heads": num_heads},
            ))
            nodes.append(OpNode(
                id=i * 3 + 1,
                op_type="attention",
                name=f"layer_{i}_attention",
                attributes={"num_heads": num_heads},
            ))
            nodes.append(OpNode(
                id=i * 3 + 2,
                op_type="matmul",
                name=f"layer_{i}_ffn",
                attributes={"hidden_size": hidden_size},
            ))

        edges = []
        for i in range(num_layers - 1):
            edges.append(Edge(from_id=i * 3 + 2, to_id=(i + 1) * 3, tensor_name=f"hidden_{i}"))

        return TptIr(
            version="1.0.0",
            metadata=ModelMetadata(
                name=config.get("architectures", [model_dir.stem])[0] if config.get("architectures") else model_dir.stem,
                source_format=f"huggingface_{model_type}",
                parameter_count=sum(
                    p.get("num_parameters", 0) for p in config.get("hidden_size", [0])
                ) if isinstance(config.get("hidden_size"), list) else 0,
            ),
            graph=ComputationalGraph(nodes=nodes, edges=edges),
        )

    def _ingest_from_weights(self, model_dir: Path) -> TptIr:
        weight_files = list(model_dir.glob("*.safetensors")) + list(model_dir.glob("*.bin"))
        nodes = []
        for i, wf in enumerate(weight_files[:10]):
            nodes.append(OpNode(
                id=i,
                op_type="tensor",
                name=wf.stem,
                attributes={"file": wf.name, "size_mb": wf.stat().st_size / 1024 / 1024},
            ))
        return TptIr(
            version="1.0.0",
            metadata=ModelMetadata(name=model_dir.name, source_format="huggingface"),
            graph=ComputationalGraph(nodes=nodes),
        )

    def pull_model(self, repo_id: str) -> Path:
        try:
            from huggingface_hub import snapshot_download
            path = snapshot_download(repo_id, cache_dir=str(self.cache_dir))
            return Path(path)
        except ImportError:
            return self.cache_dir / repo_id.replace("/", "_")
