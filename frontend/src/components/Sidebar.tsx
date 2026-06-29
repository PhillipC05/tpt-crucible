"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

interface SidebarProps {
  selectedTab: string;
  onTabChange: (tab: "overview" | "fusion" | "alloy" | "element" | "pkg") => void;
  connected: boolean;
}

const tabs = [
  { id: "overview" as const, label: "Overview", icon: "◈" },
  { id: "fusion" as const, label: "Fusion (FPGA)", icon: "▣" },
  { id: "alloy" as const, label: "Alloy (Swarm)", icon: "⬡" },
  { id: "element" as const, label: "Element (Analog)", icon: "◎" },
  { id: "pkg" as const, label: "Package", icon: "⊞" },
];

export function Sidebar({ selectedTab, onTabChange, connected }: SidebarProps) {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    const stored = localStorage.getItem("tpt_theme") as "dark" | "light" | null;
    const initial = stored ?? "dark";
    setTheme(initial);
    document.documentElement.setAttribute("data-theme", initial);
  }, []);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    localStorage.setItem("tpt_theme", next);
    document.documentElement.setAttribute("data-theme", next);
  }

  return (
    <aside className="w-64 bg-bg-secondary border-r border-border flex flex-col">
      <div className="p-4 border-b border-border">
        <h1 className="text-lg font-bold text-accent-cyan tracking-wider">
          TPT CRUCIBLE
        </h1>
        <p className="text-xs text-text-secondary mt-1">
          Observer Dashboard
        </p>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors ${
              selectedTab === tab.id
                ? "bg-bg-tertiary text-accent-cyan glow-cyan"
                : "text-text-secondary hover:text-text-primary hover:bg-bg-tertiary"
            }`}
          >
            <span className="text-base">{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}

        <div className="pt-3 mt-3 border-t border-border space-y-1">
          <Link
            href="/topology"
            className="w-full flex items-center gap-3 px-3 py-2 rounded text-sm text-text-secondary hover:text-text-primary hover:bg-bg-tertiary transition-colors"
          >
            <span className="text-base">⦻</span>
            <span>3D Topology</span>
          </Link>
          <Link
            href="/editor"
            className="w-full flex items-center gap-3 px-3 py-2 rounded text-sm text-text-secondary hover:text-text-primary hover:bg-bg-tertiary transition-colors"
          >
            <span className="text-base">◇</span>
            <span>IR Graph Editor</span>
          </Link>
          <Link
            href="/cloud"
            className="w-full flex items-center gap-3 px-3 py-2 rounded text-sm text-text-secondary hover:text-text-primary hover:bg-bg-tertiary transition-colors"
          >
            <span className="text-base">☁</span>
            <span>Cloud</span>
          </Link>
          <Link
            href="/jobs"
            className="w-full flex items-center gap-3 px-3 py-2 rounded text-sm text-text-secondary hover:text-text-primary hover:bg-bg-tertiary transition-colors"
          >
            <span className="text-base">⊟</span>
            <span>Job History</span>
          </Link>
          <Link
            href="/compare"
            className="w-full flex items-center gap-3 px-3 py-2 rounded text-sm text-text-secondary hover:text-text-primary hover:bg-bg-tertiary transition-colors"
          >
            <span className="text-base">⊕</span>
            <span>Compare Targets</span>
          </Link>
          <Link
            href="/tournament"
            className="w-full flex items-center gap-3 px-3 py-2 rounded text-sm text-text-secondary hover:text-text-primary hover:bg-bg-tertiary transition-colors"
          >
            <span className="text-base">⊛</span>
            <span>Tournament</span>
          </Link>
          <Link
            href="/provenance"
            className="w-full flex items-center gap-3 px-3 py-2 rounded text-sm text-text-secondary hover:text-text-primary hover:bg-bg-tertiary transition-colors"
          >
            <span className="text-base">⊚</span>
            <span>Provenance</span>
          </Link>
          <Link
            href="/settings"
            className="w-full flex items-center gap-3 px-3 py-2 rounded text-sm text-text-secondary hover:text-text-primary hover:bg-bg-tertiary transition-colors"
          >
            <span className="text-base">⚙</span>
            <span>Settings</span>
          </Link>
        </div>
      </nav>

      <div className="p-4 border-t border-border space-y-3">
        <button
          onClick={toggleTheme}
          title="Toggle dark/light mode"
          className="w-full flex items-center gap-2 px-3 py-1.5 rounded text-xs text-text-secondary hover:text-text-primary hover:bg-bg-tertiary transition-colors"
        >
          <span>{theme === "dark" ? "○" : "●"}</span>
          <span>{theme === "dark" ? "Light mode" : "Dark mode"}</span>
        </button>
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              connected ? "bg-accent-green" : "bg-accent-red"
            }`}
          />
          <span className="text-xs text-text-secondary">
            {connected ? "Connected" : "Disconnected"}
          </span>
        </div>
      </div>
    </aside>
  );
}
