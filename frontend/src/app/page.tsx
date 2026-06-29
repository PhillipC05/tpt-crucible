"use client";

import { useState } from "react";
import { Dashboard } from "@/components/Dashboard";
import { Sidebar } from "@/components/Sidebar";
import { TelemetryProvider, useTelemetry } from "@/contexts/TelemetryContext";

function HomeInner() {
  const [selectedTab, setSelectedTab] = useState<"overview" | "fusion" | "alloy" | "element" | "pkg">("overview");
  const { connected } = useTelemetry();

  return (
    <div className="flex h-screen bg-bg-primary grid-bg">
      <Sidebar selectedTab={selectedTab} onTabChange={setSelectedTab} connected={connected} />
      <main className="flex-1 overflow-auto p-6">
        <Dashboard tab={selectedTab} connected={connected} />
      </main>
    </div>
  );
}

export default function Home() {
  return (
    <TelemetryProvider>
      <HomeInner />
    </TelemetryProvider>
  );
}
