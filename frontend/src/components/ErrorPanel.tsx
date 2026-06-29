"use client";

import { useState } from "react";

interface ErrorEntry {
  tool: string;
  error_type: string;
  message: string;
  suggestion: string;
  raw_output?: string;
}

const sampleErrors: ErrorEntry[] = [
  { tool: "yosys", error_type: "timing_failure", message: "Timing closure failed on critical path", suggestion: "Reduce clock frequency from 300MHz to 250MHz", raw_output: "ERROR: timing analysis failed..." },
  { tool: "nextpnr", error_type: "resource_overflow", message: "DSP slice count exceeds available resources", suggestion: "Reduce MAC array dimensions from 64x64 to 32x32" },
  { tool: "platformio", error_type: "upload_failed", message: "USB upload timed out", suggestion: "Check USB connection and ensure board is in flash mode" },
];

export function ErrorPanel() {
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-red mb-3">TOOLCHAIN ERRORS</h3>
      <div className="space-y-2">
        {sampleErrors.map((err, i) => (
          <div key={i} className="bg-bg-tertiary rounded p-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-accent-red">{err.tool}</span>
                <span className="text-[10px] text-text-secondary">{err.error_type}</span>
              </div>
              <button
                onClick={() => setExpanded(expanded === i ? null : i)}
                className="text-[10px] text-text-secondary hover:text-text-primary"
              >
                {expanded === i ? "Hide" : "Details"}
              </button>
            </div>
            <div className="text-xs text-text-primary mt-1">{err.message}</div>
            <div className="text-xs text-accent-green mt-1">\u27A4 {err.suggestion}</div>
            {expanded === i && err.raw_output && (
              <pre className="mt-2 p-2 bg-bg-primary rounded text-[10px] text-text-secondary overflow-x-auto">
                {err.raw_output}
              </pre>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
