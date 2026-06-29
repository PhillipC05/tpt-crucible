"use client";

import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  MarkerType,
} from "@xyflow/react";
import { useCallback, useMemo, useState } from "react";

interface IrNode {
  id: string;
  op_type: string;
  name: string;
  severity?: "pass" | "warn" | "fail";
  target?: string;
  quant_bits?: number;
}

interface IrEdge {
  from: string;
  to: string;
  tensor_name: string;
}

const opColors: Record<string, string> = {
  matmul: "#00e5ff",
  relu: "#3fb950",
  gelu: "#3fb950",
  softmax: "#ffab00",
  attention: "#f85149",
  conv2d: "#00e5ff",
  add: "#8b949e",
  layernorm: "#3fb950",
  embedding: "#00e5ff",
  fused_matmul_relu: "#00e5ff",
  fused_matmul_gelu: "#00e5ff",
};

const severityColors: Record<string, string> = {
  pass: "#3fb950",
  warn: "#ffab00",
  fail: "#f85149",
};

function IrNodeComponent({ data }: { data: any }) {
  const color = opColors[data.op_type] || "#8b949e";
  const severityColor = data.severity ? severityColors[data.severity] : null;

  return (
    <div
      className={`relative px-4 py-3 rounded-lg border-2 min-w-[120px] ${
        severityColor ? "glow-cyan" : ""
      }`}
      style={{
        background: "#161b22",
        borderColor: color,
      }}
    >
      <Handle type="target" position={Position.Top} className="!bg-accent-cyan !w-2 !h-2" />
      <div className="text-center">
        <div className="text-[10px] uppercase tracking-wider" style={{ color }}>
          {data.op_type}
        </div>
        <div className="text-xs text-text-primary mt-0.5 font-mono">{data.name}</div>
        {data.target && (
          <div className="text-[10px] mt-1 px-1.5 py-0.5 rounded bg-bg-tertiary text-text-secondary">
            {data.target.toUpperCase()}
          </div>
        )}
        {data.quant_bits && (
          <div className="text-[10px] mt-1 text-accent-amber">
            {data.quant_bits}-bit
          </div>
        )}
        {severityColor && (
          <div
            className="absolute -top-1 -right-1 w-3 h-3 rounded-full border border-bg-primary"
            style={{ background: severityColor }}
          />
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-accent-cyan !w-2 !h-2" />
    </div>
  );
}

const nodeTypes = { irNode: IrNodeComponent };

const sampleIr: IrNode[] = [
  { id: "0", op_type: "embedding", name: "token_embed", severity: "pass", target: "fpga" },
  { id: "1", op_type: "layernorm", name: "norm_0", severity: "pass" },
  { id: "2", op_type: "matmul", name: "q_proj", severity: "pass", target: "fpga", quant_bits: 8 },
  { id: "3", op_type: "matmul", name: "k_proj", severity: "pass", target: "fpga", quant_bits: 8 },
  { id: "4", op_type: "matmul", name: "v_proj", severity: "pass", target: "fpga", quant_bits: 8 },
  { id: "5", op_type: "attention", name: "self_attn", severity: "warn", target: "swarm" },
  { id: "6", op_type: "matmul", name: "out_proj", severity: "pass", target: "fpga", quant_bits: 8 },
  { id: "7", op_type: "add", name: "residual_0", severity: "pass" },
  { id: "8", op_type: "layernorm", name: "norm_1", severity: "pass" },
  { id: "9", op_type: "matmul", name: "fc1", severity: "pass", target: "fpga", quant_bits: 4 },
  { id: "10", op_type: "gelu", name: "act_0", severity: "pass", target: "analog" },
  { id: "11", op_type: "matmul", name: "fc2", severity: "pass", target: "fpga", quant_bits: 4 },
  { id: "12", op_type: "add", name: "residual_1", severity: "pass" },
];

const sampleEdges: IrEdge[] = [
  { from: "0", to: "1", tensor_name: "tokens" },
  { from: "1", to: "2", tensor_name: "normed" },
  { from: "1", to: "3", tensor_name: "normed" },
  { from: "1", to: "4", tensor_name: "normed" },
  { from: "2", to: "5", tensor_name: "q" },
  { from: "3", to: "5", tensor_name: "k" },
  { from: "4", to: "5", tensor_name: "v" },
  { from: "5", to: "6", tensor_name: "attn_out" },
  { from: "0", to: "7", tensor_name: "tokens" },
  { from: "6", to: "7", tensor_name: "attn_out" },
  { from: "7", to: "8", tensor_name: "residual" },
  { from: "8", to: "9", tensor_name: "normed" },
  { from: "9", to: "10", tensor_name: "fc1_out" },
  { from: "10", to: "11", tensor_name: "act_out" },
  { from: "7", to: "12", tensor_name: "residual" },
  { from: "11", to: "12", tensor_name: "fc2_out" },
];

export function IrGraphEditor({
  onNodeSelect,
}: {
  onNodeSelect?: (node: IrNode | null) => void;
}) {
  const [selectedNode, setSelectedNode] = useState<IrNode | null>(null);
  const [showContextMenu, setShowContextMenu] = useState(false);
  const [contextMenuPos, setContextMenuPos] = useState({ x: 0, y: 0 });
  const [showQuantDialog, setShowQuantDialog] = useState(false);
  const [quantBits, setQuantBits] = useState(8);

  const substitutionMap: Record<string, string[]> = {
    attention: ["mha", "flash_attention"],
    softmax: ["approx_softmax", "lookup_softmax"],
    gelu: ["sigmoid_gelu", "polynomial_gelu"],
    layernorm: ["rmsnorm", "batchnorm"],
  };

  const { initialNodes, initialEdges } = useMemo(() => {
    const nodeWidth = 160;
    const nodeHeight = 80;
    const cols = 3;
    const spacingX = 200;
    const spacingY = 120;

    const nodes: Node[] = sampleIr.map((irNode, i) => ({
      id: irNode.id,
      type: "irNode",
      position: {
        x: (i % cols) * spacingX,
        y: Math.floor(i / cols) * spacingY,
      },
      data: irNode as unknown as Record<string, unknown>,
    }));

    const edges: Edge[] = sampleEdges.map((e, i) => ({
      id: `e${i}`,
      source: e.from,
      target: e.to,
      label: e.tensor_name,
      labelStyle: { fill: "#8b949e", fontSize: 9, fontWeight: "normal" },
      labelBgStyle: { fill: "#0d1117", fillOpacity: 0.8 },
      labelBgPadding: [4, 2] as [number, number],
      animated: true,
      style: { stroke: "#30363d", strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#30363d" },
    }));

    return { initialNodes: nodes, initialEdges: edges };
  }, []);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onNodeClick = useCallback(
    (_: any, node: Node) => {
      const irNode = sampleIr.find((n) => n.id === node.id) || null;
      setSelectedNode(irNode);
      onNodeSelect?.(irNode);
    },
    [onNodeSelect]
  );

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
    onNodeSelect?.(null);
  }, [onNodeSelect]);

  return (
    <div className="relative h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
        className="bg-bg-primary"
      >
        <Background color="#30363d" gap={20} />
        <Controls className="!bg-bg-secondary !border-border !rounded-lg" />
        <MiniMap
          nodeColor={(n) => opColors[n.data?.op_type as string] || "#8b949e"}
          className="!bg-bg-secondary !border-border !rounded-lg"
          maskColor="rgba(0,0,0,0.5)"
        />
      </ReactFlow>

      {selectedNode && (
        <div className="absolute top-4 right-4 z-10 stat-card w-56">
          <h4 className="text-xs font-bold text-accent-cyan mb-2">SELECTED NODE</h4>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-text-secondary">Type</span>
              <span style={{ color: opColors[selectedNode.op_type] || "#8b949e" }}>
                {selectedNode.op_type}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Name</span>
              <span>{selectedNode.name}</span>
            </div>
            {selectedNode.target && (
              <div className="flex justify-between">
                <span className="text-text-secondary">Target</span>
                <span className="text-accent-cyan">{selectedNode.target}</span>
              </div>
            )}
            {selectedNode.quant_bits && (
              <div className="flex justify-between">
                <span className="text-text-secondary">Quant</span>
                <span className="text-accent-amber">{selectedNode.quant_bits}-bit</span>
              </div>
            )}
            {selectedNode.severity && (
              <div className="flex justify-between">
                <span className="text-text-secondary">Status</span>
                <span className={selectedNode.severity === "pass" ? "text-accent-green" : selectedNode.severity === "warn" ? "text-accent-amber" : "text-accent-red"}>
                  {selectedNode.severity.toUpperCase()}
                </span>
              </div>
            )}
            <div className="pt-2 border-t border-border space-y-1">
              {substitutionMap[selectedNode.op_type] && (
                <div>
                  <div className="text-text-secondary mb-1">Substitutions:</div>
                  {substitutionMap[selectedNode.op_type].map((sub) => (
                    <button
                      key={sub}
                      className="w-full text-left px-2 py-1 rounded bg-bg-tertiary hover:bg-accent-cyan/20 text-[10px] hover:text-accent-cyan"
                      onClick={() => {
                        setNodes((nds) =>
                          nds.map((n) =>
                            n.id === selectedNode.id
                              ? { ...n, data: { ...n.data, op_type: sub } }
                              : n
                          )
                        );
                      }}
                    >
                      {sub}
                    </button>
                  ))}
                </div>
              )}
              <button
                className="w-full text-left px-2 py-1 rounded bg-bg-tertiary hover:bg-accent-amber/20 text-[10px] hover:text-accent-amber"
                onClick={() => setShowQuantDialog(true)}
              >
                Set quantization
              </button>
            </div>
          </div>
        </div>
      )}

      {showQuantDialog && selectedNode && (
        <div className="absolute top-4 right-64 z-20 stat-card w-48">
          <h4 className="text-xs font-bold text-accent-amber mb-2">QUANTIZATION</h4>
          <div className="space-y-2">
            <div className="flex gap-1">
              {[4, 8, 16, 32].map((bits) => (
                <button
                  key={bits}
                  onClick={() => {
                    setQuantBits(bits);
                    setNodes((nds) =>
                      nds.map((n) =>
                        n.id === selectedNode.id
                          ? { ...n, data: { ...n.data, quant_bits: bits } }
                          : n
                      )
                    );
                    setShowQuantDialog(false);
                  }}
                  className={`px-2 py-1 rounded text-[10px] ${
                    quantBits === bits
                      ? "bg-accent-cyan/20 text-accent-cyan border border-accent-cyan/50"
                      : "bg-bg-tertiary text-text-secondary border border-border"
                  }`}
                >
                  {bits}-bit
                </button>
              ))}
            </div>
            <button
              onClick={() => setShowQuantDialog(false)}
              className="w-full px-2 py-1 rounded bg-bg-tertiary text-text-secondary text-[10px]"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="absolute bottom-4 left-4 z-10 stat-card text-xs">
        <div className="flex gap-3">
          <span>{sampleIr.length} nodes</span>
          <span>{sampleEdges.length} edges</span>
        </div>
      </div>
    </div>
  );
}
