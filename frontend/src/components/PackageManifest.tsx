"use client";

import { useState } from "react";

interface PackageManifest {
  format_version: string;
  model_name: string;
  source_sha256: string;
  targets: TargetEntry[];
  preflight?: PreflightReport;
  quant_profile?: QuantProfile;
  mosaic_partition?: MosaicPartition;
}

interface TargetEntry {
  name: string;
  artifacts: Artifact[];
}

interface Artifact {
  path: string;
  sha256: string;
  size_bytes: number;
}

interface PreflightReport {
  compatibility_score: number;
  passes: number;
  warnings: number;
  failures: number;
}

interface QuantProfile {
  name: string;
  weight_bits: number;
  activation_bits: number;
  estimated_accuracy_loss: number;
}

interface MosaicPartition {
  assignments: { layer_id: number; target: string }[];
}

function StatusBadge({ score }: { score: number }) {
  const color = score >= 0.8 ? "text-accent-green" : score >= 0.5 ? "text-accent-amber" : "text-accent-red";
  const label = score >= 0.8 ? "READY" : score >= 0.5 ? "PARTIAL" : "NOT READY";
  return (
    <span className={`text-xs font-bold ${color}`}>{label} ({(score * 100).toFixed(0)}%)</span>
  );
}

export function PackageManifestViewer({ manifest }: { manifest?: PackageManifest }) {
  const data = manifest || {
    format_version: "1.0.0",
    model_name: "tinyllama-1.1b",
    source_sha256: "a1b2c3d4e5f6...",
    targets: [
      { name: "alloy", artifacts: [
        { path: "firmware/node_0.c", sha256: "abc123", size_bytes: 1024 },
        { path: "firmware/topology.json", sha256: "def456", size_bytes: 256 },
      ]},
      { name: "fusion", artifacts: [
        { path: "rtl/tpt_mac_array.v", sha256: "789abc", size_bytes: 4096 },
        { path: "rtl/board.json", sha256: "def012", size_bytes: 128 },
      ]},
      { name: "element", artifacts: [
        { path: "netlist.spice", sha256: "345678", size_bytes: 2048 },
        { path: "confidence.json", sha256: "9abcdef", size_bytes: 64 },
      ]},
    ],
    preflight: { compatibility_score: 0.92, passes: 45, warnings: 3, failures: 1 },
    quant_profile: { name: "INT8 Mixed", weight_bits: 8, activation_bits: 8, estimated_accuracy_loss: 0.02 },
    mosaic_partition: { assignments: Array.from({ length: 12 }, (_, i) => ({ layer_id: i, target: ["fpga", "swarm", "analog"][i % 3] })) },
  };

  const [activeTab, setActiveTab] = useState<"overview" | "targets" | "preflight">("overview");

  const totalArtifacts = data.targets.reduce((sum, t) => sum + t.artifacts.length, 0);
  const totalSize = data.targets.reduce(
    (sum, t) => sum + t.artifacts.reduce((s, a) => s + a.size_bytes, 0), 0
  );

  return (
    <div className="stat-card space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-accent-cyan">PACKAGE MANIFEST</h3>
        <StatusBadge score={data.preflight?.compatibility_score || 0} />
      </div>

      <div className="flex gap-1">
        {(["overview", "targets", "preflight"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-2 py-1 rounded text-[10px] ${
              activeTab === tab
                ? "bg-accent-cyan/20 text-accent-cyan"
                : "bg-bg-tertiary text-text-secondary"
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {activeTab === "overview" && (
        <div className="space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-text-secondary">Model</span>
            <span className="text-accent-cyan font-mono">{data.model_name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Format</span>
            <span>v{data.format_version}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Targets</span>
            <span>{data.targets.map((t) => t.name).join(", ")}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Artifacts</span>
            <span>{totalArtifacts}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Total Size</span>
            <span>{(totalSize / 1024).toFixed(1)} KB</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">SHA-256</span>
            <span className="font-mono text-[10px]">{data.source_sha256}</span>
          </div>
          {data.quant_profile && (
            <div className="flex justify-between">
              <span className="text-text-secondary">Quantization</span>
              <span className="text-accent-amber">{data.quant_profile.name}</span>
            </div>
          )}
        </div>
      )}

      {activeTab === "targets" && (
        <div className="space-y-3">
          {data.targets.map((target) => (
            <div key={target.name} className="bg-bg-tertiary rounded p-2">
              <div className="text-xs font-bold text-accent-cyan mb-1">{target.name.toUpperCase()}</div>
              <div className="space-y-1">
                {target.artifacts.map((art) => (
                  <div key={art.path} className="flex justify-between text-[10px]">
                    <span className="text-text-secondary font-mono">{art.path}</span>
                    <span>{(art.size_bytes / 1024).toFixed(1)} KB</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === "preflight" && data.preflight && (
        <div className="space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-text-secondary">Score</span>
            <span className="text-accent-green">{(data.preflight.compatibility_score * 100).toFixed(0)}%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Passes</span>
            <span className="text-accent-green">{data.preflight.passes}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Warnings</span>
            <span className="text-accent-amber">{data.preflight.warnings}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Failures</span>
            <span className="text-accent-red">{data.preflight.failures}</span>
          </div>
          {data.mosaic_partition && (
            <div className="mt-2">
              <div className="text-text-secondary mb-1">Partition Map</div>
              <div className="flex gap-1 flex-wrap">
                {data.mosaic_partition.assignments.map((a) => (
                  <span
                    key={a.layer_id}
                    className={`px-1 py-0.5 rounded text-[8px] ${
                      a.target === "fpga" ? "bg-accent-cyan/20 text-accent-cyan" :
                      a.target === "swarm" ? "bg-accent-amber/20 text-accent-amber" :
                      "bg-accent-green/20 text-accent-green"
                    }`}
                  >
                    L{a.layer_id}→{a.target.slice(0, 3)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
