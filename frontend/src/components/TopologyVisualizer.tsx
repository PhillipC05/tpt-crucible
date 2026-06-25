"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls, Text, Line } from "@react-three/drei";
import { useMemo, useState } from "react";
import * as THREE from "three";

interface NodeData {
  id: number;
  position: [number, number, number];
  status: "online" | "offline" | "busy";
  latency_ms: number;
  layers: number[];
}

interface EdgeData {
  from: number;
  to: number;
  active: boolean;
}

function getTopologyPositions(
  type: "grid2d" | "star" | "ring" | "mesh",
  count: number
): [number, number, number][] {
  const positions: [number, number, number][] = [];

  if (type === "grid2d") {
    const cols = Math.ceil(Math.sqrt(count));
    for (let i = 0; i < count; i++) {
      const row = Math.floor(i / cols);
      const col = i % cols;
      positions.push([col * 2 - (cols - 1), 0, row * 2 - (Math.ceil(count / cols) - 1)]);
    }
  } else if (type === "star") {
    positions.push([0, 0, 0]);
    for (let i = 1; i < count; i++) {
      const angle = ((i - 1) / (count - 1)) * Math.PI * 2;
      positions.push([Math.cos(angle) * 3, 0, Math.sin(angle) * 3]);
    }
  } else if (type === "ring") {
    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2;
      positions.push([Math.cos(angle) * 3, 0, Math.sin(angle) * 3]);
    }
  } else {
    for (let i = 0; i < count; i++) {
      const phi = Math.acos(1 - (2 * (i + 0.5)) / count);
      const theta = Math.PI * (1 + Math.sqrt(5)) * i;
      positions.push([
        Math.sin(phi) * Math.cos(theta) * 3,
        Math.sin(phi) * Math.sin(theta) * 3,
        Math.cos(phi) * 3,
      ]);
    }
  }
  return positions;
}

function getEdges(
  type: "grid2d" | "star" | "ring" | "mesh",
  count: number
): EdgeData[] {
  const edges: EdgeData[] = [];
  if (type === "grid2d") {
    const cols = Math.ceil(Math.sqrt(count));
    for (let i = 0; i < count; i++) {
      if (i + 1 < count && (i + 1) % cols !== 0) edges.push({ from: i, to: i + 1, active: true });
      if (i + cols < count) edges.push({ from: i, to: i + cols, active: true });
    }
  } else if (type === "star") {
    for (let i = 1; i < count; i++) edges.push({ from: 0, to: i, active: true });
  } else if (type === "ring") {
    for (let i = 0; i < count; i++) edges.push({ from: i, to: (i + 1) % count, active: true });
  } else {
    for (let i = 0; i < count; i++) {
      for (let j = i + 1; j < count; j++) {
        if (Math.random() > 0.6) edges.push({ from: i, to: j, active: Math.random() > 0.3 });
      }
    }
  }
  return edges;
}

const statusColors = {
  online: "#3fb950",
  offline: "#f85149",
  busy: "#ffab00",
};

function SwarmNode({
  node,
  selected,
  onSelect,
}: {
  node: NodeData;
  selected: boolean;
  onSelect: () => void;
}) {
  const color = statusColors[node.status];
  return (
    <group position={node.position} onClick={onSelect}>
      <mesh>
        <sphereGeometry args={[selected ? 0.35 : 0.25, 16, 16]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={selected ? 0.5 : 0.2}
          transparent
          opacity={0.9}
        />
      </mesh>
      {selected && (
        <mesh>
          <ringGeometry args={[0.4, 0.5, 32]} />
          <meshBasicMaterial color="#00e5ff" side={THREE.DoubleSide} />
        </mesh>
      )}
      <Text
        position={[0, 0.5, 0]}
        fontSize={0.15}
        color="#c9d1d9"
        anchorX="center"
        anchorY="bottom"
      >
        N{node.id}
      </Text>
    </group>
  );
}

function ConnectionLine({
  from,
  to,
  active,
}: {
  from: [number, number, number];
  to: [number, number, number];
  active: boolean;
}) {
  return (
    <Line
      points={[from, to]}
      color={active ? "#00e5ff" : "#30363d"}
      lineWidth={active ? 2 : 1}
      transparent
      opacity={active ? 0.6 : 0.2}
    />
  );
}

function Scene({
  nodes,
  edges,
  selectedNode,
  onSelectNode,
}: {
  nodes: NodeData[];
  edges: EdgeData[];
  selectedNode: number | null;
  onSelectNode: (id: number | null) => void;
}) {
  return (
    <>
      <ambientLight intensity={0.4} />
      <pointLight position={[10, 10, 10]} intensity={0.8} />
      <pointLight position={[-10, -10, -10]} intensity={0.3} />

      {edges.map((edge, i) => {
        const fromNode = nodes.find((n) => n.id === edge.from);
        const toNode = nodes.find((n) => n.id === edge.to);
        if (!fromNode || !toNode) return null;
        return (
          <ConnectionLine
            key={i}
            from={fromNode.position}
            to={toNode.position}
            active={edge.active}
          />
        );
      })}

      {nodes.map((node) => (
        <SwarmNode
          key={node.id}
          node={node}
          selected={selectedNode === node.id}
          onSelect={() =>
            onSelectNode(selectedNode === node.id ? null : node.id)
          }
        />
      ))}

      <OrbitControls
        enablePan
        enableZoom
        enableRotate
        minDistance={3}
        maxDistance={20}
      />
    </>
  );
}

export function TopologyVisualizer({
  topologyType = "grid2d",
  nodeCount = 16,
  className = "",
}: {
  topologyType?: "grid2d" | "star" | "ring" | "mesh";
  nodeCount?: number;
  className?: string;
}) {
  const [selectedNode, setSelectedNode] = useState<number | null>(null);

  const { nodes, edges } = useMemo(() => {
    const positions = getTopologyPositions(topologyType, nodeCount);
    const edgeData = getEdges(topologyType, nodeCount);

    const nodeData: NodeData[] = positions.map((pos, i) => ({
      id: i,
      position: pos,
      status: Math.random() > 0.1 ? "online" : Math.random() > 0.5 ? "busy" : "offline",
      latency_ms: 1 + Math.random() * 4,
      layers: [i * 4, i * 4 + 1, i * 4 + 2, i * 4 + 3],
    }));

    return { nodes: nodeData, edges: edgeData };
  }, [topologyType, nodeCount]);

  const selectedData = selectedNode !== null ? nodes[selectedNode] : null;

  return (
    <div className={`relative ${className}`}>
      <div className="absolute top-3 left-3 z-10">
        <div className="stat-card text-xs space-y-1">
          <div className="text-accent-amber font-bold mb-2">TOPOLOGY</div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-[#3fb950]" />
            <span>Online ({nodes.filter((n) => n.status === "online").length})</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-[#ffab00]" />
            <span>Busy ({nodes.filter((n) => n.status === "busy").length})</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-[#f85149]" />
            <span>Offline ({nodes.filter((n) => n.status === "offline").length})</span>
          </div>
          <div className="mt-2 text-text-secondary">
            Edges: {edges.filter((e) => e.active).length}/{edges.length}
          </div>
        </div>
      </div>

      {selectedData && (
        <div className="absolute top-3 right-3 z-10">
          <div className="stat-card text-xs space-y-1 w-48">
            <div className="text-accent-cyan font-bold">NODE {selectedData.id}</div>
            <div>Status: <span className={selectedData.status === "online" ? "text-accent-green" : selectedData.status === "busy" ? "text-accent-amber" : "text-accent-red"}>{selectedData.status.toUpperCase()}</span></div>
            <div>Latency: {selectedData.latency_ms.toFixed(1)} ms</div>
            <div>Layers: {selectedData.layers.join(", ")}</div>
          </div>
        </div>
      )}

      <Canvas
        camera={{ position: [8, 6, 8], fov: 50 }}
        className="bg-bg-primary"
        style={{ borderRadius: "8px", border: "1px solid #30363d" }}
      >
        <Scene
          nodes={nodes}
          edges={edges}
          selectedNode={selectedNode}
          onSelectNode={setSelectedNode}
        />
      </Canvas>
    </div>
  );
}
