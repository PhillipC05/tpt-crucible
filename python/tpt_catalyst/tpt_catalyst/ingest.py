"""Model ingestion — auto-detect format from file extension + magic bytes, route to appropriate ingestor."""

from pathlib import Path
from .ir import TptIr, OpNode, Edge, ModelMetadata, ComputationalGraph


def detect_format(path: Path) -> str:
    """Auto-detect model format from file extension and magic bytes.

    Returns one of: pytorch, onnx, tensorflow, gguf, tflite, exl2, llamafile,
    keras_h5, jax_flax, awq_gptq, huggingface, safetensors.
    """
    suffix = path.suffix.lower()

    # Extension-based detection (fast path)
    if suffix in (".pt", ".pth", ".bin"):
        # Could be PyTorch or SafeTensors — check magic bytes
        if _check_magic(path, b"PK"):  # ZIP = safetensors
            return "safetensors"
        return "pytorch"
    elif suffix == ".onnx":
        return "onnx"
    elif suffix in (".pb", ".savedmodel"):
        return "tensorflow"
    elif suffix == ".gguf":
        return "gguf"
    elif suffix == ".tflite":
        return "tflite"
    elif suffix == ".exl2":
        return "exl2"
    elif suffix == ".llamafile":
        return "llamafile"
    elif suffix in (".h5", ".keras"):
        return "keras_h5"
    elif suffix == ".safetensors":
        return "safetensors"

    # Magic byte detection (slow path — for files without recognized extension)
    if path.is_file():
        # Check TFLite
        from .tflite_ingest import detect_tflite
        if detect_tflite(path):
            return "tflite"

        # Check EXL2
        from .exl2_ingest import detect_exl2
        if detect_exl2(path):
            return "exl2"

        # Check Llamafile
        from .llamafile_ingest import detect_llamafile
        if detect_llamafile(path):
            return "llamafile"

        # Check Keras HDF5
        from .keras_ingest import detect_keras_h5
        if detect_keras_h5(path):
            return "keras_h5"

        # Check GGUF
        if _check_magic(path, b"GGUF"):
            return "gguf"

        # Check SafeTensors (ZIP-based)
        if _check_magic(path, b"PK"):
            return "safetensors"

    # Directory-based detection
    if path.is_dir():
        # Check for JAX/Flax orbax checkpoint (before HF check since _metadata is specific)
        if (path / "_metadata").exists():
            return "jax_flax"

        # Check for HuggingFace model directory
        if (path / "config.json").exists():
            # Check for AWQ/GPTQ
            from .awq_gptq_ingest import detect_quantize_config
            if detect_quantize_config(path):
                return "awq_gptq"
            # Check for JAX/Flax
            from .jax_ingest import detect_jax_checkpoint, detect_jax_safetensors
            if detect_jax_checkpoint(path) or detect_jax_safetensors(path):
                return "jax_flax"
            return "huggingface"

        # Check for SafeTensors directory
        if list(path.glob("*.safetensors")):
            return "safetensors"

    # Fallback: try extension match
    if suffix:
        raise ValueError(f"Unsupported model format: {suffix}")

    raise ValueError(f"Cannot detect model format for: {path}")


def _check_magic(path: Path, magic: bytes) -> bool:
    """Check if file starts with given magic bytes."""
    try:
        with open(path, "rb") as f:
            header = f.read(len(magic))
            return header == magic
    except (OSError, IOError):
        return False


def ingest_model(path: Path) -> TptIr:
    """Ingest a model file and return TPT-IR.

    Auto-detects format from file extension + magic bytes.
    No --format flag required.
    """
    fmt = detect_format(path)

    dispatch = {
        "pytorch": _ingest_pytorch,
        "onnx": _ingest_onnx,
        "tensorflow": _ingest_tensorflow,
        "gguf": _ingest_gguf,
        "tflite": _ingest_tflite,
        "exl2": _ingest_exl2,
        "llamafile": _ingest_llamafile,
        "keras_h5": _ingest_keras_h5,
        "jax_flax": _ingest_jax_flax,
        "awq_gptq": _ingest_awq_gptq,
        "huggingface": _ingest_huggingface,
        "safetensors": _ingest_safetensors,
    }

    ingestor = dispatch.get(fmt)
    if ingestor is None:
        raise ValueError(f"No ingestor available for format: {fmt}")

    return ingestor(path)


def _ingest_pytorch(path: Path) -> TptIr:
    """Ingest a PyTorch JIT-traced/scripted model."""
    try:
        import torch
        model = torch.jit.load(str(path))
        graph = _extract_pytorch_graph(model)
        param_count = sum(p.numel() for p in model.parameters()) if hasattr(model, "parameters") else 0
        return TptIr(
            version="1.0.0",
            metadata=ModelMetadata(name=path.stem, source_format="pytorch", parameter_count=param_count),
            graph=graph,
        )
    except ImportError:
        return TptIr(
            version="1.0.0",
            metadata=ModelMetadata(name=path.stem, source_format="pytorch"),
            graph=ComputationalGraph(),
        )


def _extract_pytorch_graph(model) -> ComputationalGraph:
    """Extract computational graph from a TorchScript model."""
    nodes = []
    edges = []
    node_id = 0
    id_map = {}

    graph = model.graph
    for node in graph.nodes():
        kind = node.kind()
        op_name = kind.split("::")[-1] if "::" in kind else kind
        name = node.displayName() or op_name
        attrs = {}
        for key in node.attributeNames():
            try:
                attrs[key] = node[key]
            except Exception:
                pass

        nodes.append(OpNode(id=node_id, op_type=op_name, name=name, attributes=attrs))
        id_map[str(node)] = node_id
        node_id += 1

    for node in graph.nodes():
        from_id = id_map.get(str(node))
        if from_id is None:
            continue
        for output in node.outputs():
            for use in output.uses():
                to_id = id_map.get(str(use.user))
                if to_id is not None:
                    edges.append(Edge(from_id=from_id, to_id=to_id, tensor_name=output.debugName()))

    return ComputationalGraph(nodes=nodes, edges=edges)


def _ingest_onnx(path: Path) -> TptIr:
    """Ingest an ONNX model using the onnx protobuf parser."""
    try:
        import onnx
        model = onnx.load(str(path))
        graph = _extract_onnx_graph(model)
        param_count = sum(
            len(t.data) for t in model.graph.initializer
        ) if model.graph.initializer else 0
        return TptIr(
            version="1.0.0",
            metadata=ModelMetadata(name=model.graph.name or path.stem, source_format="onnx", parameter_count=param_count),
            graph=graph,
        )
    except ImportError:
        return TptIr(
            version="1.0.0",
            metadata=ModelMetadata(name=path.stem, source_format="onnx"),
            graph=ComputationalGraph(),
        )


def _extract_onnx_graph(model) -> ComputationalGraph:
    """Extract computational graph from an ONNX model."""
    nodes = []
    edges = []
    output_to_id = {}
    node_id = 0

    for onnx_node in model.graph.node:
        op_type = onnx_node.op_type
        name = onnx_node.name or f"{op_type}_{node_id}"
        attrs = {a.name: a for a in onnx_node.attribute}

        nodes.append(OpNode(id=node_id, op_type=op_type, name=name, attributes=attrs))

        for output_name in onnx_node.output:
            output_to_id[output_name] = node_id

        node_id += 1

    for onnx_node in model.graph.node:
        to_id = output_to_id.get(onnx_node.output[0] if onnx_node.output else "")
        if to_id is None:
            continue
        for input_name in onnx_node.input:
            from_id = output_to_id.get(input_name)
            if from_id is not None:
                edges.append(Edge(from_id=from_id, to_id=to_id, tensor_name=input_name))

    return ComputationalGraph(nodes=nodes, edges=edges)


def _ingest_tensorflow(path: Path) -> TptIr:
    """Ingest a TensorFlow SavedModel or frozen graph."""
    try:
        import tensorflow as tf
        return _ingest_tf_savedmodel(path)
    except ImportError:
        pass

    try:
        import tensorflow as tf
        return _ingest_tf_frozen_graph(path)
    except Exception:
        pass

    return TptIr(
        version="1.0.0",
        metadata=ModelMetadata(name=path.stem, source_format="tensorflow"),
        graph=ComputationalGraph(),
    )


def _ingest_tf_savedmodel(path: Path) -> TptIr:
    """Load a TF SavedModel and extract the graph."""
    import tensorflow as tf
    loaded = tf.saved_model.load(str(path))
    graph = ComputationalGraph()
    node_id = 0

    for name, func in loaded.signatures.items():
        for concrete_func in [func]:
            for node in concrete_func.graph.as_graph_def().node:
                op_type = node.op
                attrs = {}
                for key in node.attr:
                    attrs[key] = node.attr[key].SerializeToString().decode("latin-1")
                graph.nodes.append(OpNode(id=node_id, op_type=op_type, name=node.name, attributes=attrs))
                node_id += 1

    return TptIr(
        version="1.0.0",
        metadata=ModelMetadata(name=path.stem, source_format="tensorflow"),
        graph=graph,
    )


def _ingest_tf_frozen_graph(path: Path) -> TptIr:
    """Load a frozen TF graph (.pb file)."""
    import tensorflow as tf
    graph_def = tf.compat.v1.GraphDef()
    graph_def.ParseFromString(path.read_bytes())

    graph = ComputationalGraph()
    node_id = 0

    for node in graph_def.node:
        attrs = {}
        for key in node.attr:
            attrs[key] = node.attr[key].SerializeToString().decode("latin-1")
        graph.nodes.append(OpNode(id=node_id, op_type=node.op, name=node.name, attributes=attrs))
        node_id += 1

    for i, node in enumerate(graph_def.node):
        for input_name in node.input:
            clean_name = input_name.lstrip("^")
            for j, other in enumerate(graph_def.node):
                if other.name == clean_name:
                    graph.edges.append(Edge(from_id=j, to_id=i, tensor_name=input_name))
                    break

    return TptIr(
        version="1.0.0",
        metadata=ModelMetadata(name=path.stem, source_format="tensorflow"),
        graph=graph,
    )


def _ingest_gguf(path: Path) -> TptIr:
    """Ingest a GGUF model file."""
    from .gguf_ingest import ingest_gguf
    return ingest_gguf(path)


def _ingest_tflite(path: Path) -> TptIr:
    """Ingest a TFLite FlatBuffer model."""
    from .tflite_ingest import ingest_tflite
    return ingest_tflite(path)


def _ingest_exl2(path: Path) -> TptIr:
    """Ingest an EXL2 quantized model."""
    from .exl2_ingest import ingest_exl2
    return ingest_exl2(path)


def _ingest_llamafile(path: Path) -> TptIr:
    """Ingest a llamafile (ELF + GGUF)."""
    from .llamafile_ingest import ingest_llamafile
    return ingest_llamafile(path)


def _ingest_keras_h5(path: Path) -> TptIr:
    """Ingest a Keras HDF5 model."""
    from .keras_ingest import ingest_keras_h5
    return ingest_keras_h5(path)


def _ingest_jax_flax(path: Path) -> TptIr:
    """Ingest a JAX/Flax checkpoint."""
    from .jax_ingest import ingest_jax_flax
    return ingest_jax_flax(path)


def _ingest_awq_gptq(path: Path) -> TptIr:
    """Ingest an AWQ/GPTQ quantized model."""
    from .awq_gptq_ingest import ingest_awq_gptq
    return ingest_awq_gptq(path)


def _ingest_huggingface(path: Path) -> TptIr:
    """Ingest a HuggingFace model directory."""
    from .safetensors_ingest import HuggingFaceIngester
    ingester = HuggingFaceIngester()
    return ingester.ingest(path)


def _ingest_safetensors(path: Path) -> TptIr:
    """Ingest a SafeTensors model."""
    from .safetensors_ingest import SafeTensorsIngester
    ingester = SafeTensorsIngester()
    return ingester.ingest(path)