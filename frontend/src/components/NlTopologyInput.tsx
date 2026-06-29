"use client";

import { useState } from "react";

interface NlTopologyInputProps {
  onSubmit?: (description: string) => void;
}

export function NlTopologyInput({ onSubmit }: NlTopologyInputProps) {
  const [input, setInput] = useState("");
  const [preview, setPreview] = useState<string | null>(null);

  const handleSubmit = () => {
    if (!input.trim()) return;
    setPreview(
      `Parsed: ${input.trim()} → topology type: auto-detect, node count: auto`
    );
    onSubmit?.(input);
  };

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">
        DESCRIBE YOUR TOPOLOGY
      </h3>
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="e.g. 16 ESP32 nodes in a 4x4 grid, star topology with 8 nodes..."
        className="w-full px-3 py-2 rounded bg-bg-tertiary border border-border text-sm text-text-primary placeholder-text-secondary resize-none h-20 font-mono"
      />
      <button
        onClick={handleSubmit}
        disabled={!input.trim()}
        className="mt-2 px-4 py-1.5 rounded bg-accent-cyan text-bg-primary text-xs font-bold disabled:opacity-30"
      >
        Generate Topology
      </button>
      {preview && (
        <div className="mt-2 p-2 rounded bg-bg-tertiary text-xs text-text-secondary font-mono">
          {preview}
        </div>
      )}
    </div>
  );
}
