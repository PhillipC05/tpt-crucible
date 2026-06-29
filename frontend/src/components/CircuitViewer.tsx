"use client";

interface CircuitCandidate {
  id: number;
  confidence: number;
  failureMode: string;
  componentCount: number;
  driftPrediction: number;
}

interface CircuitViewerProps {
  candidates?: CircuitCandidate[];
  selectedId?: number;
  onSelect?: (id: number) => void;
}

const defaultCandidates: CircuitCandidate[] = [
  { id: 1, confidence: 0.94, failureMode: "thermal_drift", componentCount: 128, driftPrediction: 0.02 },
  { id: 2, confidence: 0.88, failureMode: "none", componentCount: 96, driftPrediction: 0.05 },
  { id: 3, confidence: 0.72, failureMode: "noise_overflow", componentCount: 64, driftPrediction: 0.12 },
];

export function CircuitViewer({
  candidates = defaultCandidates,
  selectedId = 1,
  onSelect,
}: CircuitViewerProps) {
  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">ANALOG CIRCUIT CANDIDATES</h3>
      <div className="space-y-2">
        {candidates.map((c) => (
          <button
            key={c.id}
            onClick={() => onSelect?.(c.id)}
            className={`w-full p-2 rounded border text-left transition-colors ${
              selectedId === c.id
                ? "border-accent-cyan bg-accent-cyan/10"
                : "border-border bg-bg-tertiary hover:border-accent-cyan/50"
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-bold text-text-primary">Candidate #{c.id}</span>
              <span className={`text-xs font-mono ${
                c.confidence >= 0.85 ? "text-accent-green" : c.confidence >= 0.7 ? "text-accent-amber" : "text-accent-red"
              }`}>
                {(c.confidence * 100).toFixed(0)}% conf
              </span>
            </div>
            <div className="flex justify-between text-[10px] text-text-secondary">
              <span>{c.componentCount} components</span>
              <span>drift: {(c.driftPrediction * 100).toFixed(2)}%</span>
              <span className={c.failureMode === "none" ? "text-accent-green" : "text-accent-amber"}>
                {c.failureMode === "none" ? "clean" : c.failureMode}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
