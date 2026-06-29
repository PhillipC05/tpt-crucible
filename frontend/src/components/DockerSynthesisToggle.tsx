"use client";

import { useState } from "react";

interface DockerSynthesisToggleProps {
  dockerAvailable?: boolean;
  hostToolchainAvailable?: boolean;
}

export function DockerSynthesisToggle({
  dockerAvailable = true,
  hostToolchainAvailable = false,
}: DockerSynthesisToggleProps) {
  const [useDocker, setUseDocker] = useState(!hostToolchainAvailable && dockerAvailable);

  if (!dockerAvailable || hostToolchainAvailable) return null;

  return (
    <div className="stat-card">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-bold text-accent-cyan">DOCKER SYNTHESIS</h3>
        <button
          onClick={() => setUseDocker(!useDocker)}
          className={`w-10 h-5 rounded-full transition-colors relative ${
            useDocker ? "bg-accent-green" : "bg-bg-tertiary"
          }`}
        >
          <div
            className={`w-4 h-4 rounded-full bg-white absolute top-0.5 transition-all ${
              useDocker ? "left-5" : "left-0.5"
            }`}
          />
        </button>
      </div>
      <div className="text-xs text-text-secondary mb-2">
        Host toolchain not found. Using Docker container for synthesis.
      </div>
      {useDocker && (
        <div className="flex items-center gap-1 text-[10px] text-accent-green">
          <div className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse" />
          Synthesis routed through tpt-crucible/synthesis container
        </div>
      )}
    </div>
  );
}
