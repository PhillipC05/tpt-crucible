"use client";

interface LayerQuant {
  name: string;
  bits: number;
  sensitivity: number;
}

const sampleLayers: LayerQuant[] = [
  { name: "layer_0_q_proj", bits: 4, sensitivity: 0.1 },
  { name: "layer_0_k_proj", bits: 4, sensitivity: 0.15 },
  { name: "layer_0_v_proj", bits: 4, sensitivity: 0.2 },
  { name: "layer_0_attn", bits: 8, sensitivity: 0.6 },
  { name: "layer_0_ffn_up", bits: 4, sensitivity: 0.12 },
  { name: "layer_0_ffn_down", bits: 8, sensitivity: 0.55 },
  { name: "layer_1_q_proj", bits: 4, sensitivity: 0.11 },
  { name: "layer_1_attn", bits: 16, sensitivity: 0.85 },
];

const bitsColor: Record<number, string> = {
  4: "bg-accent-green/60",
  8: "bg-accent-amber/60",
  16: "bg-accent-red/40",
  32: "bg-accent-red/60",
};

export function QuantizationMap() {
  const avgBits = sampleLayers.reduce((sum, l) => sum + l.bits, 0) / sampleLayers.length;
  const compression = (32 / avgBits).toFixed(1);

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">QUANTIZATION MAP</h3>
      <div className="flex justify-between text-xs text-text-secondary mb-3">
        <span>Avg bits: {avgBits.toFixed(1)}</span>
        <span>Compression: {compression}x</span>
      </div>
      <div className="space-y-1">
        {sampleLayers.map((layer) => (
          <div key={layer.name} className="flex items-center gap-2 text-[10px]">
            <span className={`w-8 text-center px-1 py-0.5 rounded ${bitsColor[layer.bits]} text-white`}>
              {layer.bits}b
            </span>
            <span className="flex-1 text-text-primary font-mono truncate">{layer.name}</span>
            <div className="w-16 h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
              <div
                className="h-full bg-accent-cyan rounded-full"
                style={{ width: `${layer.sensitivity * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      <div className="flex justify-between mt-2 text-[10px] text-text-secondary">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-accent-green/60" /> INT4
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-accent-amber/60" /> INT8
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-accent-red/40" /> FP16
        </div>
      </div>
    </div>
  );
}
