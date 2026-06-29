"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useToast } from "@/components/Toast";
import { ErrorBoundary } from "@/components/ErrorBoundary";

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

const ACCEPTED_EXTENSIONS = [".gguf", ".pt", ".onnx", ".tflite", ".safetensors"];
const MAX_FILE_BYTES = 10 * 1024 * 1024 * 1024; // 10 GB

const targetInfo: Record<string, { label: string; description: string; icon: string }> = {
  alloy: { label: "Swarm", description: "ESP32/RP2040 mesh network", icon: "\u2B21" },
  fusion: { label: "FPGA", description: "Xilinx Alveo with HBM", icon: "\u25A3" },
  element: { label: "Analog", description: "Custom PCB circuit", icon: "\u25CE" },
  silicon: { label: "CIM", description: "Compute-in-memory array", icon: "\u25A6" },
  pulse: { label: "Neuro", description: "Spiking neural network", icon: "\u26A1" },
  photon: { label: "Photonic", description: "MZI mesh (experimental)", icon: "\u2600" },
};

function validateFile(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext))) {
    return `Unsupported file type. Accepted: ${ACCEPTED_EXTENSIONS.join(", ")}`;
  }
  if (file.size > MAX_FILE_BYTES) {
    return "File exceeds 10 GB limit.";
  }
  return null;
}

export default function CloudPage() {
  const { toast } = useToast();
  const [uploading, setUploading] = useState(false);
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

  useEffect(() => {
    const fetchJobs = () => {
      fetch(`${apiUrl}/api/jobs`)
        .then((r) => r.json())
        .then((data: Job[]) => setJobs(data))
        .catch(() => {});
    };
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, [apiUrl]);

  const handleFile = useCallback((file: File) => {
    const err = validateFile(file);
    if (err) { setFileError(err); setSelectedFile(null); return; }
    setFileError(null);
    setSelectedFile(file);
  }, []);

  const handleStartCompilation = useCallback(async () => {
    if (!selectedFile || !selectedTarget) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("model", selectedFile);
      formData.append("target", selectedTarget);
      const res = await fetch(`${apiUrl}/api/jobs`, { method: "POST", body: formData });
      if (res.ok) {
        const job: Job = await res.json();
        setJobs((prev) => [job, ...prev]);
        toast("Compilation job submitted", "success");
      } else {
        toast(`Job submission failed: ${res.statusText}`, "error");
      }
    } catch {
      toast("Backend unreachable — job not submitted", "error");
    }
    setUploading(false);
    setSelectedFile(null);
  }, [selectedFile, selectedTarget, apiUrl]);

  const statusColors: Record<string, string> = {
    complete: "bg-accent-green",
    running: "bg-accent-cyan animate-pulse",
    pending: "bg-text-secondary",
    failed: "bg-accent-red",
  };

  return (
    <ErrorBoundary>
    <div className="min-h-screen bg-bg-primary grid-bg p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-accent-cyan">TPT Crucible Cloud</h1>
          <p className="text-sm text-text-secondary mt-1">Upload models, compile for custom hardware, download packages</p>
        </div>

        <div className="stat-card">
          <h3 className="text-sm font-bold text-accent-amber mb-3">UPLOAD MODEL</h3>
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_EXTENSIONS.join(",")}
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
              dragOver ? "border-accent-cyan bg-accent-cyan/5" : "border-border hover:border-accent-cyan/50"
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault(); setDragOver(false);
              const file = e.dataTransfer.files[0];
              if (file) handleFile(file);
            }}
            onClick={() => fileInputRef.current?.click()}
          >
            {uploading ? (
              <div className="space-y-2">
                <div className="text-accent-cyan animate-pulse">Submitting job...</div>
              </div>
            ) : selectedFile ? (
              <div className="space-y-1">
                <div className="text-sm text-accent-green">{selectedFile.name}</div>
                <div className="text-xs text-text-secondary">{(selectedFile.size / 1_000_000).toFixed(1)} MB \u2014 click to change</div>
              </div>
            ) : (
              <>
                <div className="text-3xl mb-2 text-text-secondary">{"\u2191"}</div>
                <div className="text-sm text-text-primary">Drag and drop model file here</div>
                <div className="text-xs text-text-secondary mt-1">Supports {ACCEPTED_EXTENSIONS.join(", ")}</div>
                <div className="text-[10px] text-text-secondary mt-2">or click to browse</div>
              </>
            )}
          </div>
          {fileError && <p className="text-xs text-accent-red mt-2">{fileError}</p>}
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
            onClick={handleStartCompilation}
            disabled={!selectedTarget || !selectedFile || uploading}
            className={`px-6 py-2.5 rounded font-bold text-sm transition-colors ${
              selectedTarget && selectedFile && !uploading
                ? "bg-accent-cyan text-bg-primary hover:bg-accent-cyan/90"
                : "bg-bg-tertiary text-text-secondary cursor-not-allowed"
            }`}
          >
            {uploading ? "Submitting..." : "Start Compilation"}
          </button>
        </div>

        <div className="stat-card">
          <h3 className="text-sm font-bold text-accent-amber mb-3">COMPILATION JOBS</h3>
          <div className="space-y-2">
            {jobs.length === 0 && (
              <p className="text-xs text-text-secondary text-center py-4">No jobs yet. Submit a compilation job above.</p>
            )}
            {jobs.map((job) => (
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
    </ErrorBoundary>
  );
}
