"use client";

import { useState } from "react";

interface Job {
  id: string;
  model_name: string;
  target: string;
  status: string;
  progress: number;
  created_at: string;
  estimated_time?: string;
  result_url?: string;
}

const sampleJobs: Job[] = [
  { id: "job_001", model_name: "tinyllama-1.1b", target: "alloy", status: "complete", progress: 100, created_at: "14:32:01", estimated_time: "2m 15s", result_url: "/download/job_001.tptpkg" },
  { id: "job_002", model_name: "llama2-7b", target: "fusion", status: "running", progress: 67, created_at: "14:31:45", estimated_time: "~45m remaining" },
  { id: "job_003", model_name: "mistral-7b", target: "element", status: "pending", progress: 0, created_at: "14:30:22" },
  { id: "job_004", model_name: "qwen2.5-3b", target: "alloy", status: "failed", progress: 34, created_at: "14:29:10" },
];

const targetInfo: Record<string, { label: string; description: string; icon: string }> = {
  alloy: { label: "Swarm", description: "ESP32/RP2040 mesh network", icon: "\u2B21" },
  fusion: { label: "FPGA", description: "Xilinx Alveo with HBM", icon: "\u25A3" },
  element: { label: "Analog", description: "Custom PCB circuit", icon: "\u25CE" },
  silicon: { label: "CIM", description: "Compute-in-memory array", icon: "\u25A6" },
  pulse: { label: "Neuro", description: "Spiking neural network", icon: "\u26A1" },
  photon: { label: "Photonic", description: "MZI mesh (experimental)", icon: "\u2600" },
};

export default function CloudPage() {
  const [uploading, setUploading] = useState(false);
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleUpload = () => {
    setUploading(true);
    setTimeout(() => setUploading(false), 2000);
  };

  const statusColors: Record<string, string> = {
    complete: "bg-accent-green",
    running: "bg-accent-cyan animate-pulse",
    pending: "bg-text-secondary",
    failed: "bg-accent-red",
  };

  return (
    <div className="min-h-screen bg-bg-primary grid-bg p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-accent-cyan">TPT Crucible Cloud</h1>
          <p className="text-sm text-text-secondary mt-1">Upload models, compile for custom hardware, download packages</p>
        </div>

        <div className="stat-card">
          <h3 className="text-sm font-bold text-accent-amber mb-3">UPLOAD MODEL</h3>
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
              dragOver ? "border-accent-cyan bg-accent-cyan/5" : "border-border hover:border-accent-cyan/50"
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => { e.preventDefault(); setDragOver(false); handleUpload(); }}
            onClick={handleUpload}
          >
            {uploading ? (
              <div className="space-y-2">
                <div className="text-accent-cyan animate-pulse">Uploading...</div>
                <div className="w-48 h-1.5 bg-bg-tertiary rounded-full mx-auto overflow-hidden">
                  <div className="h-full bg-accent-cyan rounded-full animate-pulse" style={{ width: "60%" }} />
                </div>
              </div>
            ) : (
              <>
                <div className="text-3xl mb-2 text-text-secondary">\u2191</div>
                <div className="text-sm text-text-primary">Drag and drop model file here</div>
                <div className="text-xs text-text-secondary mt-1">Supports .gguf, .pt, .onnx, .safetensors</div>
                <div className="text-[10px] text-text-secondary mt-2">or click to browse</div>
              </>
            )}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-bold text-accent-amber mb-3">SELECT TARGET HARDWARE</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(targetInfo).map(([key, info]) => (
              <button
                key={key}
                onClick={() => setSelectedTarget(key)}
                className={`stat-card text-left transition-all ${
                  selectedTarget === key
                    ? "border-accent-cyan glow-cyan"
                    : "hover:border-accent-cyan/30"
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg">{info.icon}</span>
                  <span className="text-sm font-bold text-accent-cyan">{info.label}</span>
                  {key === "photon" && (
                    <span className="text-[8px] px-1 py-0.5 rounded bg-accent-amber/20 text-accent-amber">EXP</span>
                  )}
                </div>
                <div className="text-xs text-text-secondary">{info.description}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleUpload}
            disabled={!selectedTarget || uploading}
            className={`px-6 py-2.5 rounded font-bold text-sm transition-colors ${
              selectedTarget && !uploading
                ? "bg-accent-cyan text-bg-primary hover:bg-accent-cyan/90"
                : "bg-bg-tertiary text-text-secondary cursor-not-allowed"
            }`}
          >
            {uploading ? "Compiling..." : "Start Compilation"}
          </button>
          <button className="px-4 py-2.5 rounded bg-bg-tertiary text-text-secondary hover:text-text-primary text-sm border border-border">
            Browse Packages
          </button>
        </div>

        <div className="stat-card">
          <h3 className="text-sm font-bold text-accent-amber mb-3">COMPILATION JOBS</h3>
          <div className="space-y-2">
            {sampleJobs.map((job) => (
              <div key={job.id} className="flex items-center gap-3 p-3 rounded bg-bg-tertiary hover:bg-bg-primary transition-colors">
                <div className={`w-2.5 h-2.5 rounded-full ${statusColors[job.status]}`} />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-mono text-text-primary">{job.model_name}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-bg-primary text-text-secondary">{job.target}</span>
                  </div>
                  <div className="text-[10px] text-text-secondary mt-0.5">
                    {job.created_at} {job.estimated_time ? `\u2022 ${job.estimated_time}` : ""}
                  </div>
                </div>
                {job.status === "complete" && job.result_url && (
                  <a
                    href={job.result_url}
                    className="px-3 py-1 rounded bg-accent-green/20 text-accent-green text-xs hover:bg-accent-green/30"
                  >
                    Download
                  </a>
                )}
                {job.status === "running" && (
                  <div className="w-20">
                    <div className="h-1.5 bg-bg-primary rounded-full overflow-hidden">
                      <div className="h-full bg-accent-cyan rounded-full" style={{ width: `${job.progress}%` }} />
                    </div>
                    <div className="text-[10px] text-text-secondary text-right mt-0.5">{job.progress}%</div>
                  </div>
                )}
                {job.status === "failed" && (
                  <span className="text-[10px] text-accent-red">Failed</span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
