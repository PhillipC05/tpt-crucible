"use client";

import { useState } from "react";

interface ReplayEntry {
  timestamp_ms: number;
  hardware_type: string;
  node_id: string;
  tokens_per_second: number;
  memory_bandwidth: number;
  thermal_drift: number;
}

const sampleData: ReplayEntry[] = Array.from({ length: 20 }, (_, i) => ({
  timestamp_ms: i * 1000,
  hardware_type: i % 3 === 0 ? "fpga" : i % 3 === 1 ? "swarm" : "analog",
  node_id: `node_${i % 4}`,
  tokens_per_second: 100 + Math.random() * 50,
  memory_bandwidth: 300 + Math.random() * 200,
  thermal_drift: 0.05 + Math.random() * 0.1,
}));

export function ReplayOverlay() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const current = sampleData[currentIndex] || sampleData[0];

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">REPLAY OVERLAY</h3>
      <div className="flex gap-4 text-xs">
        <div className="flex-1">
          <div className="text-text-secondary mb-1">Before</div>
          <div className="bg-bg-tertiary rounded p-2">
            <div className="text-accent-cyan">{sampleData[0]?.tokens_per_second.toFixed(1)} TPS</div>
            <div className="text-text-secondary">fpga | node_0</div>
          </div>
        </div>
        <div className="flex items-center text-text-secondary">\u2192</div>
        <div className="flex-1">
          <div className="text-text-secondary mb-1">After</div>
          <div className="bg-bg-tertiary rounded p-2">
            <div className="text-accent-green">{current.tokens_per_second.toFixed(1)} TPS</div>
            <div className="text-text-secondary">{current.hardware_type} | {current.node_id}</div>
          </div>
        </div>
      </div>
      <div className="mt-3">
        <input
          type="range"
          min="0"
          max={sampleData.length - 1}
          value={currentIndex}
          onChange={(e) => setCurrentIndex(parseInt(e.target.value))}
          className="w-full accent-accent-cyan"
        />
        <div className="flex justify-between text-[10px] text-text-secondary">
          <span>0s</span>
          <span>{(currentIndex * 1).toFixed(0)}s</span>
          <span>{(sampleData.length - 1).toFixed(0)}s</span>
        </div>
      </div>
    </div>
  );
}
