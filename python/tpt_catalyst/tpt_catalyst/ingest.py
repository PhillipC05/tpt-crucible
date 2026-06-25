"""Model ingestion — load PyTorch/ONNX/TensorFlow/GGUF models into TPT-IR."""

from pathlib import Path
from .ir import TptIr, OpNode, Edge, ModelMetadata, ComputationalGraph


def ingest_model(path: Path) -> TptIr:
    """Ingest a model file and return TPT-IR."""
    suffix = path.suffix.lower()
    if suffix in (".pt", ".pth", ".bin"):
        return _ingest_pytorch(path)
    elif suffix == ".onnx":
        return _ingest_onnx(path)
    elif suffix in (".pb", ".savedmodel", ""):
        return _ingest_tensorflow(path)
    elif suffix == ".gguf":
        from .gguf_ingest import ingest_gguf
        return ingest_gguf(path)
    else:
        raise ValueError(f"Unsupported model format: {suffix}")


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
