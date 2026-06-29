"use client";

interface DiscoveryProps {
  discovered?: boolean;
  topologyType?: string;
  nodeCount?: number;
  measurements?: number;
  rttMatrix?: number[][];
}

export function AutoDiscoveryPanel({
  discovered = false,
  topologyType = "grid2d",
  nodeCount = 16,
  measurements = 120,
}: DiscoveryProps) {
  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">
        AUTO-DISCOVERY
      </h3>
      {discovered ? (
        <div className="space-y-2">
          <div className="flex justify-between text-[11px]">
            <span className="text-text-secondary">Topology</span>
            <span className="font-mono text-accent-green">{topologyType}</span>
          </div>
          <div className="flex justify-between text-[11px]">
            <span className="text-text-secondary">Nodes</span>
            <span className="font-mono text-text-primary">{nodeCount}</span>
          </div>
          <div className="flex justify-between text-[11px]">
            <span className="text-text-secondary">RTT Measurements</span>
            <span className="font-mono text-text-primary">{measurements}</span>
          </div>
          <div className="mt-2 text-[10px] text-accent-green font-mono">
            Topology confirmed. Ready for partitioning.
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <div className="text-[11px] text-text-secondary">
            No topology discovered yet.
          </div>
          <div className="text-[10px] text-text-secondary font-mono">
            Run <code className="text-accent-cyan">tpt-alloy discover</code> to probe
            node RTT and infer topology.
          </div>
        </div>
      )}
    </div>
  );
}
