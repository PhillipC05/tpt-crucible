"use client";

import React, { useEffect, useState } from "react";

// ---------------------------------------------------------------------------
// Types (mirror schema.go NodeHeartbeatStatus)
// ---------------------------------------------------------------------------

export type NodeStatus = "green" | "amber" | "red";

export interface NodeHeartbeatStatus {
  node_id: string;
  status: NodeStatus;
  last_seen: string;       // ISO timestamp
  missed_beats: number;
  assigned_layers: number[];
  latency_ms: number;
}

export interface SwarmHeatmap {
  timestamp: string;
  nodes: NodeHeartbeatStatus[];
  online: number;
  degraded: number;
  dead: number;
}

export interface NodeHeatmapProps {
  wsUrl: string;          // WebSocket URL that streams SwarmHeatmap JSON
  cols?: number;          // grid columns, default 4
}

// ---------------------------------------------------------------------------
// Status helpers
// ---------------------------------------------------------------------------

const STATUS_BG: Record<NodeStatus, string> = {
  green: "bg-emerald-700 ring-emerald-400",
  amber: "bg-amber-600 ring-amber-300",
  red:   "bg-rose-700 ring-rose-400",
};

const STATUS_LABEL: Record<NodeStatus, string> = {
  green: "Online",
  amber: "Degraded",
  red:   "Dead",
};

const STATUS_DOT: Record<NodeStatus, string> = {
  green: "bg-emerald-300",
  amber: "bg-amber-300",
  red:   "bg-rose-400 animate-pulse",
};

// ---------------------------------------------------------------------------
// Individual node card
// ---------------------------------------------------------------------------

function NodeCard({ node }: { node: NodeHeartbeatStatus }) {
  const ring = STATUS_BG[node.status];
  return (
    <div
      className={`relative flex flex-col rounded border border-zinc-700 p-2 text-[10px] font-mono ring-1 transition-colors ${ring}`}
      title={`Node ${node.node_id} — ${STATUS_LABEL[node.status]}\nMissed beats: ${node.missed_beats}\nLatency: ${node.latency_ms.toFixed(1)} ms\nLayers: ${node.assigned_layers.join(", ") || "none"}`}
    >
      {/* Status dot */}
      <span
        className={`absolute right-1.5 top-1.5 h-2 w-2 rounded-full ${STATUS_DOT[node.status]}`}
      />

      {/* Node ID */}
      <span className="font-bold text-zinc-100">N{node.node_id}</span>

      {/* Layer count */}
      <span className="mt-0.5 text-zinc-300">
        {node.assigned_layers.length} layer{node.assigned_layers.length !== 1 ? "s" : ""}
      </span>

      {/* Latency */}
      <span className={node.latency_ms > 50 ? "text-amber-300" : "text-zinc-400"}>
        {node.latency_ms.toFixed(0)} ms
      </span>

      {/* Missed beats badge */}
      {node.missed_beats > 0 && (
        <span className="mt-0.5 rounded bg-rose-900 px-1 text-rose-300">
          ×{node.missed_beats}
        </span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main heatmap component
// ---------------------------------------------------------------------------

export default function NodeHeatmap({ wsUrl, cols = 4 }: NodeHeatmapProps) {
  const [heatmap, setHeatmap] = useState<SwarmHeatmap | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string>("");

  useEffect(() => {
    let ws: WebSocket;
    let retryTimeout: ReturnType<typeof setTimeout>;

    const connect = () => {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => setConnected(true);

      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data as string);
          // Accept both a bare SwarmHeatmap and a wrapped TelemetryMessage
          const payload: SwarmHeatmap =
            msg.type === "swarm_heatmap" ? msg.payload : msg;
          setHeatmap(payload);
          setLastUpdate(new Date().toLocaleTimeString());
        } catch {
          // ignore malformed frames
        }
      };

      ws.onclose = () => {
        setConnected(false);
        retryTimeout = setTimeout(connect, 3000);
      };

      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      ws?.close();
      clearTimeout(retryTimeout);
    };
  }, [wsUrl]);

  const nodes = heatmap?.nodes ?? [];

  return (
    <div className="flex flex-col gap-3 rounded border border-zinc-700 bg-zinc-900 p-4 font-mono">
      {/* Header */}
      <div className="flex items-center justify-between text-xs">
        <h2 className="font-semibold tracking-widest text-cyan-400 uppercase">
          Swarm Node Status
        </h2>
        <div className="flex items-center gap-2 text-zinc-500">
          <span
            className={`h-2 w-2 rounded-full ${connected ? "bg-emerald-400" : "bg-zinc-600"}`}
          />
          {connected ? "Live" : "Reconnecting…"}
          {lastUpdate && <span className="ml-1">{lastUpdate}</span>}
        </div>
      </div>

      {/* Summary bar */}
      {heatmap && (
        <div className="flex gap-3 text-xs">
          <span className="text-emerald-400">● {heatmap.online} online</span>
          <span className="text-amber-400">◐ {heatmap.degraded} degraded</span>
          <span className="text-rose-400">✕ {heatmap.dead} dead</span>
          <span className="ml-auto text-zinc-600">
            health{" "}
            <span className="text-zinc-300">
              {nodes.length > 0
                ? Math.round((heatmap.online / nodes.length) * 100)
                : 0}
              %
            </span>
          </span>
        </div>
      )}

      {/* Node grid */}
      {nodes.length === 0 ? (
        <p className="text-xs text-zinc-600">
          {connected ? "Waiting for telemetry…" : "Not connected"}
        </p>
      ) : (
        <div
          className="grid gap-2"
          style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
        >
          {nodes.map((node) => (
            <NodeCard key={node.node_id} node={node} />
          ))}
        </div>
      )}

      {/* Legend */}
      <div className="flex gap-3 text-[10px] text-zinc-500">
        {(["green", "amber", "red"] as NodeStatus[]).map((s) => (
          <span key={s} className="flex items-center gap-1">
            <span className={`h-2 w-2 rounded-full ${STATUS_DOT[s]}`} />
            {STATUS_LABEL[s]}
          </span>
        ))}
      </div>
    </div>
  );
}
