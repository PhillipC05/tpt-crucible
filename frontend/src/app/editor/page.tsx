"use client";

import dynamic from "next/dynamic";
import { useCallback, useRef, useState } from "react";
import { useToast } from "@/components/Toast";
import { ErrorBoundary } from "@/components/ErrorBoundary";

const IrGraphEditor = dynamic(
  () => import("@/components/IrGraphEditor").then((mod) => mod.IrGraphEditor),
  { ssr: false }
);

const TelemetryReplay = dynamic(
  () => import("@/components/TelemetryReplay").then((mod) => mod.TelemetryReplay),
  { ssr: false }
);

export default function EditorPage() {
  const { toast } = useToast();
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const graphRef = useRef<any>(null);

  const handleExport = useCallback(async () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";
    const graph = graphRef.current?.getGraph?.() ?? {};
    try {
      const res = await fetch(`${apiUrl}/api/ir/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(graph),
      });
      if (!res.ok) throw new Error(res.statusText);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "model.tptir";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      const json = JSON.stringify(graph, null, 2);
      const blob = new Blob([json], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "model.tptir";
      a.click();
      URL.revokeObjectURL(url);
    }
  }, []);

  const handleSave = useCallback(async () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";
    const graph = graphRef.current?.getGraph?.() ?? {};
    setSaving(true);
    setStatusMsg("");
    try {
      const res = await fetch(`${apiUrl}/api/ir/current`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(graph),
      });
      if (res.ok) {
        setStatusMsg("Saved");
        toast("Graph saved", "success");
      } else {
        setStatusMsg(`Error: ${res.statusText}`);
        toast(`Save failed: ${res.statusText}`, "error");
      }
    } catch {
      setStatusMsg("Save failed — backend unreachable");
      toast("Backend unreachable — changes not saved", "error");
    } finally {
      setSaving(false);
      setTimeout(() => setStatusMsg(""), 3000);
    }
  }, []);

  return (
    <ErrorBoundary>
    <div className="h-screen flex flex-col bg-bg-primary grid-bg">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-accent-cyan">TPT-IR Visual Graph Editor</h1>
          <p className="text-xs text-text-secondary">Interactive DAG editor for neural network operators</p>
        </div>
        <div className="flex items-center gap-2">
          {statusMsg && <span className="text-xs text-accent-amber">{statusMsg}</span>}
          <button
            onClick={handleExport}
            className="px-3 py-1.5 rounded bg-bg-tertiary text-text-secondary hover:text-text-primary text-xs border border-border"
          >
            Export .tptir
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-3 py-1.5 rounded bg-accent-cyan/20 text-accent-cyan text-xs border border-accent-cyan/50 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>

      <div className="flex-1 flex">
        <div className="flex-1">
          <IrGraphEditor onNodeSelect={setSelectedNode} />
        </div>

        <div className="w-72 border-l border-border p-4 space-y-4 overflow-auto">
          {selectedNode ? (
            <div className="stat-card space-y-3">
              <h3 className="text-sm font-bold text-accent-amber">OPERATOR DETAILS</h3>
              <div className="space-y-2 text-xs">
                <div>
                  <label className="text-text-secondary block mb-1">Type</label>
                  <div className="px-2 py-1 bg-bg-tertiary rounded font-mono text-accent-cyan">
                    {selectedNode.op_type}
                  </div>
                </div>
                <div>
                  <label className="text-text-secondary block mb-1">Name</label>
                  <div className="px-2 py-1 bg-bg-tertiary rounded font-mono">
                    {selectedNode.name}
                  </div>
                </div>
                {selectedNode.target && (
                  <div>
                    <label className="text-text-secondary block mb-1">Hardware Target</label>
                    <div className="flex gap-1">
                      {["fpga", "swarm", "analog"].map((t) => (
                        <button
                          key={t}
                          className={`px-2 py-1 rounded text-[10px] ${
                            selectedNode.target === t
                              ? "bg-accent-cyan/20 text-accent-cyan border border-accent-cyan/50"
                              : "bg-bg-tertiary text-text-secondary border border-border"
                          }`}
                        >
                          {t}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {selectedNode.severity && (
                  <div>
                    <label className="text-text-secondary block mb-1">Pre-flight Status</label>
                    <div className={`px-2 py-1 rounded text-[10px] ${
                      selectedNode.severity === "pass" ? "bg-accent-green/20 text-accent-green" :
                      selectedNode.severity === "warn" ? "bg-accent-amber/20 text-accent-amber" :
                      "bg-accent-red/20 text-accent-red"
                    }`}>
                      {selectedNode.severity.toUpperCase()}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="stat-card">
              <p className="text-xs text-text-secondary text-center py-4">
                Click a node to view details
              </p>
            </div>
          )}

          <TelemetryReplay entries={[]} />
        </div>
      </div>
    </div>
    </ErrorBoundary>
  );
}
