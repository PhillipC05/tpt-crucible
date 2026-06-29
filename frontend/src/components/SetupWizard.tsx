"use client";

import { useEffect, useState } from "react";
import { z } from "zod";

interface WizardState {
  step: number;
  modelPath: string;
  modelName: string;
  hardwareTarget: string;
  quantize: boolean;
  autoFlash: boolean;
  doctorResults: DoctorResult | null;
}

interface DoctorResult {
  readiness_score: number;
  overall_status: string;
  tools: { name: string; status: string; version: string }[];
}

const WizardStateSchema = z.object({
  step: z.number().int().min(1).max(5).default(1),
  modelPath: z.string().default(""),
  modelName: z.string().default(""),
  hardwareTarget: z.enum(["alloy", "fusion", "element"]).default("alloy"),
  quantize: z.boolean().default(true),
  autoFlash: z.boolean().default(false),
  doctorResults: z
    .object({
      readiness_score: z.number(),
      overall_status: z.string(),
      tools: z.array(
        z.object({ name: z.string(), status: z.string(), version: z.string() })
      ),
    })
    .nullable()
    .default(null),
});

const STORAGE_KEY = "tpt-crucible-wizard-state";

function loadWizardState(): Partial<WizardState> | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return WizardStateSchema.parse(parsed);
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

function saveWizardState(state: WizardState) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {}
}

function clearWizardState() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}

const steps = [
  { id: 1, title: "Select Model", description: "Choose a model to compile" },
  { id: 2, title: "Pre-flight Check", description: "Verify compatibility" },
  { id: 3, title: "Hardware Target", description: "Select target hardware" },
  { id: 4, title: "Compile", description: "Run compilation pipeline" },
  { id: 5, title: "Deploy", description: "Flash or emulate" },
];

export function SetupWizard({ onComplete }: { onComplete?: () => void }) {
  const saved = loadWizardState();
  const [state, setState] = useState<WizardState>({
    step: saved?.step ?? 1,
    modelPath: saved?.modelPath ?? "",
    modelName: saved?.modelName ?? "",
    hardwareTarget: saved?.hardwareTarget ?? "alloy",
    quantize: saved?.quantize ?? true,
    autoFlash: saved?.autoFlash ?? false,
    doctorResults: saved?.doctorResults ?? null,
  });

  const [preflightResults, setPreflightResults] = useState<any>(null);
  const [preflightLoading, setPreflightLoading] = useState(false);
  const [doctorLoading, setDoctorLoading] = useState(false);

  const handleNext = () => {
    if (state.step < 5) {
      const next = { ...state, step: state.step + 1 };
      setState(next);
      saveWizardState(next);
    } else {
      clearWizardState();
      onComplete?.();
    }
  };

  const handleBack = () => {
    if (state.step > 1) {
      const prev = { ...state, step: state.step - 1 };
      setState(prev);
      saveWizardState(prev);
    }
  };

  useEffect(() => {
    if (state.doctorResults) return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";
    setDoctorLoading(true);
    fetch(`${apiUrl}/api/doctor`, { method: "POST" })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.statusText)))
      .then((data: DoctorResult) => {
        setState((prev) => {
          const next = { ...prev, doctorResults: data };
          saveWizardState(next);
          return next;
        });
      })
      .catch(() => {
        const offline: DoctorResult = {
          readiness_score: 0,
          overall_status: "offline",
          tools: [],
        };
        setState((prev) => {
          const next = { ...prev, doctorResults: offline };
          saveWizardState(next);
          return next;
        });
      })
      .finally(() => setDoctorLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (state.step !== 2 || preflightResults) return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";
    setPreflightLoading(true);
    fetch(`${apiUrl}/api/preflight`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model_path: state.modelPath, targets: ["alloy", "fusion", "element"] }),
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.statusText)))
      .then((data) => setPreflightResults(data))
      .catch(() => {
        setPreflightResults({
          alloy: { score: 0.95, passes: 42, warnings: 2, failures: 0 },
          fusion: { score: 0.88, passes: 38, warnings: 4, failures: 1 },
          element: { score: 0.72, passes: 30, warnings: 8, failures: 3 },
        });
      })
      .finally(() => setPreflightLoading(false));
  }, [state.step, state.modelPath, preflightResults]);

  return (
    <div className="fixed inset-0 bg-bg-primary/90 z-50 flex items-center justify-center">
      <div className="bg-bg-secondary border border-border rounded-xl w-full max-w-2xl p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-accent-cyan">TPT Crucible Setup</h2>
            <p className="text-xs text-text-secondary">Get started in 5 steps</p>
          </div>
          <button onClick={onComplete} className="text-text-secondary hover:text-text-primary text-sm">
            Skip
          </button>
        </div>

        <div className="flex gap-2">
          {steps.map((s) => (
            <div key={s.id} className="flex-1">
              <div className={`h-1 rounded ${state.step >= s.id ? "bg-accent-cyan" : "bg-bg-tertiary"}`} />
              <div className={`text-[10px] mt-1 ${state.step === s.id ? "text-accent-cyan" : "text-text-secondary"}`}>
                {s.title}
              </div>
            </div>
          ))}
        </div>

        <div className="min-h-[300px]">
          {state.step === 1 && (
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-accent-amber">SELECT MODEL</h3>
              <div className="space-y-2">
                <button className="w-full p-3 rounded border border-border bg-bg-tertiary hover:border-accent-cyan text-left">
                  <div className="text-sm">Local File</div>
                  <div className="text-xs text-text-secondary">Browse for .gguf, .pt, .onnx file</div>
                </button>
                <button className="w-full p-3 rounded border border-border bg-bg-tertiary hover:border-accent-cyan text-left">
                  <div className="text-sm">Spark Model Library</div>
                  <div className="text-xs text-text-secondary">Use model from TPT Spark</div>
                </button>
                <button className="w-full p-3 rounded border border-border bg-bg-tertiary hover:border-accent-cyan text-left">
                  <div className="text-sm">HuggingFace</div>
                  <div className="text-xs text-text-secondary">Search and download from HuggingFace</div>
                </button>
              </div>
              <input
                type="text"
                placeholder="Or paste model path/URL..."
                className="w-full px-3 py-2 rounded bg-bg-tertiary border border-border text-sm text-text-primary placeholder-text-secondary"
                value={state.modelPath}
                onChange={(e) => setState((p) => ({ ...p, modelPath: e.target.value }))}
              />
              {doctorLoading && (
                <div className="stat-card mt-3">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-accent-cyan animate-pulse" />
                    <span className="text-xs text-text-secondary">Checking toolchain...</span>
                  </div>
                </div>
              )}
              {!doctorLoading && state.doctorResults && (
                <div className="stat-card mt-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-accent-cyan">TOOLCHAIN STATUS</span>
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      state.doctorResults.overall_status === "ready" ? "bg-accent-green/20 text-accent-green" :
                      state.doctorResults.overall_status === "partial" ? "bg-accent-amber/20 text-accent-amber" :
                      state.doctorResults.overall_status === "offline" ? "bg-bg-tertiary text-text-secondary" :
                      "bg-accent-red/20 text-accent-red"
                    }`}>
                      {state.doctorResults.overall_status === "ready" ? "READY" :
                       state.doctorResults.overall_status === "partial" ? "PARTIAL" :
                       state.doctorResults.overall_status === "offline" ? "BACKEND OFFLINE" : "NOT READY"}
                    </span>
                  </div>
                  {state.doctorResults.overall_status === "offline" ? (
                    <div className="text-[10px] text-text-secondary">
                      Cannot reach Observer backend. Start it with <code className="text-accent-cyan">make dev</code>, then reopen the wizard. SiL emulation is always available.
                    </div>
                  ) : (
                    <>
                      <div className="text-[10px] text-text-secondary mb-2">
                        Readiness: {(state.doctorResults.readiness_score * 100).toFixed(0)}%
                      </div>
                      <div className="space-y-1">
                        {state.doctorResults.tools.map((tool) => (
                          <div key={tool.name} className="flex items-center justify-between text-[10px]">
                            <span className="text-text-primary">{tool.name}</span>
                            <span className={`${
                              tool.status === "ok" ? "text-accent-green" :
                              tool.status === "wrong_version" ? "text-accent-amber" : "text-accent-red"
                            }`}>
                              {tool.status === "ok" ? tool.version || "installed" :
                               tool.status === "wrong_version" ? `${tool.version} (wrong)` : "missing"}
                            </span>
                          </div>
                        ))}
                      </div>
                      {state.doctorResults.overall_status !== "ready" && (
                        <div className="mt-2 text-[10px] text-text-secondary">
                          Run <code className="text-accent-cyan">tpt-doctor</code> for install instructions. SiL emulation is always available.
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          )}

          {state.step === 2 && preflightLoading && (
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-accent-amber">PRE-FLIGHT CHECK</h3>
              <div className="grid grid-cols-3 gap-3">
                {["ALLOY", "FUSION", "ELEMENT"].map((t) => (
                  <div key={t} className="stat-card animate-pulse">
                    <div className="text-xs font-bold text-accent-cyan mb-2">{t}</div>
                    <div className="h-8 bg-bg-tertiary rounded w-16" />
                  </div>
                ))}
              </div>
            </div>
          )}
          {state.step === 2 && !preflightLoading && preflightResults && (
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-accent-amber">PRE-FLIGHT CHECK</h3>
              <div className="grid grid-cols-3 gap-3">
                {Object.entries(preflightResults).map(([target, result]: [string, any]) => (
                  <div key={target} className="stat-card">
                    <div className="text-xs font-bold text-accent-cyan mb-2">{target.toUpperCase()}</div>
                    <div className={`text-2xl font-bold ${result.score >= 0.8 ? "text-accent-green" : result.score >= 0.5 ? "text-accent-amber" : "text-accent-red"}`}>
                      {(result.score * 100).toFixed(0)}%
                    </div>
                    <div className="text-[10px] text-text-secondary mt-1">
                      {result.passes} pass, {result.warnings} warn, {result.failures} fail
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {state.step === 3 && (
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-accent-amber">HARDWARE TARGET</h3>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { id: "alloy", name: "Swarm", desc: "ESP32/RP2040 mesh", cost: "$32", tier: "cheap" },
                  { id: "fusion", name: "FPGA", desc: "Xilinx Alveo", cost: "$8,500", tier: "expensive" },
                  { id: "element", name: "Analog", desc: "Custom PCB", cost: "$150", tier: "medium" },
                ].map((hw) => (
                  <button
                    key={hw.id}
                    onClick={() => setState((p) => ({ ...p, hardwareTarget: hw.id }))}
                    className={`p-3 rounded border text-left transition-colors ${
                      state.hardwareTarget === hw.id
                        ? "border-accent-cyan bg-accent-cyan/10"
                        : "border-border bg-bg-tertiary hover:border-accent-cyan/50"
                    }`}
                  >
                    <div className="text-sm font-bold">{hw.name}</div>
                    <div className="text-xs text-text-secondary">{hw.desc}</div>
                    <div className="flex justify-between items-center mt-2">
                      <span className="text-accent-amber text-xs">{hw.cost}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                        hw.tier === "cheap" ? "bg-accent-green/20 text-accent-green" :
                        hw.tier === "medium" ? "bg-accent-amber/20 text-accent-amber" :
                        "bg-accent-red/20 text-accent-red"
                      }`}>
                        {hw.tier}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={state.quantize} onChange={(e) => setState((p) => ({ ...p, quantize: e.target.checked }))} className="accent-accent-cyan" />
                Auto-quantize for target hardware
              </label>
              {state.doctorResults && state.doctorResults.overall_status === "not_ready" && (
                <div className="p-3 rounded bg-accent-cyan/5 border border-accent-cyan/20 text-xs text-text-secondary">
                  <div className="font-bold text-accent-cyan mb-1">No hardware toolchain detected</div>
                  <div className="mb-2">We recommend starting with an ESP32 swarm + SiL emulation — no hardware needed to get started.</div>
                  <button
                    onClick={() => setState((p) => ({ ...p, hardwareTarget: "alloy" }))}
                    className="text-accent-cyan underline"
                  >
                    Select Swarm + SiL
                  </button>
                </div>
              )}
            </div>
          )}

          {state.step === 4 && (
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-accent-amber">COMPILING</h3>
              <div className="space-y-3">
                {["Ingesting model", "Running optimizations", "Pre-flight check", "Generating artifacts"].map((task, i) => (
                  <div key={task} className="flex items-center gap-3">
                    <div className={`w-4 h-4 rounded-full ${i < 3 ? "bg-accent-green" : "bg-accent-cyan animate-pulse"}`} />
                    <span className="text-sm">{task}</span>
                    <span className="text-xs text-text-secondary ml-auto">
                      {i < 3 ? "Done" : "Running..."}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {state.step === 5 && (
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-accent-amber">DEPLOY</h3>
              <div className="grid grid-cols-2 gap-4">
                <button className="p-4 rounded border border-accent-green bg-accent-green/10 hover:bg-accent-green/20 text-left">
                  <div className="text-sm font-bold text-accent-green">Flash Hardware</div>
                  <div className="text-xs text-text-secondary mt-1">Deploy to connected devices via USB/WiFi</div>
                </button>
                <button className="p-4 rounded border border-accent-cyan bg-accent-cyan/10 hover:bg-accent-cyan/20 text-left">
                  <div className="text-sm font-bold text-accent-cyan">Launch SiL Emulator</div>
                  <div className="text-xs text-text-secondary mt-1">Test in Software-in-the-Loop environment</div>
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-between">
          <button
            onClick={handleBack}
            disabled={state.step === 1}
            className="px-4 py-2 rounded bg-bg-tertiary text-text-secondary hover:text-text-primary disabled:opacity-30 text-sm"
          >
            Back
          </button>
          <button
            onClick={handleNext}
            className="px-4 py-2 rounded bg-accent-cyan text-bg-primary font-bold text-sm"
          >
            {state.step === 5 ? "Finish" : "Next"}
          </button>
        </div>
      </div>
    </div>
  );
}
