"use client";

interface NeuromorphicTargetCardProps {
  chipType?: string;
  numCores?: number;
  spikeRateHz?: number;
  estimatedAccuracy?: number;
}

export function NeuromorphicTargetCard({
  chipType = "loihi",
  numCores = 128,
  spikeRateHz = 45.2,
  estimatedAccuracy = 0.87,
}: NeuromorphicTargetCardProps) {
  return (
    <div className="stat-card">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-bold text-accent-cyan">NEUROMORPHIC</h3>
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-accent-purple/20 text-purple-400">
          SNN
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-[11px] mb-3">
        <div>
          <span className="text-text-secondary">Chip</span>
          <div className="font-mono text-text-primary uppercase">{chipType}</div>
        </div>
        <div>
          <span className="text-text-secondary">Cores</span>
          <div className="font-mono text-text-primary">{numCores}</div>
        </div>
        <div>
          <span className="text-text-secondary">Spike Rate</span>
          <div className="font-mono text-accent-cyan">{spikeRateHz.toFixed(1)} Hz</div>
        </div>
        <div>
          <span className="text-text-secondary">Accuracy</span>
          <div className={`font-mono ${estimatedAccuracy >= 0.85 ? "text-accent-green" : "text-accent-amber"}`}>
            {(estimatedAccuracy * 100).toFixed(1)}%
          </div>
        </div>
      </div>
      <div className="w-full h-2 bg-bg-tertiary rounded-full overflow-hidden">
        <div
          className="h-full bg-purple-400 rounded-full transition-all"
          style={{ width: `${estimatedAccuracy * 100}%` }}
        />
      </div>
      <div className="text-[10px] text-text-secondary mt-1">
        ANN→SNN conversion: LIF neurons, STDP learning
      </div>
    </div>
  );
}
