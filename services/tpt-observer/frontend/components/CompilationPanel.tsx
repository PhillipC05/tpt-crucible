"use client";

import React, { useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type HardwareTarget = "alloy" | "fusion" | "element";
export type QuantizeMode = "off" | "auto" | "int8" | "int4" | "mixed-precision";

export interface CompilationConfig {
  target: HardwareTarget;
  quantize: QuantizeMode;
  accuracyBudget: number;   // 0.0–1.0 (max allowed accuracy loss)
  sparsity: "none" | "2:4" | "auto";
  incremental: boolean;
}

export interface CompilationPanelProps {
  estimatedMinutes?: number;
  onCompile: (config: CompilationConfig) => void;
  disabled?: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const TARGET_LABELS: Record<HardwareTarget, string> = {
  alloy: "Swarm (ESP32 / RP2040 / RISC-V)",
  fusion: "FPGA (Xilinx Alveo)",
  element: "Analog (SPICE/KiCad)",
};

const QUANT_LABELS: Record<QuantizeMode, string> = {
  off: "None — keep original precision",
  auto: "Auto — search for best scheme",
  int8: "INT8 — uniform 8-bit",
  int4: "INT4 — uniform 4-bit",
  "mixed-precision": "Mixed precision — per-layer",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CompilationPanel({
  estimatedMinutes,
  onCompile,
  disabled = false,
}: CompilationPanelProps) {
  const [target, setTarget] = useState<HardwareTarget>("alloy");
  const [quantize, setQuantize] = useState<QuantizeMode>("auto");
  const [accuracyBudget, setAccuracyBudget] = useState(0.02);
  const [sparsity, setSparsity] = useState<"none" | "2:4" | "auto">("none");
  const [incremental, setIncremental] = useState(false);

  const handleCompile = () => {
    onCompile({ target, quantize, accuracyBudget, sparsity, incremental });
  };

  return (
    <div className="w-80 rounded border border-zinc-700 bg-zinc-900 p-4 font-mono text-xs text-zinc-200">
      <h2 className="mb-4 text-sm font-semibold tracking-widest text-cyan-400 uppercase">
        Compilation
      </h2>

      {/* Hardware target */}
      <label className="mb-3 block">
        <span className="mb-1 block text-zinc-400">Hardware target</span>
        <select
          value={target}
          onChange={(e) => setTarget(e.target.value as HardwareTarget)}
          disabled={disabled}
          className="w-full rounded border border-zinc-600 bg-zinc-800 px-2 py-1.5 text-zinc-100 focus:outline-none focus:ring-1 focus:ring-cyan-500 disabled:opacity-50"
        >
          {(Object.keys(TARGET_LABELS) as HardwareTarget[]).map((t) => (
            <option key={t} value={t}>
              {TARGET_LABELS[t]}
            </option>
          ))}
        </select>
      </label>

      {/* Auto-quantization toggle */}
      <div className="mb-3">
        <span className="mb-1 block text-zinc-400">Quantization</span>
        <div className="flex flex-wrap gap-1">
          {(Object.keys(QUANT_LABELS) as QuantizeMode[]).map((m) => (
            <button
              key={m}
              onClick={() => setQuantize(m)}
              disabled={disabled}
              className={`rounded px-2 py-1 transition-colors disabled:opacity-50 ${
                quantize === m
                  ? "bg-cyan-700 text-white ring-1 ring-cyan-400"
                  : "bg-zinc-700 text-zinc-300 hover:bg-zinc-600"
              }`}
            >
              {m === "auto" ? "Auto ✦" : m === "mixed-precision" ? "mixed" : m}
            </button>
          ))}
        </div>
        <p className="mt-1 text-zinc-500">{QUANT_LABELS[quantize]}</p>
      </div>

      {/* Accuracy budget — only shown when quantization is active */}
      {quantize !== "off" && (
        <label className="mb-3 block">
          <span className="mb-1 flex justify-between text-zinc-400">
            <span>Max accuracy loss</span>
            <span className="text-amber-400">{(accuracyBudget * 100).toFixed(1)} %</span>
          </span>
          <input
            type="range"
            min={0.005}
            max={0.1}
            step={0.005}
            value={accuracyBudget}
            onChange={(e) => setAccuracyBudget(parseFloat(e.target.value))}
            disabled={disabled}
            className="w-full accent-cyan-400 disabled:opacity-50"
          />
        </label>
      )}

      {/* Sparsity */}
      <label className="mb-3 block">
        <span className="mb-1 block text-zinc-400">Sparsity</span>
        <select
          value={sparsity}
          onChange={(e) => setSparsity(e.target.value as typeof sparsity)}
          disabled={disabled}
          className="w-full rounded border border-zinc-600 bg-zinc-800 px-2 py-1.5 text-zinc-100 focus:outline-none focus:ring-1 focus:ring-cyan-500 disabled:opacity-50"
        >
          <option value="none">None</option>
          <option value="2:4">2:4 structured (FPGA skip-zero gating)</option>
          <option value="auto">Auto-detect from .tptprofile</option>
        </select>
      </label>

      {/* Incremental compilation */}
      <label className="mb-4 flex cursor-pointer items-center gap-2">
        <input
          type="checkbox"
          checked={incremental}
          onChange={(e) => setIncremental(e.target.checked)}
          disabled={disabled}
          className="accent-cyan-500 disabled:opacity-50"
        />
        <span className="text-zinc-400">
          Incremental (use cache for unchanged layers)
        </span>
      </label>

      {/* Estimated time */}
      {estimatedMinutes !== undefined && (
        <p className="mb-4 text-zinc-500">
          Estimated:{" "}
          <span className="text-amber-400">
            ~{estimatedMinutes}–{Math.round(estimatedMinutes * 1.3)} min
          </span>
        </p>
      )}

      {/* Compile button */}
      <button
        onClick={handleCompile}
        disabled={disabled}
        className="w-full rounded bg-cyan-700 py-2 font-bold tracking-wider text-white transition-colors hover:bg-cyan-600 active:bg-cyan-800 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {disabled ? "Compiling…" : "▶  Compile"}
      </button>
    </div>
  );
}
