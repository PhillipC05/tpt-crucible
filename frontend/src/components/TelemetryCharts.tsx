"use client";

import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Legend,
} from "recharts";
import { useMemo } from "react";

function generateTimeSeries(points: number, baseValue: number, variance: number) {
  const now = Date.now();
  return Array.from({ length: points }, (_, i) => ({
    time: new Date(now - (points - i) * 1000).toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    value: Math.max(0, baseValue + (Math.random() - 0.5) * variance),
  }));
}

export function TokensPerSecondChart({ data }: { data?: { time: string; value: number }[] }) {
  const chartData = data || useMemo(() => generateTimeSeries(30, 120, 40), []);

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">TOKENS / SECOND</h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="tpsGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#00e5ff" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#00e5ff" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
          <XAxis dataKey="time" tick={{ fill: "#8b949e", fontSize: 10 }} interval={4} />
          <YAxis tick={{ fill: "#8b949e", fontSize: 10 }} />
          <Tooltip
            contentStyle={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 4, fontSize: 12 }}
            labelStyle={{ color: "#c9d1d9" }}
          />
          <Area type="monotone" dataKey="value" stroke="#00e5ff" fill="url(#tpsGradient)" strokeWidth={2} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function MemoryBandwidthChart({ data }: { data?: { time: string; value: number }[] }) {
  const chartData = data || useMemo(() => generateTimeSeries(30, 412, 60), []);

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-amber mb-3">MEMORY BANDWIDTH (GB/s)</h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="bwGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ffab00" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#ffab00" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
          <XAxis dataKey="time" tick={{ fill: "#8b949e", fontSize: 10 }} interval={4} />
          <YAxis tick={{ fill: "#8b949e", fontSize: 10 }} />
          <Tooltip
            contentStyle={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 4, fontSize: 12 }}
            labelStyle={{ color: "#c9d1d9" }}
          />
          <Area type="monotone" dataKey="value" stroke="#ffab00" fill="url(#bwGradient)" strokeWidth={2} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ThermalDriftChart({ data }: { data?: { time: string; value: number }[] }) {
  const chartData = data || useMemo(() => generateTimeSeries(30, 0.12, 0.08), []);

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-green mb-3">THERMAL DRIFT (%)</h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
          <XAxis dataKey="time" tick={{ fill: "#8b949e", fontSize: 10 }} interval={4} />
          <YAxis tick={{ fill: "#8b949e", fontSize: 10 }} domain={[0, 0.5]} />
          <Tooltip
            contentStyle={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 4, fontSize: 12 }}
            labelStyle={{ color: "#c9d1d9" }}
          />
          <Line type="monotone" dataKey="value" stroke="#3fb950" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

interface LatencyNode {
  id: string;
  latency: number;
  status: "online" | "busy" | "offline";
}

export function LatencyHeatmap({ nodes }: { nodes?: LatencyNode[] }) {
  const nodeData = nodes || useMemo(() =>
    Array.from({ length: 16 }, (_, i) => ({
      id: `N${i}`,
      latency: 1 + Math.random() * 4,
      status: Math.random() > 0.1 ? "online" : Math.random() > 0.5 ? "busy" : "offline",
    } as LatencyNode)),
  []);

  const maxLatency = Math.max(...nodeData.map((n) => n.latency));

  function getHeatColor(latency: number): string {
    const ratio = latency / maxLatency;
    if (ratio < 0.33) return "bg-accent-green/60";
    if (ratio < 0.66) return "bg-accent-amber/60";
    return "bg-accent-red/60";
  }

  function getStatusBorder(status: string): string {
    if (status === "online") return "border-accent-green/50";
    if (status === "busy") return "border-accent-amber/50";
    return "border-accent-red/50";
  }

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">NODE LATENCY HEATMAP</h3>
      <div className="grid grid-cols-4 gap-2">
        {nodeData.map((node) => (
          <div
            key={node.id}
            className={`aspect-square rounded border ${getStatusBorder(node.status)} ${getHeatColor(node.latency)} flex flex-col items-center justify-center text-xs transition-all hover:scale-105`}
          >
            <span className="font-bold text-white">{node.id}</span>
            <span className="text-[10px] text-white/80">{node.latency.toFixed(1)}ms</span>
          </div>
        ))}
      </div>
      <div className="flex justify-between mt-3 text-[10px] text-text-secondary">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-accent-green/60" />
          <span>Low (&lt;{(maxLatency * 0.33).toFixed(1)}ms)</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-accent-amber/60" />
          <span>Medium</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-accent-red/60" />
          <span>High (&gt;{(maxLatency * 0.66).toFixed(1)}ms)</span>
        </div>
      </div>
    </div>
  );
}

export function PowerChart({ data }: { data?: { name: string; idle: number; active: number; peak: number }[] }) {
  const chartData = data || [
    { name: "ESP32 x16", idle: 0.8, active: 3.2, peak: 8.0 },
    { name: "Alveo U280", idle: 50, active: 75, peak: 225 },
    { name: "Analog 4L", idle: 0.1, active: 0.5, peak: 1.2 },
  ];

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-amber mb-3">POWER CONSUMPTION</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
          <XAxis dataKey="name" tick={{ fill: "#8b949e", fontSize: 10 }} />
          <YAxis tick={{ fill: "#8b949e", fontSize: 10 }} />
          <Tooltip
            contentStyle={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 4, fontSize: 12 }}
            labelStyle={{ color: "#c9d1d9" }}
          />
          <Legend wrapperStyle={{ fontSize: 10, color: "#8b949e" }} />
          <Bar dataKey="idle" fill="#3fb950" name="Idle (mW)" />
          <Bar dataKey="active" fill="#ffab00" name="Active (mW)" />
          <Bar dataKey="peak" fill="#f85149" name="Peak (mW)" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function CompilationTimeline({ stages }: { stages?: { name: string; duration: number; status: "done" | "running" | "pending" }[] }) {
  const stageData = stages || [
    { name: "Ingest", duration: 2.1, status: "done" },
    { name: "Optimize", duration: 1.5, status: "done" },
    { name: "Partition", duration: 0.8, status: "done" },
    { name: "Compile", duration: 45.2, status: "running" },
    { name: "Validate", duration: 0, status: "pending" },
  ];

  const totalDuration = stageData.reduce((sum, s) => sum + s.duration, 0);

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">COMPILATION TIMELINE</h3>
      <div className="space-y-2">
        {stageData.map((stage) => {
          const pct = totalDuration > 0 ? (stage.duration / totalDuration) * 100 : 0;
          const barColor = stage.status === "done" ? "bg-accent-green" : stage.status === "running" ? "bg-accent-cyan animate-pulse" : "bg-bg-tertiary";
          const textColor = stage.status === "done" ? "text-accent-green" : stage.status === "running" ? "text-accent-cyan" : "text-text-secondary";

          return (
            <div key={stage.name}>
              <div className="flex justify-between text-xs mb-1">
                <span className={textColor}>{stage.name}</span>
                <span className="text-text-secondary">
                  {stage.status === "done" ? `${stage.duration.toFixed(1)}s` : stage.status === "running" ? "Running..." : "Pending"}
                </span>
              </div>
              <div className="h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
                <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: stage.status === "pending" ? "0%" : `${Math.min(pct * 3, 100)}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
