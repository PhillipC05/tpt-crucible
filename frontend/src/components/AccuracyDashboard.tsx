"use client";

interface LayerAccuracy {
  name: string;
  voltageDrift: number;
  status: "pass" | "warn" | "fail";
}

interface AccuracyDashboardProps {
  layers?: LayerAccuracy[];
  overallSimilarity?: number;
  perplexityDelta?: number;
}

const defaultLayers: LayerAccuracy[] = [
  { name: "layer_0_q_proj", voltageDrift: 0.01, status: "pass" },
  { name: "layer_0_attn", voltageDrift: 0.08, status: "warn" },
  { name: "layer_0_ffn", voltageDrift: 0.02, status: "pass" },
  { name: "layer_1_q_proj", voltageDrift: 0.15, status: "fail" },
  { name: "layer_1_attn", voltageDrift: 0.03, status: "pass" },
];

const statusColor: Record<string, string> = {
  pass: "bg-accent-green",
  warn: "bg-accent-amber",
  fail: "bg-accent-red",
};

const statusText: Record<string, string> = {
  pass: "text-accent-green",
  warn: "text-accent-amber",
  fail: "text-accent-red",
};

export function AccuracyDashboard({
  layers = defaultLayers,
  overallSimilarity = 0.95,
  perplexityDelta = 0.02,
}: AccuracyDashboardProps) {
  const passCount = layers.filter((l) => l.status === "pass").length;
  const warnCount = layers.filter((l) => l.status === "warn").length;
  const failCount = layers.filter((l) => l.status === "fail").length;

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">ACCURACY DASHBOARD</h3>
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="text-center">
          <div className="text-[10px] text-text-secondary">Similarity</div>
          <div className={`text-lg font-mono font-bold ${overallSimilarity >= 0.9 ? "text-accent-green" : overallSimilarity >= 0.7 ? "text-accent-amber" : "text-accent-red"}`}>
            {(overallSimilarity * 100).toFixed(1)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-[10px] text-text-secondary">Perplexity Δ</div>
          <div className="text-lg font-mono font-bold text-accent-cyan">
            {perplexityDelta.toFixed(3)}
          </div>
        </div>
        <div className="text-center">
          <div className="text-[10px] text-text-secondary">Layers</div>
          <div className="text-lg font-mono font-bold text-text-primary">
            {passCount}/{layers.length}
          </div>
        </div>
      </div>

      <div className="space-y-1">
        {layers.map((layer) => (
          <div key={layer.name} className="flex items-center gap-2 text-[10px]">
            <div className={`w-2 h-2 rounded-full ${statusColor[layer.status]}`} />
            <span className="flex-1 text-text-primary font-mono truncate">{layer.name}</span>
            <span className={`font-mono ${statusText[layer.status]}`}>
              {layer.voltageDrift.toFixed(3)}V
            </span>
          </div>
        ))}
      </div>

      <div className="mt-2 flex gap-3 text-[10px] text-text-secondary">
        <span className="text-accent-green">{passCount} pass</span>
        <span className="text-accent-amber">{warnCount} warn</span>
        <span className="text-accent-red">{failCount} fail</span>
      </div>
    </div>
  );
}
