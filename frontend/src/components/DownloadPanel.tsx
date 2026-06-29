"use client";

import { useEffect, useState } from "react";

interface DownloadItem {
  filename: string;
  size: string;
  type: string;
  url: string;
}

/* sample data — shown when no package is loaded or API is unreachable */
const SAMPLE_DOWNLOADS: DownloadItem[] = [
  { filename: "model.tptpkg", size: "45.2 MB", type: "Package", url: "#" },
  { filename: "ir/model.tptir", size: "1.2 MB", type: "IR File", url: "#" },
  { filename: "compat/preflight.json", size: "4 KB", type: "Report", url: "#" },
  { filename: "quant/quant_profile.json", size: "1 KB", type: "Profile", url: "#" },
  { filename: "bom/parts.csv", size: "2 KB", type: "BOM", url: "#" },
];

function formatBytes(bytes: number): string {
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`;
  if (bytes >= 1_000) return `${(bytes / 1_000).toFixed(0)} KB`;
  return `${bytes} B`;
}

export function DownloadPanel({ packageId }: { packageId?: string }) {
  const [items, setItems] = useState<DownloadItem[]>(SAMPLE_DOWNLOADS);
  const [offline, setOffline] = useState(!packageId);

  useEffect(() => {
    if (!packageId) { setOffline(true); return; }
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";
    fetch(`${apiUrl}/api/packages/${packageId}/artifacts`)
      .then((r) => r.json())
      .then((artifacts: { path: string; size_bytes: number; sha256: string }[]) => {
        const ext = (p: string) => {
          if (p.endsWith(".tptpkg")) return "Package";
          if (p.endsWith(".tptir")) return "IR File";
          if (p.endsWith(".json")) return "Report";
          if (p.endsWith(".csv")) return "BOM";
          if (p.endsWith(".v") || p.endsWith(".vhdl")) return "RTL";
          if (p.endsWith(".spice")) return "SPICE";
          return "File";
        };
        setOffline(false);
        setItems(
          artifacts.map((a) => ({
            filename: a.path,
            size: formatBytes(a.size_bytes),
            type: ext(a.path),
            url: `${apiUrl}/api/packages/${packageId}/download/${encodeURIComponent(a.path)}`,
          }))
        );
      })
      .catch(() => setOffline(true));
  }, [packageId]);

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">DOWNLOADS</h3>
      {offline && (
        <div className="flex items-center gap-2 mb-3 px-2 py-1.5 rounded bg-accent-amber/10 border border-accent-amber/30">
          <span className="text-accent-amber text-xs">⚠</span>
          <span className="text-xs text-accent-amber">Offline — showing sample data</span>
        </div>
      )}
      <div className="space-y-1">
        {items.map((item) => (
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
