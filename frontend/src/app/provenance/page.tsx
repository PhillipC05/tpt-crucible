"use client";

import { useRef, useState } from "react";
import Link from "next/link";

interface ProvenanceNode {
  step_id: string;
  step_type: string;
  params: Record<string, unknown>;
  timestamp: string;
  triggered_by: string;
  accuracy_delta: number | null;
  parent_ids: string[];
  notes: string;
}

interface ProvenanceGraph {
  model_name: string;
  source_sha256: string;
  created_at: string;
  nodes: ProvenanceNode[];
}

interface DiffResult {
  added: ProvenanceNode[];
  removed: ProvenanceNode[];
  summary: string;
}

const STEP_TYPE_COLORS: Record<string, string> = {
  INGEST: "#00d8ff",
  OPTIMIZE: "#f59e0b",
  PREFLIGHT_FIX: "#fb7185",
  QUANTIZE: "#a78bfa",
  SPARSITY: "#34d399",
  INTERMITTENT: "#fde68a",
  PACK: "#60a5fa",
  CACHE_HIT: "#4ade80",
  OTA_UPDATE: "#f97316",
  ADAPTIVE_RECOMPILE: "#e879f9",
  CUSTOM: "#94a3b8",
};

function StepBadge({ type }: { type: string }) {
  const color = STEP_TYPE_COLORS[type] ?? "#94a3b8";
  return (
    <span
      className="inline-block px-1.5 py-0.5 rounded text-xs font-mono font-bold uppercase"
      style={{ color, border: `1px solid ${color}33`, background: `${color}11` }}
    >
      {type}
    </span>
  );
}

function ProvenanceTimeline({ graph, diff }: { graph: ProvenanceGraph; diff: DiffResult | null }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const addedIds = new Set(diff?.added.map((n) => n.step_id) ?? []);
  const removedIds = new Set(diff?.removed.map((n) => n.step_id) ?? []);

  return (
    <div className="space-y-1">
      {graph.nodes.map((node, i) => {
        const isExpanded = expanded === node.step_id;
        const isAdded = addedIds.has(node.step_id);
        const isRemoved = removedIds.has(node.step_id);
        return (
          <div key={node.step_id}>
            {i > 0 && (
              <div className="ml-4 w-px h-3 bg-border" />
            )}
            <div
              className={`rounded border transition-colors cursor-pointer ${
                isAdded
                  ? "border-green-600/60 bg-green-900/10"
                  : isRemoved
                  ? "border-red-600/60 bg-red-900/10"
                  : "border-border bg-bg-secondary hover:border-border/80"
              }`}
              onClick={() => setExpanded(isExpanded ? null : node.step_id)}
            >
              <div className="flex items-center gap-3 p-3">
                <div
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ background: STEP_TYPE_COLORS[node.step_type] ?? "#94a3b8" }}
                />
                <StepBadge type={node.step_type} />
                <span className="text-xs text-text-secondary font-mono truncate flex-1">
                  {node.step_id.slice(0, 16)}…
                </span>
                {node.accuracy_delta !== null && (
                  <span
                    className={`text-xs font-mono ${
                      node.accuracy_delta >= 0 ? "text-green-400" : "text-red-400"
                    }`}
                  >
                    {node.accuracy_delta > 0 ? "+" : ""}{node.accuracy_delta.toFixed(2)}%
                  </span>
                )}
                <span className="text-xs text-text-secondary flex-shrink-0">
                  {new Date(node.timestamp).toLocaleTimeString()}
                </span>
                {isAdded && <span className="text-xs text-green-400 font-bold">+new</span>}
                {isRemoved && <span className="text-xs text-red-400 font-bold">−removed</span>}
                <span className="text-text-secondary text-xs">{isExpanded ? "▲" : "▼"}</span>
              </div>

              {isExpanded && (
                <div className="px-4 pb-3 space-y-2 border-t border-border/50 pt-2">
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-text-secondary">Triggered by:</span>{" "}
                      <span className="text-text-primary font-mono">{node.triggered_by}</span>
                    </div>
                    <div>
                      <span className="text-text-secondary">Parents:</span>{" "}
                      <span className="text-text-primary font-mono">
                        {node.parent_ids.length === 0
                          ? "root"
                          : node.parent_ids.map((id) => id.slice(0, 8)).join(", ")}
                      </span>
                    </div>
                  </div>
                  {node.notes && (
                    <div className="text-xs text-text-secondary italic">{node.notes}</div>
                  )}
                  {Object.keys(node.params).length > 0 && (
                    <pre className="text-xs bg-bg-tertiary rounded p-2 overflow-x-auto text-text-secondary">
                      {JSON.stringify(node.params, null, 2)}
                    </pre>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function ProvenancePage() {
  const [pkgUrl, setPkgUrl] = useState("");
  const [diffUrl, setDiffUrl] = useState("");
  const [graph, setGraph] = useState<ProvenanceGraph | null>(null);
  const [diff, setDiff] = useState<DiffResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const apiUrl =
    typeof window !== "undefined"
      ? (localStorage.getItem("tpt_api_url") ?? "http://localhost:8080")
      : "http://localhost:8080";

  async function loadProvenance() {
    if (!pkgUrl.trim()) return;
    setLoading(true);
    setError(null);
    setDiff(null);
    try {
      const res = await fetch(`${apiUrl}/api/provenance`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tptpkg: pkgUrl.trim(), diff: diffUrl.trim() || null }),
      });
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      setGraph(data.graph);
      setDiff(data.diff ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  const stepTypeCounts = graph
    ? Object.entries(
        graph.nodes.reduce<Record<string, number>>((acc, n) => {
          acc[n.step_type] = (acc[n.step_type] ?? 0) + 1;
          return acc;
        }, {})
      )
    : [];

  return (
    <div className="min-h-screen bg-bg-primary text-text-primary p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-accent-cyan tracking-wider">
              ⊚ Model Provenance
            </h1>
            <p className="text-text-secondary text-sm mt-1">
              Full compilation lineage — every transformation, operator substitution, and quantization decision recorded as an auditable DAG.
            </p>
          </div>
          <Link href="/" className="text-text-secondary hover:text-text-primary text-sm">
            ← Dashboard
          </Link>
        </div>

        {/* Load Panel */}
        <div className="bg-bg-secondary border border-border rounded p-4 space-y-3">
          <h2 className="text-sm font-semibold text-accent-cyan uppercase tracking-wider">
            Load Package
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-text-secondary mb-1">Primary .tptpkg path</label>
              <input
                type="text"
                placeholder="/path/to/model.tptpkg"
                value={pkgUrl}
                onChange={(e) => setPkgUrl(e.target.value)}
                className="w-full bg-bg-tertiary border border-border rounded px-2 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent-cyan font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-text-secondary mb-1">
                Compare with (optional .tptpkg path)
              </label>
              <input
                type="text"
                placeholder="/path/to/other.tptpkg"
                value={diffUrl}
                onChange={(e) => setDiffUrl(e.target.value)}
                className="w-full bg-bg-tertiary border border-border rounded px-2 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent-cyan font-mono"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={loadProvenance}
              disabled={loading || !pkgUrl.trim()}
              className="px-4 py-1.5 rounded bg-accent-cyan text-bg-primary font-semibold text-sm hover:opacity-90 disabled:opacity-40 transition-opacity"
            >
              {loading ? "Loading…" : "Load Provenance"}
            </button>
            {diff && (
              <span className="flex items-center text-xs text-text-secondary">
                Diff mode active — new steps highlighted in{" "}
                <span className="text-green-400 ml-1">green</span>
              </span>
            )}
          </div>
          {error && (
            <div className="text-xs text-red-400 bg-red-900/20 border border-red-800 rounded p-2">
              {error}
            </div>
          )}
        </div>

        {graph && (
          <>
            {/* Summary bar */}
            <div className="bg-bg-secondary border border-border rounded p-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="text-xs text-text-secondary">Model</div>
                  <div className="font-mono text-text-primary truncate">{graph.model_name}</div>
                </div>
                <div>
                  <div className="text-xs text-text-secondary">Source SHA-256</div>
                  <div className="font-mono text-text-primary text-xs">{graph.source_sha256.slice(0, 16)}…</div>
                </div>
                <div>
                  <div className="text-xs text-text-secondary">Created</div>
                  <div className="font-mono text-text-primary text-xs">
                    {new Date(graph.created_at).toLocaleString()}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-text-secondary">Pipeline steps</div>
                  <div className="font-mono text-accent-cyan">{graph.nodes.length}</div>
                </div>
              </div>

              {stepTypeCounts.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {stepTypeCounts.map(([type, count]) => (
                    <span key={type} className="flex items-center gap-1 text-xs">
                      <span
                        className="inline-block w-2 h-2 rounded-full"
                        style={{ background: STEP_TYPE_COLORS[type] ?? "#94a3b8" }}
                      />
                      <span className="text-text-secondary">{type}</span>
                      <span className="text-text-primary font-mono">×{count}</span>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Diff summary */}
            {diff && (
              <div className="bg-bg-secondary border border-border rounded p-3 text-sm">
                <span className="text-text-secondary">Diff summary: </span>
                <span className="text-green-400">+{diff.added.length} added</span>
                {" · "}
                <span className="text-red-400">−{diff.removed.length} removed</span>
                {diff.summary && (
                  <span className="text-text-secondary ml-2 text-xs">{diff.summary}</span>
                )}
              </div>
            )}

            {/* Timeline */}
            <div className="bg-bg-secondary border border-border rounded p-4">
              <h2 className="text-sm font-semibold text-accent-cyan uppercase tracking-wider mb-4">
                Compilation Timeline
              </h2>
              {graph.nodes.length === 0 ? (
                <p className="text-text-secondary text-sm text-center py-4">
                  No provenance nodes recorded in this package.
                </p>
              ) : (
                <ProvenanceTimeline graph={graph} diff={diff} />
              )}
            </div>

            {/* Accuracy delta chart */}
            {graph.nodes.some((n) => n.accuracy_delta !== null) && (
              <div className="bg-bg-secondary border border-border rounded p-4">
                <h2 className="text-sm font-semibold text-accent-cyan uppercase tracking-wider mb-3">
                  Accuracy Delta per Step
                </h2>
                <div className="flex items-end gap-1 h-20">
                  {graph.nodes
                    .filter((n) => n.accuracy_delta !== null)
                    .map((node) => {
                      const pct = Math.abs(node.accuracy_delta!) * 10;
                      const clamped = Math.min(pct, 100);
                      return (
                        <div
                          key={node.step_id}
                          title={`${node.step_type}: ${node.accuracy_delta! > 0 ? "+" : ""}${node.accuracy_delta!.toFixed(2)}%`}
                          className="flex-1 rounded-t transition-all"
                          style={{
                            height: `${clamped}%`,
                            minHeight: "2px",
                            background: node.accuracy_delta! >= 0 ? "#4ade80" : "#fb7185",
                            opacity: 0.8,
                          }}
                        />
                      );
                    })}
                </div>
                <div className="flex justify-between text-xs text-text-secondary mt-1">
                  <span>start</span>
                  <span>end</span>
                </div>
              </div>
            )}
          </>
        )}

        {!graph && !loading && (
          <div className="bg-bg-secondary border border-border rounded p-10 text-center text-text-secondary">
            <p className="text-4xl mb-3">⊚</p>
            <p className="text-sm">
              Enter a <span className="font-mono text-text-primary">.tptpkg</span> path above to inspect its compilation lineage.
            </p>
            <p className="text-xs mt-2">
              Optionally provide a second package path to diff the two lineages side-by-side.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
