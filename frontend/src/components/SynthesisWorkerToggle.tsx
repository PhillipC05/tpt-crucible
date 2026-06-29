"use client";

import { useState } from "react";

interface SynthesisWorkerToggleProps {
  workerUrl?: string;
  enabled?: boolean;
  onToggle?: (enabled: boolean) => void;
}

export function SynthesisWorkerToggle({
  workerUrl = "",
  enabled = false,
  onToggle,
}: SynthesisWorkerToggleProps) {
  const [url, setUrl] = useState(workerUrl);
  const [isOn, setIsOn] = useState(enabled);

  const handleToggle = () => {
    const next = !isOn;
    setIsOn(next);
    onToggle?.(next);
  };

  if (!url) {
    return null;
  }

  return (
    <div className="stat-card">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-bold text-accent-cyan">SYNTHESIS WORKER</h3>
        <button
          onClick={handleToggle}
          className={`w-10 h-5 rounded-full transition-colors relative ${
            isOn ? "bg-accent-green" : "bg-bg-tertiary"
          }`}
        >
          <div
            className={`w-4 h-4 rounded-full bg-white absolute top-0.5 transition-all ${
              isOn ? "left-5" : "left-0.5"
            }`}
          />
        </button>
      </div>
      <div className="text-xs text-text-secondary mb-2">
        Offload FPGA synthesis to remote worker
      </div>
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Worker URL..."
          className="flex-1 px-2 py-1 rounded bg-bg-tertiary border border-border text-xs text-text-primary font-mono"
        />
      </div>
      {isOn && (
        <div className="mt-2 flex items-center gap-1 text-[10px] text-accent-green">
          <div className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse" />
          Connected to worker
        </div>
      )}
    </div>
  );
}
