"use client";

interface PipelineStage {
  name: string;
  status: "complete" | "running" | "pending" | "error";
  duration_s: number;
  target: string;
  latency_ms: number;
}

const samplePipeline: PipelineStage[] = [
  { name: "Token Embedding", status: "complete", duration_s: 0.1, target: "FPGA", latency_ms: 0.5 },
  { name: "Layer 0 Q/K/V", status: "complete", duration_s: 2.3, target: "SWARM", latency_ms: 1.2 },
  { name: "Layer 0 Attention", status: "complete", duration_s: 5.1, target: "SWARM", latency_ms: 2.1 },
  { name: "Layer 0 FFN", status: "complete", duration_s: 1.8, target: "FPGA", latency_ms: 0.3 },
  { name: "Layer 1 Q/K/V", status: "running", duration_s: 1.9, target: "SWARM", latency_ms: 1.5 },
  { name: "Layer 1 Attention", status: "pending", duration_s: 0, target: "SWARM", latency_ms: 0 },
  { name: "Layer 1 FFN", status: "pending", duration_s: 0, target: "FPGA", latency_ms: 0 },
  { name: "Output Head", status: "pending", duration_s: 0, target: "ANALOG", latency_ms: 0 },
];

const targetColors: Record<string, string> = {
  FPGA: "bg-accent-cyan/20 text-accent-cyan",
  SWARM: "bg-accent-amber/20 text-accent-amber",
  ANALOG: "bg-accent-green/20 text-accent-green",
};

const statusIcons: Record<string, string> = {
  complete: "\u2713",
  running: "\u25B6",
  pending: "\u25CB",
  error: "\u2717",
};

export function PipelineView() {
  const completed = samplePipeline.filter((s) => s.status === "complete").length;
  const totalLatency = samplePipeline.reduce((sum, s) => sum + s.latency_ms, 0);

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">PIPELINE VIEW</h3>
      <div className="flex justify-between text-xs text-text-secondary mb-3">
        <span>{completed}/{samplePipeline.length} stages</span>
        <span>Total latency: {totalLatency.toFixed(1)}ms</span>
      </div>
      <div className="space-y-1">
        {samplePipeline.map((stage, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span className={`w-4 text-center ${
              stage.status === "complete" ? "text-accent-green" :
              stage.status === "running" ? "text-accent-cyan animate-pulse" :
              stage.status === "error" ? "text-accent-red" : "text-text-secondary"
            }`}>{statusIcons[stage.status]}</span>
            <span className="flex-1 text-text-primary">{stage.name}</span>
            <span className={`px-1.5 py-0.5 rounded text-[10px] ${targetColors[stage.target] || "bg-bg-tertiary text-text-secondary"}`}>
              {stage.target}
            </span>
            <span className="w-16 text-right text-text-secondary">
              {stage.duration_s > 0 ? `${stage.duration_s}s` : "-"}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-3 h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
        <div
          className="h-full bg-accent-cyan rounded-full transition-all"
          style={{ width: `${(completed / samplePipeline.length) * 100}%` }}
        />
      </div>
    </div>
  );
}
