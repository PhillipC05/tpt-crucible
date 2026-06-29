"use client";

interface LayerSparsity {
  name: string;
  density: number;
  mode: string;
}

const sampleLayers: LayerSparsity[] = [
  { name: "layer_0_q_proj", density: 0.75, mode: "2:4" },
  { name: "layer_0_k_proj", density: 0.72, mode: "2:4" },
  { name: "layer_0_v_proj", density: 0.68, mode: "2:4" },
  { name: "layer_0_ffn_up", density: 0.55, mode: "4:8" },
  { name: "layer_0_ffn_down", density: 0.62, mode: "4:8" },
  { name: "layer_1_q_proj", density: 0.78, mode: "2:4" },
  { name: "layer_1_k_proj", density: 0.71, mode: "2:4" },
  { name: "layer_1_v_proj", density: 0.65, mode: "2:4" },
];

function densityColor(density: number): string {
  if (density > 0.7) return "bg-accent-green/60";
  if (density > 0.5) return "bg-accent-amber/60";
  return "bg-accent-red/60";
}

export function SparsityHeatmap() {
  const avgDensity = sampleLayers.reduce((sum, l) => sum + l.density, 0) / sampleLayers.length;
  const estimatedSpeedup = (1 / avgDensity).toFixed(1);

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">SPARSITY MAP</h3>
      <div className="flex justify-between text-xs text-text-secondary mb-3">
        <span>Avg density: {(avgDensity * 100).toFixed(0)}%</span>
        <span>Est. speedup: {estimatedSpeedup}x</span>
      </div>
      <div className="grid grid-cols-2 gap-1">
        {sampleLayers.map((layer) => (
          <div
            key={layer.name}
            className={`p-1.5 rounded text-[10px] ${densityColor(layer.density)} text-white`}
          >
            <div className="font-mono truncate">{layer.name}</div>
            <div className="flex justify-between mt-0.5">
              <span>{(layer.density * 100).toFixed(0)}%</span>
              <span>{layer.mode}</span>
            </div>
          </div>
        ))}
      </div>
      <div className="flex justify-between mt-3 text-[10px] text-text-secondary">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-accent-green/60" /> Dense (&gt;70%)
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-accent-amber/60" /> Medium
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-accent-red/60" /> Sparse (&lt;50%)
        </div>
      </div>
    </div>
  );
}
