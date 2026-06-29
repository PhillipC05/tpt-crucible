"""Physical Topology Auto-Discovery — discover swarm layout via RTT probing."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json
import math
from pathlib import Path

from .topology import Topology, TopologyType


@dataclass
class RttMeasurement:
    src: int
    dst: int
    rtt_ms: float
    success: bool = True


@dataclass
class DiscoveryConfig:
    node_count: int = 16
    timeout_s: float = 30.0
    ping_interval_ms: int = 50
    retries: int = 3
    wifi_ssid: str = ""
    coordinator_port: int = 8080


@dataclass
class DiscoveryResult:
    rtt_matrix: list[list[float]]
    inferred_topology: Topology | None = None
    measurements: list[RttMeasurement] = field(default_factory=list)
    success: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "success": self.success,
            "node_count": len(self.rtt_matrix),
            "measurements": len(self.measurements),
        }
        if self.inferred_topology:
            result["topology_type"] = self.inferred_topology.type.value
        if self.error:
            result["error"] = self.error
        return result


class TopologyDiscovery:
    """Broadcast RTT probing and minimum spanning tree inference."""

    def __init__(self, config: DiscoveryConfig):
        self.config = config
        self.rtt_matrix: list[list[float]] = [
            [0.0] * config.node_count for _ in range(config.node_count)
        ]
        self.measurements: list[RttMeasurement] = []

    def simulate_broadcast(self) -> list[RttMeasurement]:
        """Simulate RTT broadcast between all node pairs.

        In production, this sends WiFi UDP pings from each node.
        Here we model it as a grid with distance-based latency.
        """
        n = self.config.node_count
        side = int(math.sqrt(n)) or 1
        measurements = []

        for i in range(n):
            for j in range(i + 1, n):
                ri, ci = divmod(i, side)
                rj, cj = divmod(j, side)
                manhattan = abs(ri - rj) + abs(ci - cj)
                base_rtt = 1.0 + manhattan * 0.5
                self.rtt_matrix[i][j] = base_rtt
                self.rtt_matrix[j][i] = base_rtt
                measurements.append(RttMeasurement(src=i, dst=j, rtt_ms=base_rtt))

        self.measurements = measurements
        return measurements

    def receive_report(self, measurements: list[RttMeasurement]) -> None:
        """Aggregate RTT measurements from nodes into the matrix."""
        for m in measurements:
            if m.src < len(self.rtt_matrix) and m.dst < len(self.rtt_matrix):
                self.rtt_matrix[m.src][m.dst] = m.rtt_ms
                self.rtt_matrix[m.dst][m.src] = m.rtt_ms
                self.measurements.append(m)

    def infer_topology(self) -> Topology:
        """Reconstruct graph from RTT matrix using minimum spanning tree."""
        n = len(self.rtt_matrix)
        edges: list[tuple[float, int, int]] = []

        for i in range(n):
            for j in range(i + 1, n):
                if self.rtt_matrix[i][j] > 0:
                    edges.append((self.rtt_matrix[i][j], i, j))

        edges.sort(key=lambda e: e[0])

        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        mst_edges: list[list[int]] = [[] for _ in range(n)]
        mst_count = 0
        for rtt, u, v in edges:
            ru, rv = find(u), find(v)
            if ru != rv:
                parent[ru] = rv
                mst_edges[u].append(v)
                mst_edges[v].append(u)
                mst_count += 1
                if mst_count == n - 1:
                    break

        return Topology.custom(mst_edges)

    def discover(self) -> DiscoveryResult:
        """Run full discovery: broadcast, aggregate, infer."""
        try:
            self.simulate_broadcast()
            topology = self.infer_topology()
            return DiscoveryResult(
                rtt_matrix=self.rtt_matrix,
                inferred_topology=topology,
                measurements=self.measurements,
                success=True,
            )
        except Exception as e:
            return DiscoveryResult(
                rtt_matrix=self.rtt_matrix,
                success=False,
                error=str(e),
            )


def save_topology(topology: Topology, path: Path) -> None:
    """Save inferred topology to topology.json."""
    n = topology.node_count()
    adj: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        adj[i] = topology.neighbors(i)

    data = {
        "type": topology.type.value,
        "node_count": n,
        "adjacency": adj,
    }
    path.write_text(json.dumps(data, indent=2))


def load_topology(path: Path) -> Topology:
    """Load topology from a JSON file."""
    data = json.loads(path.read_text())
    topo_type = TopologyType(data.get("type", "custom"))
    adjacency = data.get("adjacency", [])
    if topo_type == TopologyType.GRID_2D:
        n = data.get("node_count", len(adjacency))
        side = int(math.sqrt(n)) or 1
        return Topology.grid2d(side, side)
    return Topology.custom(adjacency)
