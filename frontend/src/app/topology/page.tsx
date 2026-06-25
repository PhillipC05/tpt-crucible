"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

const TopologyVisualizer = dynamic(
  () => import("@/components/TopologyVisualizer").then((mod) => mod.TopologyVisualizer),
  { ssr: false }
);

const topologyTypes = [
  { id: "grid2d" as const, label: "2D Grid", description: "Regular mesh with nearest-neighbor connections" },
  { id: "star" as const, label: "Star", description: "Central hub with radial connections" },
  { id: "ring" as const, label: "Ring", description: "Circular topology with bidirectional links" },
  { id: "mesh" as const, label: "Full Mesh", description: "Random high-density interconnect" },
];

export default function TopologyPage() {
  const [topologyType, setTopologyType] = useState<"grid2d" | "star" | "ring" | "mesh">("grid2d");
  const [nodeCount, setNodeCount] = useState(16);

  return (
    <div className="min-h-screen bg-bg-primary grid-bg p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-accent-cyan">3D Swarm Topology Visualizer</h1>
          <p className="text-sm text-text-secondary mt-1">
            Interactive 3D visualization of swarm node layouts. Click nodes to inspect.
          </p>
        </div>

        <div className="flex flex-wrap gap-4">
          <div className="stat-card">
            <div className="stat-label mb-2">TOPOLOGY TYPE</div>
            <div className="flex gap-2">
              {topologyTypes.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTopologyType(t.id)}
                  className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                    topologyType === t.id
                      ? "bg-accent-cyan/20 text-accent-cyan border border-accent-cyan/50"
                      : "bg-bg-tertiary text-text-secondary border border-border hover:border-accent-cyan/30"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label mb-2">NODE COUNT</div>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="4"
                max="64"
                value={nodeCount}
                onChange={(e) => setNodeCount(parseInt(e.target.value))}
                className="w-32 accent-accent-cyan"
              />
              <span className="text-accent-cyan font-mono text-sm w-8">{nodeCount}</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label mb-2">DESCRIPTION</div>
            <p className="text-xs text-text-secondary">
              {topologyTypes.find((t) => t.id === topologyType)?.description}
            </p>
          </div>
        </div>

        <div className="h-[600px] rounded-lg overflow-hidden border border-border">
          <TopologyVisualizer
            topologyType={topologyType}
            nodeCount={nodeCount}
            className="h-full"
          />
        </div>
      </div>
    </div>
  );
}
