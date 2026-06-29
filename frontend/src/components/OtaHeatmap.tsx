"use client";

interface NodeStatus {
  id: string;
  status: "pending" | "flashing" | "done" | "failed";
  progress: number;
}

const sampleNodes: NodeStatus[] = Array.from({ length: 16 }, (_, i) => ({
  id: `N${i}`,
  status: i < 12 ? "done" : i < 14 ? "flashing" : i === 14 ? "pending" : "failed",
  progress: i < 12 ? 100 : i < 14 ? 50 : i === 14 ? 0 : 0,
}));

const statusColors: Record<string, string> = {
  done: "bg-accent-green/60 border-accent-green/50",
  flashing: "bg-accent-cyan/60 border-accent-cyan/50 animate-pulse",
  pending: "bg-bg-tertiary border-border",
  failed: "bg-accent-red/60 border-accent-red/50",
};

export function OtaHeatmap() {
  const done = sampleNodes.filter((n) => n.status === "done").length;
  const flashing = sampleNodes.filter((n) => n.status === "flashing").length;
  const failed = sampleNodes.filter((n) => n.status === "failed").length;

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-amber mb-3">OTA FLASH STATUS</h3>
      <div className="grid grid-cols-4 gap-1.5">
        {sampleNodes.map((node) => (
          <div
            key={node.id}
            className={`aspect-square rounded border flex flex-col items-center justify-center ${statusColors[node.status]}`}
            title={`${node.id}: ${node.status} (${node.progress}%)`}
          >
            <div className="text-[10px] font-bold text-white">{node.id}</div>
            <div className="text-[8px] text-white/70">{node.progress}%</div>
          </div>
        ))}
      </div>
      <div className="flex justify-between mt-2 text-[10px] text-text-secondary">
        <span>{done} done</span>
        <span>{flashing} flashing</span>
        <span>{failed} failed</span>
      </div>
    </div>
  );
}
