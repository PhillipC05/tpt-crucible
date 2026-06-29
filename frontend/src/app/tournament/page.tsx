"use client";

import { useCallback, useRef, useState } from "react";
import Link from "next/link";
import { ErrorBoundary } from "@/components/ErrorBoundary";

interface TournamentConstraints {
  maxLatencyMs: string;
  maxPowerW: string;
  maxCostUsd: string;
  minAccuracy: string;
  targets: string[];
  quantizationSchemes: string[];
  synthesisModes: string[];
  nodeCountMin: string;
  nodeCountMax: string;
}

interface ParetoPoint {
  target: string;
  quant_scheme: string;
  synthesis_mode: string;
  node_count: number;
  tokens_per_sec: number;
  latency_ms: number;
  power_watts: number;
  cost_usd: number;
  accuracy_delta: number;
  score: number;
  is_pareto: boolean;
  is_recommended: boolean;
}

interface TournamentReport {
  total_configs_evaluated: number;
  pareto_points: ParetoPoint[];
  recommended: ParetoPoint | null;
  sweep_duration_s: number;
}

const ALL_TARGETS = ["alloy", "fusion", "element", "cim", "neuromorphic", "photonic"];
const ALL_QUANT = ["float32", "int8", "int4", "int4_k"];
const ALL_SYNTH = ["default", "balanced", "overlay", "timing_driven"];

function ScatterPlot({ points, recommended }: { points: ParetoPoint[]; recommended: ParetoPoint | null }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hovered, setHovered] = useState<ParetoPoint | null>(null);

  function drawPlot(canvas: HTMLCanvasElement, pts: ParetoPoint[], rec: ParetoPoint | null) {
    const ctx = canvas.getContext("2d");
    if (!ctx || pts.length === 0) return;
    const W = canvas.width;
    const H = canvas.height;
    const PAD = 48;

    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = "#0d1117";
    ctx.fillRect(0, 0, W, H);

    const tpsValues = pts.map((p) => p.tokens_per_sec);
    const latValues = pts.map((p) => p.latency_ms);
    const minTps = Math.min(...tpsValues);
    const maxTps = Math.max(...tpsValues);
    const minLat = Math.min(...latValues);
    const maxLat = Math.max(...latValues);
    const tpsRange = maxTps - minTps || 1;
    const latRange = maxLat - minLat || 1;

    const toX = (tps: number) => PAD + ((tps - minTps) / tpsRange) * (W - PAD * 2);
    const toY = (lat: number) => H - PAD - ((lat - minLat) / latRange) * (H - PAD * 2);

    // Grid lines
    ctx.strokeStyle = "#1e2d3d";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const x = PAD + (i / 4) * (W - PAD * 2);
      const y = PAD + (i / 4) * (H - PAD * 2);
      ctx.beginPath(); ctx.moveTo(x, PAD); ctx.lineTo(x, H - PAD); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(PAD, y); ctx.lineTo(W - PAD, y); ctx.stroke();
    }

    // Axis labels
    ctx.fillStyle = "#8b9ab3";
    ctx.font = "11px monospace";
    ctx.textAlign = "center";
    ctx.fillText("Tokens/sec →", W / 2, H - 8);
    ctx.save();
    ctx.translate(14, H / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText("Latency (ms) →", 0, 0);
    ctx.restore();

    const targetColors: Record<string, string> = {
      alloy: "#00d8ff",
      fusion: "#f59e0b",
      element: "#a78bfa",
      cim: "#34d399",
      neuromorphic: "#fb7185",
      photonic: "#fde68a",
    };

    pts.forEach((p) => {
      const x = toX(p.tokens_per_sec);
      const y = toY(p.latency_ms);
      const color = targetColors[p.target] ?? "#ffffff";
      const r = p.is_pareto ? 7 : 4;

      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = p.is_recommended
        ? "#fde68a"
        : p.is_pareto
        ? color
        : color + "55";
      ctx.fill();

      if (p.is_recommended) {
        ctx.strokeStyle = "#fde68a";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x, y, r + 4, 0, Math.PI * 2);
        ctx.stroke();
      } else if (p.is_pareto) {
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    });
  }

  function handleCanvasRef(canvas: HTMLCanvasElement | null) {
    if (canvas && points.length > 0) {
      drawPlot(canvas, points, recommended);
    }
  }

  return (
    <div className="relative">
      <canvas
        ref={(el) => { (canvasRef as any).current = el; handleCanvasRef(el); }}
        width={560}
        height={300}
        className="w-full rounded border border-border"
        style={{ maxWidth: "100%" }}
      />
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-text-secondary">
        {ALL_TARGETS.map((t) => (
          <span key={t} className="flex items-center gap-1">
            <span
              className="inline-block w-3 h-3 rounded-full"
              style={{
                background: { alloy: "#00d8ff", fusion: "#f59e0b", element: "#a78bfa", cim: "#34d399", neuromorphic: "#fb7185", photonic: "#fde68a" }[t] ?? "#fff",
              }}
            />
            {t}
          </span>
        ))}
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded-full border border-yellow-300" style={{ background: "#fde68a" }} />
          recommended
        </span>
      </div>
    </div>
  );
}

export default function TournamentPage() {
  const [constraints, setConstraints] = useState<TournamentConstraints>({
    maxLatencyMs: "",
    maxPowerW: "",
    maxCostUsd: "",
    minAccuracy: "",
    targets: [...ALL_TARGETS],
    quantizationSchemes: [...ALL_QUANT],
    synthesisModes: ["default", "balanced"],
    nodeCountMin: "4",
    nodeCountMax: "32",
  });
  const [report, setReport] = useState<TournamentReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiUrl =
    typeof window !== "undefined"
      ? (localStorage.getItem("tpt_api_url") ?? "http://localhost:8080")
      : "http://localhost:8080";

  function toggleItem(key: "targets" | "quantizationSchemes" | "synthesisModes", val: string) {
    setConstraints((prev) => {
      const arr = prev[key];
      return {
        ...prev,
        [key]: arr.includes(val) ? arr.filter((x) => x !== val) : [...arr, val],
      };
    });
  }

  async function runTournament() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiUrl}/api/tournament`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          max_latency_ms: constraints.maxLatencyMs ? Number(constraints.maxLatencyMs) : null,
          max_power_w: constraints.maxPowerW ? Number(constraints.maxPowerW) : null,
          max_cost_usd: constraints.maxCostUsd ? Number(constraints.maxCostUsd) : null,
          min_accuracy: constraints.minAccuracy ? Number(constraints.minAccuracy) : null,
          targets: constraints.targets,
          quant_schemes: constraints.quantizationSchemes,
          synthesis_modes: constraints.synthesisModes,
          node_count_min: Number(constraints.nodeCountMin),
          node_count_max: Number(constraints.nodeCountMax),
        }),
      });
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      setReport(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  const paretoPoints = report?.pareto_points ?? [];

  const exportJSON = useCallback(() => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "tournament-report.json"; a.click();
    URL.revokeObjectURL(url);
  }, [report]);

  const exportCSV = useCallback(() => {
    if (!report) return;
    const headers = ["target","quant_scheme","synthesis_mode","node_count","tokens_per_sec","latency_ms","power_watts","cost_usd","accuracy_delta","score","is_pareto","is_recommended"];
    const rows = report.pareto_points.map((p) => [
      p.target, p.quant_scheme, p.synthesis_mode, p.node_count,
      p.tokens_per_sec, p.latency_ms, p.power_watts, p.cost_usd,
      p.accuracy_delta, p.score, p.is_pareto, p.is_recommended,
    ]);
    const csv = [headers, ...rows].map((row) => row.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "tournament-report.csv"; a.click();
    URL.revokeObjectURL(url);
  }, [report]);

  return (
    <ErrorBoundary>
    <div className="min-h-screen bg-bg-primary text-text-primary p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-accent-cyan tracking-wider">
              ⊛ Compilation Tournament
            </h1>
            <p className="text-text-secondary text-sm mt-1">
              Auto-sweep quantization × target × synthesis space and find the Pareto-optimal configuration for your constraints.
            </p>
          </div>
          <Link href="/" className="text-text-secondary hover:text-text-primary text-sm">
            ← Dashboard
          </Link>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Config Panel */}
          <div className="lg:col-span-1 space-y-4">
            <div className="bg-bg-secondary border border-border rounded p-4 space-y-4">
              <h2 className="text-sm font-semibold text-accent-cyan uppercase tracking-wider">
                Constraints
              </h2>

              {[
                { label: "Max Latency (ms)", key: "maxLatencyMs" as const, placeholder: "e.g. 50" },
                { label: "Max Power (W)", key: "maxPowerW" as const, placeholder: "e.g. 5" },
                { label: "Max Cost (USD)", key: "maxCostUsd" as const, placeholder: "e.g. 1000" },
                { label: "Min Accuracy (0–1)", key: "minAccuracy" as const, placeholder: "e.g. 0.90" },
              ].map(({ label, key, placeholder }) => (
                <div key={key}>
                  <label className="block text-xs text-text-secondary mb-1">{label}</label>
                  <input
                    type="number"
                    placeholder={placeholder}
                    value={constraints[key]}
                    onChange={(e) => setConstraints((p) => ({ ...p, [key]: e.target.value }))}
                    className="w-full bg-bg-tertiary border border-border rounded px-2 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent-cyan"
                  />
                </div>
              ))}
            </div>

            <div className="bg-bg-secondary border border-border rounded p-4 space-y-3">
              <h2 className="text-sm font-semibold text-accent-cyan uppercase tracking-wider">
                Search Space
              </h2>

              <div>
                <p className="text-xs text-text-secondary mb-2">Targets</p>
                <div className="flex flex-wrap gap-1">
                  {ALL_TARGETS.map((t) => (
                    <button
                      key={t}
                      onClick={() => toggleItem("targets", t)}
                      className={`px-2 py-0.5 rounded text-xs border transition-colors ${
                        constraints.targets.includes(t)
                          ? "border-accent-cyan text-accent-cyan bg-accent-cyan/10"
                          : "border-border text-text-secondary"
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-xs text-text-secondary mb-2">Quantization</p>
                <div className="flex flex-wrap gap-1">
                  {ALL_QUANT.map((q) => (
                    <button
                      key={q}
                      onClick={() => toggleItem("quantizationSchemes", q)}
                      className={`px-2 py-0.5 rounded text-xs border transition-colors ${
                        constraints.quantizationSchemes.includes(q)
                          ? "border-accent-amber text-accent-amber bg-accent-amber/10"
                          : "border-border text-text-secondary"
                      }`}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-xs text-text-secondary mb-2">Synthesis Mode</p>
                <div className="flex flex-wrap gap-1">
                  {ALL_SYNTH.map((s) => (
                    <button
                      key={s}
                      onClick={() => toggleItem("synthesisModes", s)}
                      className={`px-2 py-0.5 rounded text-xs border transition-colors ${
                        constraints.synthesisModes.includes(s)
                          ? "border-purple-400 text-purple-400 bg-purple-400/10"
                          : "border-border text-text-secondary"
                      }`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-text-secondary mb-1">Min Nodes</label>
                  <input
                    type="number"
                    value={constraints.nodeCountMin}
                    onChange={(e) => setConstraints((p) => ({ ...p, nodeCountMin: e.target.value }))}
                    className="w-full bg-bg-tertiary border border-border rounded px-2 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent-cyan"
                  />
                </div>
                <div>
                  <label className="block text-xs text-text-secondary mb-1">Max Nodes</label>
                  <input
                    type="number"
                    value={constraints.nodeCountMax}
                    onChange={(e) => setConstraints((p) => ({ ...p, nodeCountMax: e.target.value }))}
                    className="w-full bg-bg-tertiary border border-border rounded px-2 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent-cyan"
                  />
                </div>
              </div>
            </div>

            <button
              onClick={runTournament}
              disabled={loading || constraints.targets.length === 0 || constraints.quantizationSchemes.length === 0}
              className="w-full py-2 rounded bg-accent-cyan text-bg-primary font-semibold text-sm hover:opacity-90 disabled:opacity-40 transition-opacity"
            >
              {loading ? "Running tournament…" : "Run Tournament"}
            </button>

            {error && (
              <div className="text-xs text-red-400 bg-red-900/20 border border-red-800 rounded p-2">
                {error}
              </div>
            )}
          </div>

          {/* Results Panel */}
          <div className="lg:col-span-2 space-y-4">
            {!report && !loading && (
              <div className="bg-bg-secondary border border-border rounded p-8 text-center text-text-secondary">
                <p className="text-4xl mb-3">⊛</p>
                <p className="text-sm">Configure your search space and run the tournament to find the optimal compilation configuration.</p>
              </div>
            )}

            {loading && (
              <div className="bg-bg-secondary border border-border rounded p-8 text-center">
                <div className="text-accent-cyan text-sm animate-pulse">
                  Sweeping {constraints.targets.length} targets × {constraints.quantizationSchemes.length} quant schemes × {constraints.synthesisModes.length} synthesis modes…
                </div>
              </div>
            )}

            {report && (
              <>
                <div className="bg-bg-secondary border border-border rounded p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-sm font-semibold text-accent-cyan uppercase tracking-wider">
                      Pareto Frontier
                    </h2>
                    <span className="text-xs text-text-secondary">
                      {report.total_configs_evaluated} configs in {report.sweep_duration_s.toFixed(1)}s
                    </span>
                  </div>
                  <ScatterPlot points={paretoPoints} recommended={report.recommended} />
                </div>

                {report.recommended && (
                  <div className="bg-yellow-900/20 border border-yellow-600/50 rounded p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-yellow-300 font-bold">★ Recommended Configuration</span>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
                      {[
                        { label: "Target", value: report.recommended.target },
                        { label: "Quantization", value: report.recommended.quant_scheme },
                        { label: "Synthesis", value: report.recommended.synthesis_mode },
                        { label: "Nodes", value: String(report.recommended.node_count) },
                        { label: "Tokens/sec", value: report.recommended.tokens_per_sec.toFixed(1) },
                        { label: "Latency", value: `${report.recommended.latency_ms.toFixed(1)}ms` },
                        { label: "Power", value: `${report.recommended.power_watts.toFixed(1)}W` },
                        { label: "Cost", value: `$${report.recommended.cost_usd.toFixed(0)}` },
                        { label: "Acc. delta", value: `${report.recommended.accuracy_delta > 0 ? "+" : ""}${report.recommended.accuracy_delta.toFixed(2)}%` },
                      ].map(({ label, value }) => (
                        <div key={label}>
                          <div className="text-xs text-text-secondary">{label}</div>
                          <div className="text-text-primary font-mono">{value}</div>
                        </div>
                      ))}
                    </div>
                    <Link
                      href={`/cloud?target=${report.recommended.target}&quant=${report.recommended.quant_scheme}&synthesis=${report.recommended.synthesis_mode}&nodes=${report.recommended.node_count}`}
                      className="inline-block mt-3 px-4 py-1.5 rounded bg-yellow-600 hover:bg-yellow-500 text-white text-sm font-semibold transition-colors"
                    >
                      Compile with this config →
                    </Link>
                  </div>
                )}

                <div className="bg-bg-secondary border border-border rounded p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-sm font-semibold text-accent-cyan uppercase tracking-wider">
                      All Pareto-Optimal Configs ({paretoPoints.filter((p) => p.is_pareto).length})
                    </h2>
                    <div className="flex gap-2">
                      <button onClick={exportJSON} className="px-2 py-1 rounded bg-bg-tertiary border border-border text-xs text-text-secondary hover:text-text-primary">Export JSON</button>
                      <button onClick={exportCSV} className="px-2 py-1 rounded bg-bg-tertiary border border-border text-xs text-text-secondary hover:text-text-primary">Export CSV</button>
                    </div>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs font-mono">
                      <thead>
                        <tr className="text-text-secondary border-b border-border">
                          {["Target", "Quant", "Synth", "Nodes", "TPS", "Lat(ms)", "Power(W)", "Cost($)", "Acc Δ", "Score", ""].map((h) => (
                            <th key={h} className="text-left pb-2 pr-3">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {paretoPoints
                          .filter((p) => p.is_pareto)
                          .sort((a, b) => b.score - a.score)
                          .map((p, i) => (
                            <tr key={i} className={`border-b border-border/50 ${p.is_recommended ? "bg-yellow-900/10" : ""}`}>
                              <td className="py-1.5 pr-3 text-accent-cyan">{p.target}</td>
                              <td className="py-1.5 pr-3">{p.quant_scheme}</td>
                              <td className="py-1.5 pr-3">{p.synthesis_mode}</td>
                              <td className="py-1.5 pr-3">{p.node_count}</td>
                              <td className="py-1.5 pr-3">{p.tokens_per_sec.toFixed(0)}</td>
                              <td className="py-1.5 pr-3">{p.latency_ms.toFixed(1)}</td>
                              <td className="py-1.5 pr-3">{p.power_watts.toFixed(1)}</td>
                              <td className="py-1.5 pr-3">{p.cost_usd.toFixed(0)}</td>
                              <td className={`py-1.5 pr-3 ${p.accuracy_delta >= 0 ? "text-green-400" : "text-red-400"}`}>
                                {p.accuracy_delta > 0 ? "+" : ""}{p.accuracy_delta.toFixed(2)}%
                              </td>
                              <td className="py-1.5 pr-3">{p.score.toFixed(3)}</td>
                              <td className="py-1.5">
                                {p.is_recommended && <span className="text-yellow-300">★</span>}
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
    </ErrorBoundary>
  );
}
