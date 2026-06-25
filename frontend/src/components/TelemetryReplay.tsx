"use client";

import { useState, useEffect, useRef } from "react";

interface ReplayEntry {
  timestamp_ms: number;
  hardware_type: string;
  node_id: string;
  metrics: Record<string, number>;
}

interface ReplayState {
  entries: ReplayEntry[];
  currentIndex: number;
  isPlaying: boolean;
  playbackSpeed: number;
}

export function TelemetryReplay({ entries }: { entries?: ReplayEntry[] }) {
  const [state, setState] = useState<ReplayState>({
    entries: entries || [],
    currentIndex: 0,
    isPlaying: false,
    playbackSpeed: 1,
  });
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (state.isPlaying && state.entries.length > 0) {
      intervalRef.current = setInterval(() => {
        setState((prev) => {
          const next = prev.currentIndex + 1;
          if (next >= prev.entries.length) {
            return { ...prev, isPlaying: false, currentIndex: prev.entries.length - 1 };
          }
          return { ...prev, currentIndex: next };
        });
      }, 100 / state.playbackSpeed);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [state.isPlaying, state.playbackSpeed, state.entries.length]);

  const currentEntry = state.entries[state.currentIndex];
  const progress = state.entries.length > 0 ? (state.currentIndex / (state.entries.length - 1)) * 100 : 0;

  return (
    <div className="stat-card space-y-4">
      <h3 className="text-sm font-bold text-accent-cyan">TELEMETRY REPLAY</h3>

      <div className="flex items-center gap-2">
        <button
          onClick={() => setState((p) => ({ ...p, isPlaying: false, currentIndex: 0 }))}
          className="px-2 py-1 rounded bg-bg-tertiary text-text-secondary hover:text-text-primary text-xs"
        >
          {"<<"}
        </button>
        <button
          onClick={() => setState((p) => ({ ...p, isPlaying: !p.isPlaying }))}
          className="px-3 py-1 rounded bg-accent-cyan/20 text-accent-cyan text-xs font-bold"
        >
          {state.isPlaying ? "PAUSE" : "PLAY"}
        </button>
        <button
          onClick={() => setState((p) => ({
            ...p,
            isPlaying: false,
            currentIndex: Math.min(p.currentIndex + 1, p.entries.length - 1),
          }))}
          className="px-2 py-1 rounded bg-bg-tertiary text-text-secondary hover:text-text-primary text-xs"
        >
          {">>"}
        </button>

        <div className="flex items-center gap-1 ml-2">
          {[0.5, 1, 2, 4].map((speed) => (
            <button
              key={speed}
              onClick={() => setState((p) => ({ ...p, playbackSpeed: speed }))}
              className={`px-1.5 py-0.5 rounded text-[10px] ${
                state.playbackSpeed === speed
                  ? "bg-accent-cyan/20 text-accent-cyan"
                  : "bg-bg-tertiary text-text-secondary"
              }`}
            >
              {speed}x
            </button>
          ))}
        </div>
      </div>

      <div className="relative">
        <div className="h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
          <div
            className="h-full bg-accent-cyan transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
        <input
          type="range"
          min="0"
          max={Math.max(state.entries.length - 1, 0)}
          value={state.currentIndex}
          onChange={(e) => setState((p) => ({ ...p, isPlaying: false, currentIndex: parseInt(e.target.value) }))}
          className="absolute inset-0 w-full opacity-0 cursor-pointer"
        />
      </div>

      <div className="flex justify-between text-[10px] text-text-secondary">
        <span>Entry {state.currentIndex + 1}/{state.entries.length}</span>
        <span>{currentEntry ? new Date(currentEntry.timestamp_ms).toLocaleTimeString() : "--:--:--"}</span>
      </div>

      {currentEntry && (
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="flex justify-between">
            <span className="text-text-secondary">Hardware</span>
            <span className="text-accent-cyan">{currentEntry.hardware_type}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Node</span>
            <span>{currentEntry.node_id}</span>
          </div>
          {Object.entries(currentEntry.metrics).map(([key, value]) => (
            <div key={key} className="flex justify-between">
              <span className="text-text-secondary">{key}</span>
              <span className="font-mono">{typeof value === "number" ? value.toFixed(2) : value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
