"""Alloy SiL — Virtual N-node swarm simulator."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import time
import random

from .interface import EmulatorInterface, EmulatorResult, HardwareType, TelemetryPoint


@dataclass
class VirtualNode:
    node_id: int
    layers: list[int]
    latency_ms: float = 0.0
    memory_usage_kb: float = 0.0


class AlloySil(EmulatorInterface):
    """Virtual swarm simulator with message-passing and inter-node latency model."""

    def __init__(self, node_count: int = 16):
        super().__init__(HardwareType.ALLOY)
        self.node_count = node_count
        self.nodes: list[VirtualNode] = []
        self.message_latency_ms = 0.5
        self.inter_node_jitter_ms = 0.1

    def load_model(self, model_path: str) -> bool:
        self.nodes = [
            VirtualNode(
                node_id=i,
                layers=list(range(i, self.node_count * 4, self.node_count)),
            )
            for i in range(self.node_count)
        ]
        return True

    def run_inference(self, input_data: Any) -> EmulatorResult:
        start = time.time()
        total_latency = 0.0

        for node in self.nodes:
            node.latency_ms = self.message_latency_ms + random.uniform(0, self.inter_node_jitter_ms)
            node.memory_usage_kb = 256 + random.uniform(0, 128)
            total_latency += node.latency_ms

            self._record_telemetry(f"node_{node.node_id}", {
                "latency_ms": node.latency_ms,
                "memory_usage_kb": node.memory_usage_kb,
                "layers_computed": len(node.layers),
                "status": "running",
            })

        elapsed_ms = (time.time() - start) * 1000
        tps = 1000.0 / max(total_latency, 1.0)

        return EmulatorResult(
            success=True,
            telemetry=list(self.telemetry_log[-self.node_count:]),
            inference_time_ms=elapsed_ms + total_latency,
            tokens_per_second=tps,
            metadata={"node_count": self.node_count, "total_latency_ms": total_latency},
        )

    def get_telemetry(self) -> list[TelemetryPoint]:
        return list(self.telemetry_log)
