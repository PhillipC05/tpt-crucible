"use client";

import { createContext, useContext, useEffect, useRef, useState, ReactNode } from "react";

export interface ChartPoint {
  time: string;
  value: number;
}

export interface LatencyNode {
  id: string;
  latency: number;
  status: "online" | "busy" | "offline";
}

export interface DiagnosticNode {
  node_id: string;
  status: "green" | "amber" | "red";
  latency_ms: number;
  assigned_layers: number[];
}

export interface PipelineStage {
  name: string;
  duration: number;
  status: "done" | "running" | "pending";
}

export interface OtaNodeStatus {
  node_id: string;
  status: "pending" | "flashing" | "done" | "failed";
  progress: number;
}

interface TelemetryState {
  connected: boolean;
  tpsData: ChartPoint[];
  bandwidthData: ChartPoint[];
  thermalData: ChartPoint[];
  latencyNodes: LatencyNode[];
  diagnosticNodes: DiagnosticNode[];
  pipelineStages: PipelineStage[];
  otaNodes: OtaNodeStatus[];
}

interface TelemetryContextValue extends TelemetryState {
  reconnect: () => void;
}

export const TelemetryContext = createContext<TelemetryContextValue | null>(null);

const MAX_POINTS = 60;

function toTimeLabel(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}

function append(arr: ChartPoint[], point: ChartPoint): ChartPoint[] {
  const next = [...arr, point];
  return next.length > MAX_POINTS ? next.slice(next.length - MAX_POINTS) : next;
}

export function TelemetryProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<TelemetryState>({
    connected: false,
    tpsData: [],
    bandwidthData: [],
    thermalData: [],
    latencyNodes: [],
    diagnosticNodes: [],
    pipelineStages: [],
    otaNodes: [],
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function connect() {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8080/ws";
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setState((s) => ({ ...s, connected: true }));

    ws.onclose = () => {
      setState((s) => ({ ...s, connected: false }));
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      setState((s) => ({ ...s, connected: false }));
    };

    ws.onmessage = (event) => {
      let msg: { type: string; payload: unknown };
      try {
        msg = JSON.parse(event.data as string);
      } catch {
        return;
      }

      setState((s) => {
        switch (msg.type) {
          case "tps": {
            const p = msg.payload as { timestamp: string; tps: number };
            return { ...s, tpsData: append(s.tpsData, { time: toTimeLabel(p.timestamp), value: p.tps }) };
          }
          case "bandwidth": {
            const p = msg.payload as { timestamp: string; bandwidth_gbs: number };
            return { ...s, bandwidthData: append(s.bandwidthData, { time: toTimeLabel(p.timestamp), value: p.bandwidth_gbs }) };
          }
          case "thermal": {
            const p = msg.payload as { timestamp: string; drift_pct: number };
            return { ...s, thermalData: append(s.thermalData, { time: toTimeLabel(p.timestamp), value: p.drift_pct }) };
          }
          case "node_latency": {
            const p = msg.payload as { node_id: string; latency_ms: number };
            const updated = s.latencyNodes.filter((n) => n.id !== p.node_id);
            return {
              ...s,
              latencyNodes: [
                ...updated,
                { id: p.node_id, latency: p.latency_ms, status: "online" },
              ],
            };
          }
          case "diagnostics": {
            const nodes = msg.payload as DiagnosticNode[];
            return { ...s, diagnosticNodes: nodes };
          }
          case "pipeline_event": {
            const stages = msg.payload as PipelineStage[];
            return { ...s, pipelineStages: stages };
          }
          case "ota_progress": {
            const nodes = msg.payload as OtaNodeStatus[];
            return { ...s, otaNodes: nodes };
          }
          case "swarm_heatmap": {
            const hm = msg.payload as { nodes: { node_id: string; status: string; latency_ms: number; assigned_layers: number[] }[] };
            const latencyNodes = hm.nodes.map((n) => ({
              id: n.node_id,
              latency: n.latency_ms,
              status: n.status === "green" ? "online" : n.status === "amber" ? "busy" : "offline",
            } as LatencyNode));
            const diagnosticNodes = hm.nodes.map((n) => ({
              node_id: n.node_id,
              status: n.status as "green" | "amber" | "red",
              latency_ms: n.latency_ms,
              assigned_layers: n.assigned_layers,
            }));
            return { ...s, latencyNodes, diagnosticNodes };
          }
          default:
            return s;
        }
      });
    };
  }

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, []);

  function reconnect() {
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    wsRef.current?.close();
    connect();
  }

  return (
    <TelemetryContext.Provider value={{ ...state, reconnect }}>
      {children}
    </TelemetryContext.Provider>
  );
}

export function useTelemetry(): TelemetryContextValue {
  const ctx = useContext(TelemetryContext);
  if (!ctx) throw new Error("useTelemetry must be used inside TelemetryProvider");
  return ctx;
}
