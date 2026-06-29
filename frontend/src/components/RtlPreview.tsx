"use client";

interface RtlPreviewProps {
  moduleCount?: number;
  estimatedTiming?: string;
  lutsUsed?: number;
  maxLuts?: number;
}

export function RtlPreview({
  moduleCount = 12,
  estimatedTiming = "4.2 ns",
  lutsUsed = 45200,
  maxLuts = 87480,
}: RtlPreviewProps) {
  const lutPct = (lutsUsed / maxLuts) * 100;

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">RTL PREVIEW</h3>
      <div className="grid grid-cols-2 gap-2 text-[11px] mb-3">
        <div>
          <span className="text-text-secondary">Modules</span>
          <div className="font-mono text-text-primary">{moduleCount}</div>
        </div>
        <div>
          <span className="text-text-secondary">Worst Slack</span>
          <div className={`font-mono ${parseFloat(estimatedTiming) < 5 ? "text-accent-green" : "text-accent-amber"}`}>
            {estimatedTiming}
          </div>
        </div>
      </div>
      <div className="w-full h-2 bg-bg-tertiary rounded-full overflow-hidden mb-1">
        <div
          className={`h-full rounded-full ${lutPct >= 90 ? "bg-accent-red" : lutPct >= 70 ? "bg-accent-amber" : "bg-accent-green"}`}
          style={{ width: `${lutPct}%` }}
        />
      </div>
      <div className="text-[10px] text-text-secondary font-mono">
        LUTs: {lutsUsed.toLocaleString()} / {maxLuts.toLocaleString()} ({lutPct.toFixed(1)}%)
      </div>
      <div className="mt-2 text-[9px] text-text-secondary">
        Generated RTL ready for review before Fusion pipeline entry.
      </div>
    </div>
  );
}
