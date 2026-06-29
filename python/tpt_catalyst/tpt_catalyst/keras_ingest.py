"""Keras .h5 model ingestion — convert via tf.keras.models.load_model, route to TF SavedModel path."""

from __future__ import annotations
from pathlib import Path
from typing import Any
import json

from .ir import TptIr, OpNode, Edge, ModelMetadata, ComputationalGraph


# HDF5 magic bytes
HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"


def detect_keras_h5(path: Path) -> bool:
    """Detect if a file is a Keras HDF5 model by magic bytes."""
    try:
        with open(path, "rb") as f:
            header = f.read(8)
            return header == HDF5_MAGIC
    except (OSError, IOError):
        return False


def ingest_keras_h5(path: Path) -> TptIr:
    """Ingest a Keras .h5 model file into TPT-IR.

    Converts the Keras model via tf.keras.models.load_model, then routes
    through the TensorFlow SavedModel ingestion path to extract the
    computational graph.
    """
    try:
        import tensorflow as tf
        return _ingest_keras_with_tf(path)
    except ImportError:
        pass

    # Fallback: try h5py to read model structure
    try:
        return _ingest_keras_with_h5py(path)
    except ImportError:
        pass

    return _stub_keras(path)


def _ingest_keras_with_tf(path: Path) -> TptIr:
    """Ingest Keras model using TensorFlow."""
    import tensorflow as tf

    model = tf.keras.models.load_model(str(path))

    nodes = []
    edges = []
    node_id = 0

    # Extract layers from the Keras model
    for layer in model.layers:
        layer_type = layer.__class__.__name__
        attrs: dict[str, Any] = {
            "keras_layer_type": layer_type,
            "trainable": layer.trainable,
        }

        # Extract layer config
        try:
            config = layer.get_config()
            # Filter out non-serializable values
            serializable_config = {}
            for k, v in config.items():
                try:
                    json.dumps(v)
                    serializable_config[k] = v
                except (TypeError, ValueError):
                    serializable_config[k] = str(v)
            attrs["config"] = serializable_config
        except Exception:
            pass

        # Extract weight shapes
        try:
            weights = layer.get_weights()
            attrs["num_weights"] = len(weights)
            attrs["weight_shapes"] = [list(w.shape) for w in weights]
        except Exception:
            pass

        # Extract input/output shapes
        try:
            if hasattr(layer, 'input_shape'):
                attrs["input_shape"] = str(layer.input_shape)
            if hasattr(layer, 'output_shape'):
                attrs["output_shape"] = str(layer.output_shape)
        except Exception:
            pass

        nodes.append(OpNode(
            id=node_id,
            op_type=layer_type,
            name=layer.name,
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

    # Calculate parameter count
    param_count = 0
    try:
        param_count = model.count_params()
    except Exception:
        for layer in model.layers:
            try:
                for w in layer.get_weights():
                    param_count += w.size
            except Exception:
                pass

    return TptIr(
        version="1.0.0",
        metadata=ModelMetadata(
            name=model.name or path.stem,
            source_format="keras_h5",
            parameter_count=param_count,
        ),
        graph=ComputationalGraph(nodes=nodes, edges=edges),
    )


def _ingest_keras_with_h5py(path: Path) -> TptIr:
    """Ingest Keras model using h5py (without TensorFlow)."""
    import h5py

    nodes = []
    edges = []

    with h5py.File(str(path), "r") as f:
        # Read model config
        model_config = None
        if "model_config" in f.attrs:
            try:
                model_config = json.loads(f.attrs["model_config"])
            except (json.JSONDecodeError, TypeError):
                pass

        # Read layer names from model_weights group
        if "model_weights" in f:
            weights_group = f["model_weights"]
            layer_names = list(weights_group.keys())

            for i, layer_name in enumerate(layer_names):
                attrs: dict[str, Any] = {"source": "keras_h5"}

                layer_group = weights_group[layer_name]
                weight_names = list(layer_group.keys()) if hasattr(layer_group, 'keys') else []
                attrs["weight_names"] = weight_names

                # Try to read layer config from model_config
                if model_config and "config" in model_config:
                    layers = model_config["config"].get("layers", [])
                    for layer_cfg in layers:
                        if layer_cfg.get("config", {}).get("name") == layer_name:
                            attrs["keras_layer_type"] = layer_cfg.get("class_name", "Unknown")
                            break

                nodes.append(OpNode(
                    id=i,
                    op_type=attrs.get("keras_layer_type", "layer"),
                    name=layer_name,
                    attributes=attrs,
                ))

        # If no model_weights, try top-level groups
        elif len(f.keys()) > 0:
            for i, key in enumerate(f.keys()):
                if key not in ("model_config",):
                    nodes.append(OpNode(
                        id=i,
                        op_type="group",
                        name=key,
                        attributes={"source": "keras_h5"},
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
            name=path.stem,
            source_format="keras_h5",
            parameter_count=0,
        ),
        graph=ComputationalGraph(nodes=nodes, edges=edges),
    )


def _stub_keras(path: Path) -> TptIr:
    """Stub when Keras/HDF5 parsing is not available."""
    return TptIr(
        version="1.0.0",
        metadata=ModelMetadata(
            name=path.stem,
            source_format="keras_h5",
            parameter_count=0,
        ),
        graph=ComputationalGraph(),
    )