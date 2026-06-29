"use client";

interface PipelineStage {
  nodeId: number;
  stageIndex: number;
  layers: number[];
  utilization: number;
}

interface PipelineUtilizationProps {
  stages?: PipelineStage[];
  depth?: number;
  bubblePct?: number;
}

const defaultStages: PipelineStage[] = [
  { nodeId: 0, stageIndex: 0, layers: [0, 1, 2, 3], utilization: 0.85 },
  { nodeId: 1, stageIndex: 1, layers: [4, 5, 6, 7], utilization: 0.92 },
  { nodeId: 2, stageIndex: 2, layers: [8, 9, 10, 11], utilization: 0.78 },
  { nodeId: 3, stageIndex: 3, layers: [12, 13, 14, 15], utilization: 0.88 },
];

export function PipelineUtilization({
  stages = defaultStages,
  depth = 4,
  bubblePct = 12.5,
}: PipelineUtilizationProps) {
  const avgUtil =
    stages.reduce((sum, s) => sum + s.utilization, 0) / stages.length;

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">
        PIPELINE UTILIZATION
      </h3>
      <div className="flex justify-between text-xs text-text-secondary mb-3">
        <span>Depth: {depth}</span>
        <span>Bubble: {bubblePct.toFixed(1)}%</span>
        <span>Avg: {(avgUtil * 100).toFixed(1)}%</span>
      </div>

      <div className="space-y-1.5">
        {stages.map((stage) => (
          <div key={stage.nodeId} className="flex items-center gap-2 text-[10px]">
            <span className="w-12 text-text-secondary font-mono">
              N{stage.nodeId}
            </span>
            <div className="flex-1 h-3 bg-bg-tertiary rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  stage.utilization >= 0.9
                    ? "bg-accent-green"
                    : stage.utilization >= 0.7
                      ? "bg-accent-amber"
                      : "bg-accent-red"
                }`}
                style={{ width: `${stage.utilization * 100}%` }}
              />
            </div>
            <span className="w-10 text-right font-mono text-text-primary">
              {(stage.utilization * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>

      <div className="mt-3 text-[9px] text-text-secondary font-mono">
        Pipeline bubble = (depth - 1) / total cycles. Lower is better.
      </div>
    </div>
  );
}
