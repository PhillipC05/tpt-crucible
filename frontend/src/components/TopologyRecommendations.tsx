"use client";

interface TopologyRecommendation {
  type: string;
  nodeCount: number;
  predictedLatencyMs: number;
  predictedPowerMw: number;
  confidence: number;
  score: number;
  strategy: string;
  reasoning: string;
}

interface TopologyRecommendationsProps {
  recommendations?: TopologyRecommendation[];
  onSelect?: (topology: string, strategy: string) => void;
}

const defaultRecommendations: TopologyRecommendation[] = [
  { type: "mesh", nodeCount: 16, predictedLatencyMs: 3.2, predictedPowerMw: 2400, confidence: 0.92, score: 0.88, strategy: "hybrid", reasoning: "Lowest latency; mesh topology ideal for attention-heavy model" },
  { type: "star", nodeCount: 16, predictedLatencyMs: 4.1, predictedPowerMw: 2880, confidence: 0.85, score: 0.78, strategy: "head-parallel", reasoning: "Central aggregation for head-parallel; simple wiring" },
  { type: "grid2d", nodeCount: 16, predictedLatencyMs: 5.5, predictedPowerMw: 2400, confidence: 0.75, score: 0.71, strategy: "layer", reasoning: "Standard grid; good for regular data flow patterns" },
  { type: "ring", nodeCount: 16, predictedLatencyMs: 8.2, predictedPowerMw: 2160, confidence: 0.65, score: 0.58, strategy: "layer", reasoning: "Simple wiring, predictable latency, low power" },
];

export function TopologyRecommendations({
  recommendations = defaultRecommendations,
  onSelect,
}: TopologyRecommendationsProps) {
  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">TOPOLOGY RECOMMENDATIONS</h3>
      <div className="space-y-2">
        {recommendations.map((rec, i) => (
          <button
            key={`${rec.type}-${i}`}
            onClick={() => onSelect?.(rec.type, rec.strategy)}
            className={`w-full p-2.5 rounded border text-left transition-colors ${
              i === 0
                ? "border-accent-cyan bg-accent-cyan/10"
                : "border-border bg-bg-tertiary hover:border-accent-cyan/50"
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-text-primary uppercase">{rec.type}</span>
                {i === 0 && (
                  <span className="text-[9px] px-1 py-0.5 rounded bg-accent-cyan/20 text-accent-cyan">
                    BEST
                  </span>
                )}
              </div>
              <span className="text-[10px] font-mono text-accent-cyan">
                score: {rec.score.toFixed(2)}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-1 text-[9px] text-text-secondary mb-1">
              <span>latency: {rec.predictedLatencyMs.toFixed(1)}ms</span>
              <span>power: {rec.predictedPowerMw}mW</span>
              <span>strategy: {rec.strategy}</span>
            </div>
            <div className="text-[9px] text-text-secondary italic">{rec.reasoning}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
