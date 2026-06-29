"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

interface Constraints {
  maxLatencyMs: string;
  maxPowerW: string;
  maxCostUsd: string;
  minAccuracy: string;
  carbonRegion: string;
  inferencesPerDay: string;
}

interface TargetResult {
  target: string;
  tokens_per_sec: number;
  latency_ms_per_token: number;
  power_watts: number;
  cost_usd_hardware: number;
  cost_usd_per_inference: number;
  carbon_gco2_per_inference: number;
  accuracy_delta: number;
  meets_constraints: boolean;
  sil_used: boolean;
  notes: string;
}

interface ComparisonReport {
  model_path: string;
  results: TargetResult[];
  recommended_target: string | null;
  pareto_front: string[];
  generated_at: string;
}

const TARGET_COLORS: Record<string, string> = {
  alloy: "text-accent-cyan",
  fusion: "text-accent-amber",
  element: "text-accent-green",
  cim: "#a78bfa",
  neuromorphic: "#f472b6",
  photonic: "#38bdf8",
};

const TARGET_BG: Record<string, string> = {
  alloy: "bg-accent-cyan/10 border-accent-cyan/40",
  fusion: "bg-accent-amber/10 border-accent-amber/40",
  element: "bg-accent-green/10 border-accent-green/40",
  cim: "bg-purple-500/10 border-purple-500/40",
  neuromorphic: "bg-pink-500/10 border-pink-500/40",
  photonic: "bg-sky-400/10 border-sky-400/40",
};

const CARBON_REGIONS = [
  { value: "global_avg", label: "Global avg" },
  { value: "us", label: "US" },
  { value: "eu-no", label: "EU Norway (hydro)" },
  { value: "eu-fr", label: "EU France" },
  { value: "eu-de", label: "EU Germany" },
  { value: "cn", label: "China" },
];

function normalize(vals: number[]): number[] {
  const mx = Math.max(...vals);
  if (mx === 0) return vals.map(() => 0);
  return vals.map((v) => v / mx);
}

function ScatterPlot({ results, pareto, recommended }: { results: TargetResult[]; pareto: string[]; recommended: string | null }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || results.length === 0) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;
    const pad = 48;

    ctx.clearRect(0, 0, W, H);

    const tpsVals = results.map((r) => r.tokens_per_sec);
    const latVals = results.map((r) => r.latency_ms_per_token);
    const maxTps = Math.max(...tpsVals);
    const maxLat = Math.max(...latVals);

    // Grid lines
    ctx.strokeStyle = "rgba(255,255,255,0.06)";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const x = pad + (i / 4) * (W - pad * 2);
      const y = pad + (i / 4) * (H - pad * 2);
      ctx.beginPath(); ctx.moveTo(x, pad); ctx.lineTo(x, H - pad); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(W - pad, y); ctx.stroke();
    }

    // Axis labels
    ctx.fillStyle = "rgba(255,255,255,0.4)";
    ctx.font = "10px monospace";
    ctx.textAlign = "center";
    ctx.fillText("Tokens/sec →", W / 2, H - 6);
    ctx.save();
    ctx.translate(12, H / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText("Latency ms ↑", 0, 0);
    ctx.restore();

    results.forEach((r) => {
      const x = pad + (r.tokens_per_sec / maxTps) * (W - pad * 2);
      const y = H - pad - (1 - r.latency_ms_per_token / maxLat) * (H - pad * 2);
      const radius = 6 + Math.log10(Math.max(r.tokens_per_sec, 1)) * 2;

      const isPareto = pareto.includes(r.target);
      const isRec = r.target === recommended;

      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fillStyle = isRec ? "rgba(0,255,200,0.7)" : isPareto ? "rgba(255,180,0,0.5)" : "rgba(255,255,255,0.2)";
      ctx.fill();
      if (isPareto || isRec) {
        ctx.strokeStyle = isRec ? "#00ffc8" : "#ffb400";
        ctx.lineWidth = isRec ? 2 : 1.5;
        ctx.stroke();
      }

      ctx.fillStyle = "rgba(255,255,255,0.9)";
      ctx.font = "bold 9px monospace";
      ctx.textAlign = "center";
      ctx.fillText(r.target.toUpperCase(), x, y - radius - 4);
    });
  }, [results, pareto, recommended]);

  return (
    <canvas
      ref={canvasRef}
      width={480}
      height={280}
      className="w-full rounded bg-bg-tertiary border border-border"
    />
  );
}

export default function ComparePage() {
  const [tptirPath, setTptirPath] = useState("");
  const [constraints, setConstraints] = useState<Constraints>({
    maxLatencyMs: "",
    maxPowerW: "",
    maxCostUsd: "",
    minAccuracy: "",
    carbonRegion: "global_avg",
    inferencesPerDay: "1000",
  });
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<ComparisonReport | null>(null);
  const [error, setError] = useState("");
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

  function updateConstraint(key: keyof Constraints, value: string) {
    setConstraints((c) => ({ ...c, [key]: value }));
  }

  async function runComparison() {
    setLoading(true);
    setError("");
    setReport(null);
    try {
      const body: Record<string, unknown> = { model_path: tptirPath };
      if (constraints.maxLatencyMs) body.max_latency_ms = parseFloat(constraints.maxLatencyMs);
      if (constraints.maxPowerW) body.max_power_w = parseFloat(constraints.maxPowerW);
      if (constraints.maxCostUsd) body.max_cost_usd = parseFloat(constraints.maxCostUsd);
      if (constraints.minAccuracy) body.min_accuracy = parseFloat(constraints.minAccuracy);
      body.carbon_region = constraints.carbonRegion;
      body.inferences_per_day = parseInt(constraints.inferencesPerDay, 10) || 1000;

      const res = await fetch(`${apiUrl}/api/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data: ComparisonReport = await res.json();
      setReport(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  const sortedResults = report
    ? [...report.results].sort((a, b) => b.tokens_per_sec - a.tokens_per_sec)
    : [];

  return (
    <div className="min-h-screen bg-bg-primary grid-bg p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-accent-cyan">Compare All Targets</h1>
            <p className="text-sm text-text-secondary mt-1">
              Run the same model across every hardware backend and find the optimal target for your constraints
            </p>
          </div>
          <Link href="/" className="text-xs text-text-secondary hover:text-text-primary">
            ← Dashboard
          </Link>
        </div>

        {/* Config panel */}
        <div className="stat-card space-y-4">
          <h3 className="text-sm font-bold text-accent-amber">MODEL & CONSTRAINTS</h3>
          <div>
            <label className="text-xs text-text-secondary block mb-1">TPT-IR path or model identifier</label>
            <input
              type="text"
              value={tptirPath}
              onChange={(e) => setTptirPath(e.target.value)}
              placeholder="/path/to/model.tptir"
              className="w-full bg-bg-tertiary border border-border rounded px-3 py-2 text-sm font-mono text-text-primary focus:outline-none focus:border-accent-cyan"
            />
          </div>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            {[
              { key: "maxLatencyMs", label: "Max latency (ms/token)" },
              { key: "maxPowerW", label: "Max power (W)" },
              { key: "maxCostUsd", label: "Max hardware cost (USD)" },
              { key: "minAccuracy", label: "Min accuracy (0–1)" },
              { key: "inferencesPerDay", label: "Inferences/day" },
            ].map(({ key, label }) => (
              <div key={key}>
                <label className="text-xs text-text-secondary block mb-1">{label}</label>
                <input
                  type="number"
                  value={constraints[key as keyof Constraints]}
                  onChange={(e) => updateConstraint(key as keyof Constraints, e.target.value)}
                  placeholder="any"
                  className="w-full bg-bg-tertiary border border-border rounded px-3 py-2 text-sm font-mono text-text-primary focus:outline-none focus:border-accent-cyan"
                />
              </div>
            ))}
            <div>
              <label className="text-xs text-text-secondary block mb-1">Carbon region</label>
              <select
                value={constraints.carbonRegion}
                onChange={(e) => updateConstraint("carbonRegion", e.target.value)}
                className="w-full bg-bg-tertiary border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-cyan"
              >
                {CARBON_REGIONS.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </div>
          </div>
          <button
            onClick={runComparison}
            disabled={loading || !tptirPath}
            className="px-6 py-2.5 rounded bg-accent-cyan/20 text-accent-cyan text-sm border border-accent-cyan/50 hover:bg-accent-cyan/30 disabled:opacity-40 transition-colors"
          >
            {loading ? "Running comparison..." : "Compare All Targets"}
          </button>
          {error && <p className="text-xs text-accent-red">{error}</p>}
        </div>

        {/* Results */}
        {report && (
          <>
            {report.recommended_target && (
              <div className="flex items-center gap-3 px-4 py-3 rounded bg-accent-cyan/10 border border-accent-cyan/30">
                <span className="text-accent-cyan text-lg">★</span>
                <div>
                  <div className="text-sm font-bold text-accent-cyan">
                    Recommended: {report.recommended_target.toUpperCase()}
                  </div>
                  <div className="text-xs text-text-secondary">
                    Best balance of throughput, latency, power, and cost for your constraints
                  </div>
                </div>
                <Link
                  href={`/cloud?target=${report.recommended_target}`}
                  className="ml-auto px-4 py-1.5 rounded bg-accent-cyan text-bg-primary text-xs font-bold hover:opacity-90"
                >
                  Compile →
                </Link>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Scatter plot */}
              <div className="stat-card">
                <h3 className="text-xs font-bold text-accent-amber mb-3">THROUGHPUT vs LATENCY</h3>
                <ScatterPlot
                  results={sortedResults}
                  pareto={report.pareto_front}
                  recommended={report.recommended_target}
                />
                <div className="flex gap-4 mt-2 text-[10px] text-text-secondary">
                  <span className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-full border-2 border-accent-cyan bg-accent-cyan/50" /> Recommended</span>
                  <span className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-full border-2 border-accent-amber bg-accent-amber/30" /> Pareto front</span>
                </div>
              </div>

              {/* Target cards */}
              <div className="space-y-2">
                {sortedResults.map((r) => {
                  const isRec = r.target === report.recommended_target;
                  const isPareto = report.pareto_front.includes(r.target);
                  return (
                    <div
                      key={r.target}
                      className={`p-3 rounded border ${TARGET_BG[r.target] ?? "bg-bg-tertiary border-border"} ${isRec ? "ring-1 ring-accent-cyan" : ""}`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className={`text-xs font-bold ${TARGET_COLORS[r.target] ?? "text-text-primary"}`}>
                            {r.target.toUpperCase()}
                          </span>
                          {isRec && <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent-cyan/20 text-accent-cyan">★ RECOMMENDED</span>}
                          {isPareto && !isRec && <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent-amber/20 text-accent-amber">PARETO</span>}
                          {!r.meets_constraints && <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent-red/20 text-accent-red">FAILS CONSTRAINTS</span>}
                        </div>
                        <Link
                          href={`/cloud?target=${r.target}`}
                          className="text-[10px] px-2 py-0.5 rounded bg-bg-primary text-text-secondary hover:text-text-primary border border-border"
                        >
                          Compile
                        </Link>
                      </div>
                      <div className="grid grid-cols-3 gap-x-4 gap-y-1 text-[10px]">
                        <div><span className="text-text-secondary">TPS</span><div className="font-mono font-bold text-text-primary">{r.tokens_per_sec.toFixed(1)}</div></div>
                        <div><span className="text-text-secondary">Latency</span><div className="font-mono font-bold text-text-primary">{r.latency_ms_per_token.toFixed(1)} ms</div></div>
                        <div><span className="text-text-secondary">Power</span><div className="font-mono font-bold text-text-primary">{r.power_watts.toFixed(1)} W</div></div>
                        <div><span className="text-text-secondary">HW Cost</span><div className="font-mono font-bold text-text-primary">${r.cost_usd_hardware.toLocaleString()}</div></div>
                        <div><span className="text-text-secondary">Cost/inf</span><div className="font-mono font-bold text-text-primary">${r.cost_usd_per_inference.toFixed(6)}</div></div>
                        <div><span className="text-text-secondary">Carbon</span><div className="font-mono font-bold text-text-primary">{r.carbon_gco2_per_inference.toFixed(6)} g</div></div>
                      </div>
                      {r.accuracy_delta !== 0 && (
                        <div className={`text-[10px] mt-1 ${r.accuracy_delta < 0 ? "text-accent-amber" : "text-accent-green"}`}>
                          Accuracy delta: {(r.accuracy_delta * 100).toFixed(1)}%
                        </div>
                      )}
                      {r.notes && <div className="text-[10px] text-text-secondary/60 mt-1">{r.notes}</div>}
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="text-[10px] text-text-secondary text-right">
              Generated: {report.generated_at} · {report.results.filter((r) => r.sil_used).length} SiL runs, {report.results.filter((r) => !r.sil_used).length} profile-based estimates
            </div>
          </>
        )}
      </div>
    </div>
  );
}
