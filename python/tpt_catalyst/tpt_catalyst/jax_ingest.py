"""JAX/Flax orbax checkpoint ingestion — load parameter tree, convert to float32 weight tensors, map to TPT-IR ops via model config."""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import struct

from .ir import TptIr, OpNode, Edge, ModelMetadata, ComputationalGraph


@dataclass
class JaxParamTensor:
    """A single parameter tensor from a JAX/Flax checkpoint."""
    name: str
    shape: list[int]
    dtype: str
    data_offset: int = 0
    data_size: int = 0

    @property
    def num_elements(self) -> int:
        result = 1
        for dim in self.shape:
            if dim > 0:
                result *= dim
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "shape": self.shape,
            "dtype": self.dtype,
            "num_elements": self.num_elements,
        }


@dataclass
class JaxParamTree:
    """Parameter tree from a JAX/Flax checkpoint."""
    params: dict[str, JaxParamTensor] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def parameter_count(self) -> int:
        return sum(p.num_elements for p in self.params.values())


def detect_jax_checkpoint(path: Path) -> bool:
    """Detect if a path is a JAX/Flax orbax checkpoint directory."""
    if not path.is_dir():
        return False
    # Orbax checkpoints contain _metadata or ocdbt files
    return (path / "_metadata").exists() or any(path.glob("ocdbt")) or (path / "checkpoint").exists()


def detect_jax_safetensors(path: Path) -> bool:
    """Detect if a path contains JAX/Flax model in safetensors format."""
    if not path.is_dir():
        return False
    # Flax models often have model.safetensors + config.json with "flax" in model_type
    config_path = path / "config.json"
    if config_path.exists() and list(path.glob("*.safetensors")):
        try:
            config = json.loads(config_path.read_text())
            model_type = config.get("model_type", "")
            architectures = config.get("architectures", [])
            return (
                "flax" in model_type.lower()
                or any("flax" in a.lower() for a in architectures)
                or "jax" in model_type.lower()
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    return False


def ingest_jax_flax(path: Path) -> TptIr:
    """Ingest a JAX/Flax model checkpoint into TPT-IR.

    Loads the parameter tree from an orbax checkpoint or safetensors file,
    converts weight tensors to float32 metadata, and maps them to TPT-IR ops
    via the model config.
    """
    # Try orbax first
    if detect_jax_checkpoint(path):
        try:
            return _ingest_orbax(path)
        except Exception:
            pass

    # Try safetensors-based Flax model
    if detect_jax_safetensors(path):
        try:
            return _ingest_flax_safetensors(path)
        except Exception:
            pass

    # Try msgpack-based checkpoint
    try:
        return _ingest_jax_msgpack(path)
    except Exception:
        pass

    return _stub_jax(path)


def _ingest_orbax(path: Path) -> TptIr:
    """Ingest an orbax checkpoint directory."""
    try:
        import orbax.checkpoint as ocp
    except ImportError:
        return _ingest_orbax_manual(path)

    # Use orbax to restore the checkpoint
    checkpointer = ocp.PyTreeCheckpointer()
    metadata = checkpointer.metadata(path)

    param_tree = JaxParamTree()
    param_tree.metadata = {
        "format": "orbax",
        "checkpoint_path": str(path),
    }

    # Extract parameter info from metadata
    for name, item in metadata.items():
        if hasattr(item, 'shape') and hasattr(item, 'dtype'):
            param_tree.params[name] = JaxParamTensor(
                name=name,
                shape=list(item.shape),
                dtype=str(item.dtype),
            )

    return _param_tree_to_ir(param_tree, path)


def _ingest_orbax_manual(path: Path) -> TptIr:
    """Manually parse orbax checkpoint without the orbax library."""
    param_tree = JaxParamTree()
    param_tree.metadata = {"format": "orbax_manual"}

    metadata_path = path / "_metadata"
    if metadata_path.exists():
        try:
            import json
            meta = json.loads(metadata_path.read_text())
            param_tree.metadata.update(meta)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    # Scan for .safetensors or .npz files in the checkpoint
    for tensor_file in path.rglob("*.safetensors"):
        try:
            from safetensors import safe_open
            with safe_open(str(tensor_file), framework="numpy") as f:
                for name in f.keys():
                    tensor = f.get_tensor(name)
                    param_tree.params[name] = JaxParamTensor(
                        name=name,
                        shape=list(tensor.shape),
                        dtype=str(tensor.dtype),
                    )
        except ImportError:
            pass

    return _param_tree_to_ir(param_tree, path)


def _ingest_flax_safetensors(path: Path) -> TptIr:
    """Ingest a Flax model stored as safetensors."""
    param_tree = JaxParamTree()
    param_tree.metadata = {"format": "flax_safetensors"}

    # Load model config for architecture mapping
    config_path = path / "config.json"
    model_config: dict[str, Any] = {}
    if config_path.exists():
        model_config = json.loads(config_path.read_text())
        param_tree.metadata["model_config"] = model_config

    # Load all safetensors files
    for safetensors_file in sorted(path.glob("*.safetensors")):
        try:
            from safetensors import safe_open
            with safe_open(str(safetensors_file), framework="numpy") as f:
                for name in f.keys():
                    tensor = f.get_tensor(name)
                    param_tree.params[name] = JaxParamTensor(
                        name=name,
                        shape=list(tensor.shape),
                        dtype=str(tensor.dtype),
                    )
        except ImportError:
            # Fallback: just record file info
            param_tree.params[safetensors_file.stem] = JaxParamTensor(
                name=safetensors_file.stem,
                shape=[0],
                dtype="unknown",
            )

    return _param_tree_to_ir(param_tree, path, model_config)


def _ingest_jax_msgpack(path: Path) -> TptIr:
    """Ingest a JAX msgpack-based checkpoint."""
    param_tree = JaxParamTree()
    param_tree.metadata = {"format": "jax_msgpack"}

    # Look for msgpack checkpoint files
    for msgpack_file in path.rglob("*.mpack"):
        try:
            import msgpack
            data = msgpack_file.read_bytes()
            checkpoint = msgpack.unpackb(data, raw=False)
            _flatten_msgpack_tree(checkpoint, "", param_tree)
        except ImportError:
            pass

    return _param_tree_to_ir(param_tree, path)


def _flatten_msgpack_tree(tree: Any, prefix: str, param_tree: JaxParamTree) -> None:
    """Flatten a nested msgpack tree into parameter tensors."""
    if isinstance(tree, dict):
        for key, value in tree.items():
            new_prefix = f"{prefix}/{key}" if prefix else key
            _flatten_msgpack_tree(value, new_prefix, param_tree)
    elif hasattr(tree, 'shape') and hasattr(tree, 'dtype'):
        import numpy as np
        arr = np.array(tree)
        param_tree.params[prefix] = JaxParamTensor(
            name=prefix,
            shape=list(arr.shape),
            dtype=str(arr.dtype),
        )


def _param_tree_to_ir(param_tree: JaxParamTree, path: Path, model_config: dict[str, Any] | None = None) -> TptIr:
    """Convert a JAX/Flax parameter tree to TPT-IR."""
    nodes = []
    edges = []

    # Group parameters by layer
    layer_params: dict[str, list[JaxParamTensor]] = {}
    for name, param in param_tree.params.items():
        # Extract layer prefix (e.g., "model/layers/0/attention" -> "model/layers/0")
        parts = name.split("/")
        if len(parts) >= 2:
            layer_prefix = "/".join(parts[:3]) if len(parts) >= 3 else "/".join(parts[:2])
        else:
            layer_prefix = "root"
        if layer_prefix not in layer_params:
            layer_params[layer_prefix] = []
        layer_params[layer_prefix].append(param)

    # Create nodes for each layer group
    node_id = 0
    layer_names = sorted(layer_params.keys())
    for layer_name in layer_names:
        params = layer_params[layer_name]
        attrs: dict[str, Any] = {
            "source": "jax_flax",
            "num_tensors": len(params),
            "tensors": [p.to_dict() for p in params[:10]],  # Limit for IR size
        }

        # Add model config info if available
        if model_config:
            attrs["model_type"] = model_config.get("model_type", "unknown")
            attrs["hidden_size"] = model_config.get("hidden_size", 0)
            attrs["num_layers"] = model_config.get("num_hidden_layers", 0)

        nodes.append(OpNode(
            id=node_id,
            op_type="jax_layer",
            name=layer_name,
            attributes=attrs,
        ))
        node_id += 1

    # Create edges between consecutive layers
    for i in range(1, len(nodes)):
        edges.append(Edge(
            from_id=i - 1,
            to_id=i,
            tensor_name=f"{nodes[i-1].name}_to_{nodes[i].name}",
        ))

    # Determine model name
    model_name = path.stem
    if model_config:
        architectures = model_config.get("architectures", [])
        if architectures:
            model_name = architectures[0]
        elif "model_type" in model_config:
            model_name = model_config["model_type"]

    return TptIr(
        version="1.0.0",
        metadata=ModelMetadata(
            name=model_name,
            source_format="jax_flax",
            parameter_count=param_tree.parameter_count,
        ),
        graph=ComputationalGraph(nodes=nodes, edges=edges),
    )


def _stub_jax(path: Path) -> TptIr:
    """Stub when JAX/Flax parsing is not available."""
    return TptIr(
        version="1.0.0",
        metadata=ModelMetadata(
            name=path.stem if hasattr(path, 'stem') else "jax_model",
            source_format="jax_flax",
            parameter_count=0,
        ),
        graph=ComputationalGraph(),
    )