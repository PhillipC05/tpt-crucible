"use client";

import { useState } from "react";

interface LoadedModel {
  slot: number;
  name: string;
  size_mb: number;
  last_used: string;
  precision: string;
}

const sampleModels: LoadedModel[] = [
  { slot: 0, name: "tinyllama-1.1b", size_mb: 45.2, last_used: "2 min ago", precision: "Q4_K_M" },
  { slot: 1, name: "llama2-7b", size_mb: 3800, last_used: "15 min ago", precision: "Q4_K_M" },
  { slot: 2, name: "mistral-7b", size_mb: 3600, last_used: "1 hr ago", precision: "Q8_0" },
];

export function ModelSwitcher() {
  const [selectedSlot, setSelectedSlot] = useState<number | null>(0);

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">HBM MODEL CACHE</h3>
      <div className="space-y-2">
        {sampleModels.map((model) => (
          <button
            key={model.slot}
            onClick={() => setSelectedSlot(model.slot)}
            className={`w-full flex items-center justify-between p-2 rounded text-xs transition-colors ${
              selectedSlot === model.slot
                ? "bg-accent-cyan/10 border border-accent-cyan/50"
                : "bg-bg-tertiary border border-transparent hover:border-accent-cyan/30"
            }`}
          >
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded ${selectedSlot === model.slot ? "bg-accent-cyan" : "bg-text-secondary"}`} />
              <span className="font-mono">{model.name}</span>
            </div>
            <div className="flex items-center gap-2 text-text-secondary">
              <span>{model.precision}</span>
              <span>{model.size_mb}MB</span>
            </div>
          </button>
        ))}
      </div>
      <div className="flex gap-2 mt-3">
        <button className="flex-1 px-3 py-1.5 rounded bg-accent-cyan/20 text-accent-cyan text-xs">
          Switch Model
        </button>
        <button className="px-3 py-1.5 rounded bg-bg-tertiary text-text-secondary text-xs border border-border">
          Evict
        </button>
      </div>
      <div className="mt-2 text-[10px] text-text-secondary">
        Slot 0: 45.2 MB used / 4096 MB total
      </div>
    </div>
  );
}
