"use client";

import React, { useCallback, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  NodeProps,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
} from "reactflow";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type Severity = "pass" | "warn" | "fail";

export interface PreflightWarning {
  op_name: string;
  severity: Severity;
  message: string;
  suggestion?: string;
}

export interface IRNode {
  id: string;
  op: string;
  shape?: string;
  dtype?: string;
  hardware_target?: string;
}

export interface IREdge {
  id: string;
  source: string;
  target: string;
  tensor_name?: string;
  shape?: string;
  dtype?: string;
}

export interface IRGraphEditorProps {
  nodes: IRNode[];
  edges: IREdge[];
  preflight: PreflightWarning[];
  onNodeSwap?: (nodeId: string, newOp: string) => void;
  onQuantInsert?: (afterNodeId: string) => void;
  onExport?: () => void;
}

// ---------------------------------------------------------------------------
// Severity helpers
// ---------------------------------------------------------------------------

const SEVERITY_RING: Record<Severity, string> = {
  pass: "ring-emerald-400",
  warn: "ring-amber-400",
  fail: "ring-rose-500",
};

const SEVERITY_BADGE_BG: Record<Severity, string> = {
  pass: "bg-emerald-500",
  warn: "bg-amber-400",
  fail: "bg-rose-500",
};

const SEVERITY_LABEL: Record<Severity, string> = {
  pass: "OK",
  warn: "WARN",
  fail: "FAIL",
};

// ---------------------------------------------------------------------------
// Custom node renderer
// ---------------------------------------------------------------------------

interface IRNodeData {
  label: string;
  op: string;
  shape?: string;
  dtype?: string;
  hardware_target?: string;
  severity?: Severity;
  warning?: PreflightWarning;
  onSwap?: (newOp: string) => void;
  onQuantInsert?: () => void;
}

function IRGraphNode({ data }: NodeProps<IRNodeData>) {
  const sev = data.severity;
  const ringClass = sev ? SEVERITY_RING[sev] : "ring-zinc-600";
  const [menuOpen, setMenuOpen] = React.useState(false);

  return (
    <div
      className={`relative min-w-[140px] rounded border border-zinc-600 bg-zinc-800 p-2 text-xs ring-1 ${ringClass} cursor-pointer select-none`}
      onContextMenu={(e) => {
        e.preventDefault();
        setMenuOpen((v) => !v);
      }}
    >
      <Handle type="target" position={Position.Top} className="!bg-cyan-400" />

      {/* op name */}
      <p className="font-mono font-semibold text-cyan-300">{data.op}</p>

      {/* shape / dtype */}
      {data.shape && (
        <p className="mt-0.5 text-zinc-400">{data.shape}</p>
      )}
      {data.dtype && (
        <span className="mt-0.5 inline-block rounded bg-zinc-700 px-1 font-mono text-amber-300">
          {data.dtype}
        </span>
      )}

      {/* hardware target badge */}
      {data.hardware_target && (
        <span className="mt-1 block text-zinc-500">{data.hardware_target}</span>
      )}

      {/* pre-flight badge — shown inline on the node */}
      {sev && (
        <span
          className={`absolute -right-2 -top-2 rounded-full px-1.5 py-0.5 text-[10px] font-bold text-zinc-900 ${SEVERITY_BADGE_BG[sev]}`}
          title={data.warning?.message}
        >
          {SEVERITY_LABEL[sev]}
        </span>
      )}

      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-cyan-400"
      />

      {/* right-click context menu */}
      {menuOpen && (
        <div
          className="absolute left-full top-0 z-50 ml-1 min-w-[160px] rounded border border-zinc-600 bg-zinc-900 py-1 shadow-xl"
          onMouseLeave={() => setMenuOpen(false)}
        >
          {data.warning?.suggestion && (
            <button
              className="block w-full px-3 py-1 text-left text-amber-300 hover:bg-zinc-700"
              onClick={() => {
                data.onSwap?.(data.warning!.suggestion!);
                setMenuOpen(false);
              }}
            >
              ↔ Apply fix: {data.warning.suggestion}
            </button>
          )}
          <button
            className="block w-full px-3 py-1 text-left text-zinc-300 hover:bg-zinc-700"
            onClick={() => {
              data.onQuantInsert?.();
              setMenuOpen(false);
            }}
          >
            + Insert quantization pass
          </button>
        </div>
      )}
    </div>
  );
}

const NODE_TYPES = { irNode: IRGraphNode };

// ---------------------------------------------------------------------------
// Main editor
// ---------------------------------------------------------------------------

export default function IRGraphEditor({
  nodes: irNodes,
  edges: irEdges,
  preflight,
  onNodeSwap,
  onQuantInsert,
  onExport,
}: IRGraphEditorProps) {
  // Build a lookup: op_name → worst severity warning
  const warningMap = useMemo(() => {
    const map = new Map<string, PreflightWarning>();
    // fail > warn > pass priority
    const rank: Record<Severity, number> = { fail: 2, warn: 1, pass: 0 };
    for (const w of preflight) {
      const existing = map.get(w.op_name);
      if (!existing || rank[w.severity] > rank[existing.severity]) {
        map.set(w.op_name, w);
      }
    }
    return map;
  }, [preflight]);

  // Convert IR nodes → React Flow nodes
  const initialNodes: Node<IRNodeData>[] = useMemo(
    () =>
      irNodes.map((n, idx) => {
        const warning = warningMap.get(n.op);
        return {
          id: n.id,
          type: "irNode",
          position: { x: 200, y: idx * 110 },
          data: {
            label: n.op,
            op: n.op,
            shape: n.shape,
            dtype: n.dtype,
            hardware_target: n.hardware_target,
            severity: warning?.severity,
            warning,
            onSwap: onNodeSwap
              ? (newOp: string) => onNodeSwap(n.id, newOp)
              : undefined,
            onQuantInsert: onQuantInsert
              ? () => onQuantInsert(n.id)
              : undefined,
          },
        };
      }),
    [irNodes, warningMap, onNodeSwap, onQuantInsert],
  );

  // Convert IR edges → React Flow edges
  const initialEdges: Edge[] = useMemo(
    () =>
      irEdges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.shape ?? e.tensor_name,
        style: { stroke: "#22d3ee", strokeWidth: 1.5 },
        labelStyle: { fill: "#a1a1aa", fontSize: 10 },
      })),
    [irEdges],
  );

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  // Severity summary counts
  const summary = useMemo(() => {
    const counts = { pass: 0, warn: 0, fail: 0 };
    for (const w of preflight) counts[w.severity]++;
    return counts;
  }, [preflight]);

  return (
    <div className="flex h-full flex-col bg-zinc-900 font-mono text-zinc-100">
      {/* Toolbar */}
      <div className="flex items-center gap-3 border-b border-zinc-700 px-4 py-2 text-xs">
        <span className="text-zinc-400">TPT-IR Graph</span>
        <span className="ml-auto flex gap-2">
          {summary.fail > 0 && (
            <span className="rounded bg-rose-600 px-2 py-0.5 font-bold text-white">
              {summary.fail} FAIL
            </span>
          )}
          {summary.warn > 0 && (
            <span className="rounded bg-amber-500 px-2 py-0.5 font-bold text-zinc-900">
              {summary.warn} WARN
            </span>
          )}
          {summary.pass > 0 && (
            <span className="rounded bg-emerald-600 px-2 py-0.5 font-bold text-white">
              {summary.pass} OK
            </span>
          )}
        </span>
        {onExport && (
          <button
            onClick={onExport}
            className="rounded border border-cyan-600 px-2 py-0.5 text-cyan-400 hover:bg-cyan-900"
          >
            Export .tptir
          </button>
        )}
      </div>

      {/* React Flow canvas */}
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={NODE_TYPES}
          fitView
          className="bg-zinc-900"
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#3f3f46" gap={24} />
          <Controls className="fill-zinc-400 stroke-zinc-400" />
          <MiniMap
            nodeColor={(n) => {
              const sev = (n.data as IRNodeData).severity;
              if (sev === "fail") return "#f43f5e";
              if (sev === "warn") return "#f59e0b";
              return "#22d3ee";
            }}
            maskColor="rgba(24,24,27,0.8)"
          />
        </ReactFlow>
      </div>

      {/* Pre-flight warning list below canvas */}
      {preflight.length > 0 && (
        <div className="max-h-40 overflow-y-auto border-t border-zinc-700 px-4 py-2">
          <p className="mb-1 text-xs text-zinc-500">Pre-flight warnings</p>
          {preflight.map((w, i) => (
            <div key={i} className="mb-1 flex items-start gap-2 text-xs">
              <span
                className={`mt-0.5 shrink-0 rounded px-1 py-0.5 font-bold ${SEVERITY_BADGE_BG[w.severity]} text-zinc-900`}
              >
                {SEVERITY_LABEL[w.severity]}
              </span>
              <span className="text-zinc-300">
                <span className="text-cyan-400">{w.op_name}</span>
                {" — "}
                {w.message}
                {w.suggestion && (
                  <span className="text-amber-400"> → {w.suggestion}</span>
                )}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
