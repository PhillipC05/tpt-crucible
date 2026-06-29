"use client";

interface LayerDensity {
  name: string;
  density: number;
  mode: string;
}

interface SparsityMapOverlayProps {
  layers?: LayerDensity[];
}

const defaultLayers: LayerDensity[] = [
  { name: "layer_0_q_proj", density: 0.72, mode: "2:4" },
  { name: "layer_0_k_proj", density: 0.68, mode: "2:4" },
  { name: "layer_0_v_proj", density: 0.71, mode: "2:4" },
  { name: "layer_0_ffn_up", density: 0.45, mode: "4:8" },
  { name: "layer_0_ffn_down", density: 0.52, mode: "2:4" },
  { name: "layer_1_q_proj", density: 0.80, mode: "none" },
  { name: "layer_1_ffn_up", density: 0.38, mode: "4:8" },
];

function densityColor(density: number): string {
  if (density >= 0.75) return "bg-accent-green/60";
  if (density >= 0.5) return "bg-accent-amber/60";
  return "bg-accent-red/40";
}

export function SparsityMapOverlay({ layers = defaultLayers }: SparsityMapOverlayProps) {
  const avgDensity = layers.reduce((s, l) => s + l.density, 0) / layers.length;

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">SPARSITY MAP</h3>
      <div className="flex justify-between text-xs text-text-secondary mb-3">
        <span>Avg density: {(avgDensity * 100).toFixed(1)}%</span>
        <span>Est. speedup: {(1 / Math.max(avgDensity, 0.01)).toFixed(1)}x</span>
      </div>
      <div className="space-y-1">
        {layers.map((layer) => (
          <div key={layer.name} className="flex items-center gap-2 text-[10px]">
            <span className={`w-8 text-center px-1 py-0.5 rounded ${densityColor(layer.density)} text-white`}>
              {layer.mode}
            </span>
            <span className="flex-1 text-text-primary font-mono truncate">{layer.name}</span>
            <div className="w-16 h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${densityColor(layer.density)}`}
                style={{ width: `${layer.density * 100}%` }}
              />
            </div>
            <span className="w-8 text-right font-mono text-text-secondary">
              {(layer.density * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
      <div className="mt-2 text-[9px] text-text-secondary font-mono">
        2:4 = skip 2 of 4 weights | 4:8 = skip 4 of 8
      </div>
    </div>
  );
}
