"use client";

import { useState } from "react";

interface DetectedBoard {
  name: string;
  type: string;
  serial: string;
  driver: string;
}

interface BoardAutoDetectProps {
  detected?: DetectedBoard | null;
  onConfirm?: (board: DetectedBoard) => void;
  onSelectManual?: () => void;
}

export function BoardAutoDetect({
  detected = null,
  onConfirm,
  onSelectManual,
}: BoardAutoDetectProps) {
  const [confirmed, setConfirmed] = useState(false);

  if (!detected) {
    return (
      <div className="stat-card">
        <h3 className="text-sm font-bold text-accent-cyan mb-2">BOARD DETECTION</h3>
        <div className="text-xs text-text-secondary mb-3">
          No hardware detected via USB/serial.
        </div>
        <button
          onClick={onSelectManual}
          className="w-full px-3 py-2 rounded border border-border bg-bg-tertiary hover:border-accent-cyan text-sm text-left"
        >
          <div className="text-text-primary">Select Manually</div>
          <div className="text-[10px] text-text-secondary">Choose from available board profiles</div>
        </button>
      </div>
    );
  }

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-2">BOARD DETECTED</h3>
      <div className="space-y-1 text-[11px] mb-3">
        <div className="flex justify-between">
          <span className="text-text-secondary">Board</span>
          <span className="font-mono text-text-primary">{detected.name}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-secondary">Type</span>
          <span className="font-mono text-text-primary">{detected.type}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-secondary">Serial</span>
          <span className="font-mono text-text-primary truncate max-w-[120px]">{detected.serial}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-secondary">Driver</span>
          <span className="font-mono text-accent-green">{detected.driver}</span>
        </div>
      </div>
      {!confirmed ? (
        <button
          onClick={() => { setConfirmed(true); onConfirm?.(detected); }}
          className="w-full px-3 py-1.5 rounded bg-accent-cyan text-bg-primary text-xs font-bold"
        >
          Confirm Board Profile
        </button>
      ) : (
        <div className="text-[10px] text-accent-green font-mono">Board profile confirmed</div>
      )}
    </div>
  );
}
