"use client";

import { useState, useEffect } from "react";
import { Dashboard } from "@/components/Dashboard";
import { Sidebar } from "@/components/Sidebar";

export default function Home() {
  const [connected, setConnected] = useState(false);
  const [selectedTab, setSelectedTab] = useState<"overview" | "fusion" | "alloy" | "element" | "pkg">("overview");

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8080/ws");
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    return () => ws.close();
  }, []);

  return (
    <div className="flex h-screen bg-bg-primary grid-bg">
      <Sidebar selectedTab={selectedTab} onTabChange={setSelectedTab} connected={connected} />
      <main className="flex-1 overflow-auto p-6">
        <Dashboard tab={selectedTab} connected={connected} />
      </main>
    </div>
  );
}
