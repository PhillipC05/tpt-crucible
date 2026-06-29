"use client";

import { useState } from "react";
import { useTelemetry } from "@/contexts/TelemetryContext";
import dynamic from "next/dynamic";
import {
  TokensPerSecondChart,
  MemoryBandwidthChart,
  ThermalDriftChart,
  LatencyHeatmap,
  PowerChart,
  CompilationTimeline,
} from "./TelemetryCharts";
import { PackageManifestViewer } from "./PackageManifest";
import { BomTab } from "./BomTab";
import { DiagnosticsHeatmap } from "./DiagnosticsHeatmap";
import { RegressionBadge } from "./RegressionBadge";
import { PipelineView } from "./PipelineView";
import { CostEstimator } from "./CostEstimator";
import { SparsityHeatmap } from "./SparsityHeatmap";
import { ReplayOverlay } from "./ReplayOverlay";
import { ZephyrTargetCard } from "./ZephyrTargetCard";
import { IntermittentDashboard } from "./IntermittentDashboard";
import { AlloyTuneReport } from "./AlloyTuneReport";
import { ErrorPanel } from "./ErrorPanel";
import { RiscVIsaPanel } from "./RiscVIsaPanel";
import { PhotonTargetCard } from "./PhotonTargetCard";
import { OtaHeatmap } from "./OtaHeatmap";
import { DownloadPanel } from "./DownloadPanel";
import { QuantizationMap } from "./QuantizationMap";
import { ModelSwitcher } from "./ModelSwitcher";
import { PcbVisualizer } from "./PcbVisualizer";
import { SpeculativeDecodingPanel } from "./SpeculativeDecoding";
import { CarbonCostPanel } from "./CarbonCost";
import { AutoDiscoveryPanel } from "./AutoDiscoveryPanel";
import { PipelineUtilization } from "./PipelineUtilization";

const TopologyVisualizer = dynamic(
  () => import("./TopologyVisualizer").then((mod) => mod.TopologyVisualizer),
  { ssr: false }
);

interface DashboardProps {
  tab: string;
  connected: boolean;
}

function StatCard({ label, value, unit, color = "text-accent-cyan" }: {
  label: string;
  value: string | number;
  unit?: string;
  color?: string;
}) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${color}`}>
        {value}
        {unit && <span className="text-sm text-text-secondary ml-1">{unit}</span>}
      </div>
    </div>
  );
}

function HardwareStatusCard() {
  const { connected, tpsData, diagnosticNodes, thermalData } = useTelemetry();

  const hasRecentTps = tpsData.length > 0;
  const hasSwarmNodes = diagnosticNodes.length > 0;
  const hasAnalogData = thermalData.length > 0;

  const modules: { label: string; status: "ONLINE" | "ACTIVE" | "IDLE" | "OFFLINE" }[] = [
    { label: "Observer", status: connected ? "ONLINE" : "OFFLINE" },
    { label: "FPGA Core", status: connected ? (hasRecentTps ? "ACTIVE" : "IDLE") : "OFFLINE" },
    { label: "Swarm Mesh", status: connected ? (hasSwarmNodes ? "ACTIVE" : "IDLE") : "OFFLINE" },
    { label: "Analog Array", status: connected ? (hasAnalogData ? "ACTIVE" : "IDLE") : "OFFLINE" },
    { label: "CIM Array", status: connected ? "IDLE" : "OFFLINE" },
    { label: "Neuromorphic", status: connected ? "IDLE" : "OFFLINE" },
  ];

  const statusStyle: Record<string, string> = {
    ONLINE: "bg-accent-green/20 text-accent-green",
    ACTIVE: "bg-accent-cyan/20 text-accent-cyan",
    IDLE: "bg-bg-tertiary text-text-secondary",
    OFFLINE: "bg-accent-red/20 text-accent-red",
  };

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-amber mb-3">HARDWARE STATUS</h3>
      <div className="space-y-2">
        {modules.map(({ label, status }) => (
          <div key={label} className="flex justify-between items-center">
            <span className="text-sm">{label}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${statusStyle[status]}`}>
              {status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function OverviewDashboard() {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-accent-cyan">System Overview</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Tokens/sec" value="124.5" color="text-accent-cyan" />
        <StatCard label="Active Nodes" value="16/16" color="text-accent-green" />
        <StatCard label="Temperature" value="42" unit="°C" color="text-accent-amber" />
        <StatCard label="Power Draw" value="12.4" unit="W" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TokensPerSecondChart />
        <MemoryBandwidthChart />
        <ThermalDriftChart />
        <CompilationTimeline />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <PipelineView />
        <DiagnosticsHeatmap />
        <CostEstimator />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <SpeculativeDecodingPanel />
        <CarbonCostPanel />
        <PipelineUtilization />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <HardwareStatusCard />

        <div className="stat-card">
          <h3 className="text-sm font-bold text-accent-amber mb-3">RECENT ACTIVITY</h3>
          <div className="space-y-2 text-xs text-text-secondary">
            <div className="flex gap-2">
              <span className="text-accent-cyan">14:32:01</span>
              <span>Model compiled: tinyllama-1.1b</span>
            </div>
            <div className="flex gap-2">
              <span className="text-accent-cyan">14:31:45</span>
              <span>Flash complete: 16/16 nodes</span>
            </div>
            <div className="flex gap-2">
              <span className="text-accent-cyan">14:30:22</span>
              <span>Pre-flight check: PASSED</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function FusionDashboard() {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-accent-cyan">FPGA Fusion</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard label="Clock Speed" value="300" unit="MHz" color="text-accent-cyan" />
        <StatCard label="DSP Utilization" value="72" unit="%" color="text-accent-green" />
        <StatCard label="Memory BW" value="412" unit="GB/s" />
      </div>
      <div className="stat-card">
        <h3 className="text-sm font-bold text-accent-amber mb-3">MAC ARRAY STATUS</h3>
        <div className="grid grid-cols-8 gap-1">
          {Array.from({ length: 64 }).map((_, i) => (
            <div
              key={i}
              className={`w-full aspect-square rounded-sm ${
                i < 46 ? "bg-accent-cyan/60" : "bg-bg-tertiary"
              }`}
              title={`MAC ${i}: ${i < 46 ? "Active" : "Idle"}`}
            />
          ))}
        </div>
        <p className="text-xs text-text-secondary mt-2">46/64 MAC units active</p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ErrorPanel />
        <MemoryBandwidthChart />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <RiscVIsaPanel />
        <PhotonTargetCard />
        <ModelSwitcher />
      </div>
    </div>
  );
}

function AlloyDashboard() {
  const [topologyType, setTopologyType] = useState<"grid2d" | "star" | "ring" | "mesh">("grid2d");
  const [nodeCount, setNodeCount] = useState(16);

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-accent-cyan">Swarm Alloy</h2>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard label="Nodes Online" value={`${nodeCount}/${nodeCount}`} color="text-accent-green" />
        <StatCard label="Avg Latency" value="2.3" unit="ms" color="text-accent-amber" />
        <StatCard label="Messages/sec" value="1,240" />
        <StatCard label="Total Memory" value="8.2" unit="MB" />
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="stat-card flex items-center gap-3">
          <span className="stat-label">TOPOLOGY</span>
          <div className="flex gap-1">
            {(["grid2d", "star", "ring", "mesh"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTopologyType(t)}
                className={`px-2 py-1 rounded text-xs transition-colors ${
                  topologyType === t
                    ? "bg-accent-cyan/20 text-accent-cyan border border-accent-cyan/50"
                    : "bg-bg-tertiary text-text-secondary border border-border hover:border-accent-cyan/30"
                }`}
              >
                {t === "grid2d" ? "Grid" : t === "star" ? "Star" : t === "ring" ? "Ring" : "Mesh"}
              </button>
            ))}
          </div>
        </div>
        <div className="stat-card flex items-center gap-3">
          <span className="stat-label">NODES</span>
          <input
            type="range"
            min="4"
            max="32"
            value={nodeCount}
            onChange={(e) => setNodeCount(parseInt(e.target.value))}
            className="w-24 accent-accent-cyan"
          />
          <span className="text-accent-cyan font-mono text-sm w-6">{nodeCount}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <TopologyVisualizer
            topologyType={topologyType}
            nodeCount={nodeCount}
            className="h-[500px]"
          />
        </div>
        <div className="space-y-4">
          <LatencyHeatmap />
          <AutoDiscoveryPanel discovered topologyType={topologyType} nodeCount={nodeCount} />
          <div className="stat-card">
            <h3 className="text-sm font-bold text-accent-amber mb-3">SWARM STATS</h3>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-text-secondary">Topology</span>
                <span className="text-accent-cyan">{topologyType.toUpperCase()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Active Edges</span>
                <span>{nodeCount * 2}/{nodeCount * 2}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Avg Hop Count</span>
                <span>{topologyType === "star" ? "2.0" : topologyType === "ring" ? (nodeCount / 4).toFixed(1) : "1.5"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Bandwidth</span>
                <span>1.2 GB/s</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TokensPerSecondChart />
        <MemoryBandwidthChart />
        <AlloyTuneReport />
        <IntermittentDashboard />
        <OtaHeatmap />
        <ZephyrTargetCard />
      </div>
    </div>
  );
}

function ElementDashboard() {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-accent-cyan">Analog Element</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard label="Confidence" value="94.2" unit="%" color="text-accent-green" />
        <StatCard label="Temperature" value="28.5" unit="°C" color="text-accent-amber" />
        <StatCard label="Drift" value="0.12" unit="%" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ThermalDriftChart />
        <PowerChart />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="stat-card">
          <h3 className="text-sm font-bold text-accent-amber mb-3">THERMAL MAP</h3>
          <div className="grid grid-cols-8 gap-1">
            {Array.from({ length: 32 }).map((_, i) => {
              const temp = 25 + Math.random() * 10;
              const hue = Math.max(0, 120 - (temp - 25) * 8);
              return (
                <div
                  key={i}
                  className="aspect-square rounded-sm"
                  style={{ backgroundColor: `hsl(${hue}, 70%, 50%)` }}
                  title={`Node ${i}: ${temp.toFixed(1)}°C`}
                />
              );
            })}
          </div>
          <p className="text-xs text-text-secondary mt-2">All components within tolerance</p>
        </div>
        <PcbVisualizer />
      </div>
    </div>
  );
}

function PackageDashboard() {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-accent-cyan">Package Manager</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PackageManifestViewer />
        <div className="stat-card">
          <h3 className="text-sm font-bold text-accent-amber mb-3">COMPILATION STATUS</h3>
          <div className="space-y-2">
            {[
              { name: "Alloy (Swarm)", status: "complete", progress: 100 },
              { name: "Fusion (FPGA)", status: "complete", progress: 100 },
              { name: "Element (Analog)", status: "in_progress", progress: 67 },
              { name: "Silicon (CIM)", status: "pending", progress: 0 },
              { name: "Pulse (Neuro)", status: "pending", progress: 0 },
            ].map((item) => (
              <div key={item.name}>
                <div className="flex justify-between text-sm mb-1">
                  <span>{item.name}</span>
                  <span className={item.status === "complete" ? "text-accent-green" : item.status === "in_progress" ? "text-accent-amber" : "text-text-secondary"}>
                    {item.progress}%
                  </span>
                </div>
                <div className="h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      item.status === "complete" ? "bg-accent-green" : item.status === "in_progress" ? "bg-accent-amber" : "bg-bg-tertiary"
                    }`}
                    style={{ width: `${item.progress}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4">
            <RegressionBadge baseline={0.85} current={0.87} />
            <span className="text-xs text-text-secondary ml-2">vs. previous build</span>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <BomTab />
        <SparsityHeatmap />
        <QuantizationMap />
        <DownloadPanel />
      </div>
    </div>
  );
}

export function Dashboard({ tab, connected }: DashboardProps) {
  return (
    <div>
      {!connected && (
        <div className="mb-4 p-3 bg-accent-red/10 border border-accent-red/30 rounded text-sm text-accent-red">
          Not connected to Observer backend. Telemetry data may be stale.
        </div>
      )}
      {tab === "overview" && <OverviewDashboard />}
      {tab === "fusion" && <FusionDashboard />}
      {tab === "alloy" && <AlloyDashboard />}
      {tab === "element" && <ElementDashboard />}
      {tab === "pkg" && <PackageDashboard />}
    </div>
  );
}
