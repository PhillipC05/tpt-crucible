"""ShellSession — low-level connection to a hardware deployment or SiL."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TensorSnapshot:
    layer_id: str
    shape: list[int]
    dtype: str
    values: list[float]  # flattened, truncated to 64 elements for display
    is_truncated: bool

    def pretty(self) -> str:
        vals = self.values[:16]
        tail = "..." if self.is_truncated or len(self.values) > 16 else ""
        return (
            f"Tensor[{self.layer_id}] shape={self.shape} dtype={self.dtype}\n"
            f"  [{', '.join(f'{v:.4f}' for v in vals)}{tail}]"
        )


@dataclass
class TelemetrySnapshot:
    nodes: dict[str, dict[str, float]]  # node_id → {tps, thermal_c, latency_ms}

    def pretty(self) -> str:
        lines = ["Telemetry snapshot:"]
        for node, metrics in self.nodes.items():
            parts = ", ".join(f"{k}={v:.2f}" for k, v in metrics.items())
            lines.append(f"  {node}: {parts}")
        return "\n".join(lines)


class ShellSession:
    """
    Connects to TPT hardware or SiL via WebSocket and exposes
    individual-layer execution, tensor inspection, and telemetry.

    The server-side counterpart is the Observer's `/ws/shell` endpoint,
    which proxies commands to the hardware debug interface or SiL runner.
    """

    def __init__(self, ws_url: str, tptpkg_path: Path | str) -> None:
        self.ws_url = ws_url
        self.tptpkg_path = Path(tptpkg_path)
        self._ws: Any = None
        self._layer_ids: list[str] = self._load_layer_ids()

    def _load_layer_ids(self) -> list[str]:
        ir_path = self.tptpkg_path / "ir" / "model.tptir"
        if not ir_path.exists():
            return []
        try:
            data = json.loads(ir_path.read_text())
            return [n["id"] for n in data.get("graph", {}).get("nodes", [])]
        except (json.JSONDecodeError, KeyError):
            return []

    async def connect(self) -> None:
        try:
            import websockets
            self._ws = await websockets.connect(self.ws_url)
        except ImportError:
            raise RuntimeError("websockets package required: pip install websockets")

    async def disconnect(self) -> None:
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def _send(self, cmd: dict[str, Any]) -> dict[str, Any]:
        if not self._ws:
            raise RuntimeError("Not connected — call connect() first")
        await self._ws.send(json.dumps(cmd))
        raw = await asyncio.wait_for(self._ws.recv(), timeout=30.0)
        return json.loads(raw)

    async def run_layer(self, layer_id: str, input_json: str | None = None) -> TensorSnapshot:
        inp = json.loads(input_json) if input_json else None
        resp = await self._send({"cmd": "run_layer", "layer_id": layer_id, "input": inp})
        if resp.get("status") != "ok":
            raise RuntimeError(f"run_layer failed: {resp.get('error', 'unknown error')}")
        t = resp["tensor"]
        values = t.get("values", [])
        return TensorSnapshot(
            layer_id=layer_id,
            shape=t.get("shape", []),
            dtype=t.get("dtype", "float32"),
            values=values[:64],
            is_truncated=len(values) > 64,
        )

    async def inspect(self, tensor_id: str) -> TensorSnapshot:
        resp = await self._send({"cmd": "inspect", "tensor_id": tensor_id})
        if resp.get("status") != "ok":
            raise RuntimeError(f"inspect failed: {resp.get('error', 'unknown error')}")
        t = resp["tensor"]
        values = t.get("values", [])
        return TensorSnapshot(
            layer_id=tensor_id,
            shape=t.get("shape", []),
            dtype=t.get("dtype", "float32"),
            values=values[:64],
            is_truncated=len(values) > 64,
        )

    async def telemetry_snapshot(self) -> TelemetrySnapshot:
        resp = await self._send({"cmd": "telemetry_snapshot"})
        return TelemetrySnapshot(nodes=resp.get("nodes", {}))

    async def diff(self, layer_id: str, input_a: str, input_b: str) -> dict[str, Any]:
        a = await self.run_layer(layer_id, input_a)
        b = await self.run_layer(layer_id, input_b)
        import math
        if len(a.values) != len(b.values):
            return {"error": "output shapes differ"}
        diffs = [abs(x - y) for x, y in zip(a.values, b.values)]
        return {
            "layer_id": layer_id,
            "max_abs_diff": max(diffs) if diffs else 0.0,
            "mean_abs_diff": sum(diffs) / len(diffs) if diffs else 0.0,
            "l2_norm": math.sqrt(sum(d * d for d in diffs)),
        }

    @property
    def layer_ids(self) -> list[str]:
        return self._layer_ids
