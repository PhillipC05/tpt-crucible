"use client";

interface DiagnosticNode {
  id: string;
  status: "online" | "warning" | "error";
  value: number;
  message: string;
}

const sampleNodes: DiagnosticNode[] = [
  { id: "N0", status: "online", value: 98, message: "RTT: 1.2ms" },
  { id: "N1", status: "online", value: 96, message: "RTT: 1.5ms" },
  { id: "N2", status: "warning", value: 85, message: "RTT: 3.2ms" },
  { id: "N3", status: "online", value: 99, message: "RTT: 0.8ms" },
  { id: "N4", status: "error", value: 0, message: "No response" },
  { id: "N5", status: "online", value: 97, message: "RTT: 1.1ms" },
  { id: "N6", status: "online", value: 95, message: "RTT: 1.8ms" },
  { id: "N7", status: "warning", value: 78, message: "RTT: 4.5ms" },
  { id: "N8", status: "online", value: 100, message: "RTT: 0.5ms" },
  { id: "N9", status: "online", value: 99, message: "RTT: 0.9ms" },
  { id: "N10", status: "online", value: 97, message: "RTT: 1.3ms" },
  { id: "N11", status: "online", value: 98, message: "RTT: 1.0ms" },
  { id: "N12", status: "online", value: 96, message: "RTT: 1.6ms" },
  { id: "N13", status: "warning", value: 82, message: "RTT: 3.8ms" },
  { id: "N14", status: "online", value: 99, message: "RTT: 0.7ms" },
  { id: "N15", status: "online", value: 97, message: "RTT: 1.2ms" },
];

const statusColors = {
  online: "bg-accent-green/60 border-accent-green/50",
  warning: "bg-accent-amber/60 border-accent-amber/50",
  error: "bg-accent-red/60 border-accent-red/50",
};

export function DiagnosticsHeatmap() {
  const online = sampleNodes.filter((n) => n.status === "online").length;
  const warnings = sampleNodes.filter((n) => n.status === "warning").length;
  const errors = sampleNodes.filter((n) => n.status === "error").length;

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-amber mb-3">DIAGNOSTICS HEATMAP</h3>
      <div className="grid grid-cols-4 gap-2">
        {sampleNodes.map((node) => (
          <div
            key={node.id}
            className={`aspect-square rounded border flex flex-col items-center justify-center ${statusColors[node.status]} hover:scale-105 transition-transform cursor-pointer`}
            title={node.message}
          >
            <div className="text-xs font-bold text-white">{node.id}</div>
            <div className="text-[10px] text-white/80">{node.value}%</div>
          </div>
        ))}
      </div>
      <div className="flex justify-between mt-3 text-[10px] text-text-secondary">
        <span className="flex items-center gap-1">
          <div className="w-2 h-2 rounded bg-accent-green/60" /> {online} online
        </span>
        <span className="flex items-center gap-1">
          <div className="w-2 h-2 rounded bg-accent-amber/60" /> {warnings} warning
        </span>
        <span className="flex items-center gap-1">
          <div className="w-2 h-2 rounded bg-accent-red/60" /> {errors} error
        </span>
      </div>
    </div>
  );
}
