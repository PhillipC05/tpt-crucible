"use client";

interface SpeculativeProps {
  acceptanceRate?: number;
  draftTps?: number;
  effectiveTps?: number;
  totalTokens?: number;
  acceptedTokens?: number;
  rejectedTokens?: number;
}

export function SpeculativeDecodingPanel({
  acceptanceRate = 0.75,
  draftTps = 45.2,
  effectiveTps = 38.1,
  totalTokens = 1000,
  acceptedTokens = 750,
  rejectedTokens = 250,
}: SpeculativeProps) {
  const rateColor =
    acceptanceRate >= 0.8
      ? "text-accent-green"
      : acceptanceRate >= 0.6
        ? "text-accent-amber"
        : "text-accent-red";

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">
        SPECULATIVE DECODING
      </h3>
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div>
          <div className="text-[10px] text-text-secondary uppercase">
            Acceptance Rate
          </div>
          <div className={`text-xl font-mono font-bold ${rateColor}`}>
            {(acceptanceRate * 100).toFixed(1)}%
          </div>
        </div>
        <div>
          <div className="text-[10px] text-text-secondary uppercase">
            Effective TPS
          </div>
          <div className="text-xl font-mono font-bold text-accent-cyan">
            {effectiveTps.toFixed(1)}
          </div>
        </div>
      </div>

      <div className="w-full h-2 bg-bg-tertiary rounded-full overflow-hidden mb-3">
        <div
          className="h-full bg-accent-cyan rounded-full transition-all"
          style={{ width: `${acceptanceRate * 100}%` }}
        />
      </div>

      <div className="grid grid-cols-3 gap-2 text-[10px]">
        <div className="text-center">
          <div className="text-text-secondary">Draft TPS</div>
          <div className="font-mono text-text-primary">{draftTps.toFixed(1)}</div>
        </div>
        <div className="text-center">
          <div className="text-text-secondary">Accepted</div>
          <div className="font-mono text-accent-green">{acceptedTokens}</div>
        </div>
        <div className="text-center">
          <div className="text-text-secondary">Rejected</div>
          <div className="font-mono text-accent-red">{rejectedTokens}</div>
        </div>
      </div>

      <div className="mt-3 text-[10px] text-text-secondary font-mono">
        Total tokens: {totalTokens} | Speedup: {(effectiveTps / draftTps).toFixed(2)}x vs draft-only
      </div>
    </div>
  );
}
