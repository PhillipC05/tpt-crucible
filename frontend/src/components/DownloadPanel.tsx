"use client";

interface DownloadItem {
  filename: string;
  size: string;
  type: string;
  url: string;
}

const sampleDownloads: DownloadItem[] = [
  { filename: "model.tptpkg", size: "45.2 MB", type: "Package", url: "/download/model.tptpkg" },
  { filename: "ir/model.tptir", size: "1.2 MB", type: "IR File", url: "/download/ir/model.tptir" },
  { filename: "compat/preflight.json", size: "4 KB", type: "Report", url: "/download/compat/preflight.json" },
  { filename: "quant/quant_profile.json", size: "1 KB", type: "Profile", url: "/download/quant/quant_profile.json" },
  { filename: "bom/parts.csv", size: "2 KB", type: "BOM", url: "/download/bom/parts.csv" },
];

export function DownloadPanel() {
  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">DOWNLOADS</h3>
      <div className="space-y-1">
        {sampleDownloads.map((item) => (
          <a
            key={item.filename}
            href={item.url}
            className="flex items-center justify-between p-2 rounded hover:bg-bg-tertiary transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-bg-tertiary text-text-secondary">{item.type}</span>
              <span className="text-xs font-mono text-text-primary">{item.filename}</span>
            </div>
            <span className="text-xs text-text-secondary">{item.size}</span>
          </a>
        ))}
      </div>
    </div>
  );
}
