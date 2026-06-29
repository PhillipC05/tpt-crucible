"""Live Adaptive Recompilation — self-healing hardware deployments triggered by telemetry thresholds."""

from __future__ import annotations

import json
import subprocess
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable


@dataclass
class AdaptiveThresholds:
    analog_drift_pct: float = 5.0        # trigger recompile when analog drift exceeds this
    latency_degradation_pct: float = 20.0  # % increase from baseline
    thermal_delta_c: float = 15.0         # absolute rise from compile-time temperature
    check_interval_s: float = 30.0        # how often to evaluate telemetry


@dataclass
class HealingEvent:
    trigger_metric: str
    trigger_value: float
    threshold: float
    affected_nodes: list[str]
    affected_layers: list[str]
    recompile_started_at: str
    recompile_completed_at: str | None = None
    status: str = "pending"  # pending | recompiling | flashing | complete | failed
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AdaptiveRecompiler:
    """
    Watches a telemetry WebSocket stream and triggers targeted incremental
    recompilation when configured thresholds are exceeded.

    In production, wire `telemetry_callback` to the Observer WebSocket client.
    The recompile is scoped to affected layers only (`tpt-catalyst pack --incremental`).
    After recompilation, the updated firmware is pushed via the OTA pipeline.
    """

    def __init__(
        self,
        tptpkg_path: Path | str,
        thresholds: AdaptiveThresholds | None = None,
        on_healing_event: Callable[[HealingEvent], None] | None = None,
    ) -> None:
        self.tptpkg_path = Path(tptpkg_path)
        self.thresholds = thresholds or AdaptiveThresholds()
        self.on_healing_event = on_healing_event
        self._running = False
        self._thread: threading.Thread | None = None
        self._baseline_latency: dict[str, float] = {}
        self._baseline_thermal: dict[str, float] = {}
        self._latest_telemetry: dict[str, dict[str, float]] = {}
        self._healing_log: list[HealingEvent] = []
        self._lock = threading.Lock()

    def push_telemetry(
        self,
        node_id: str,
        latency_ms: float,
        thermal_c: float,
        analog_drift_pct: float = 0.0,
    ) -> None:
        with self._lock:
            if node_id not in self._baseline_latency:
                self._baseline_latency[node_id] = latency_ms
                self._baseline_thermal[node_id] = thermal_c
            self._latest_telemetry[node_id] = {
                "latency_ms": latency_ms,
                "thermal_c": thermal_c,
                "analog_drift_pct": analog_drift_pct,
            }

    def _evaluate(self) -> list[tuple[str, str, float, float]]:
        """Return list of (node_id, metric, value, threshold) violations."""
        violations = []
        t = self.thresholds
        with self._lock:
            for node_id, readings in self._latest_telemetry.items():
                latency = readings["latency_ms"]
                baseline_lat = self._baseline_latency.get(node_id, latency)
                if baseline_lat > 0:
                    lat_pct = ((latency - baseline_lat) / baseline_lat) * 100
                    if lat_pct >= t.latency_degradation_pct:
                        violations.append((node_id, "latency_degradation_pct", lat_pct, t.latency_degradation_pct))

                thermal = readings["thermal_c"]
                baseline_temp = self._baseline_thermal.get(node_id, thermal)
                delta = thermal - baseline_temp
                if delta >= t.thermal_delta_c:
                    violations.append((node_id, "thermal_delta_c", delta, t.thermal_delta_c))

                drift = readings["analog_drift_pct"]
                if drift >= t.analog_drift_pct:
                    violations.append((node_id, "analog_drift_pct", drift, t.analog_drift_pct))
        return violations

    def _identify_affected_layers(self, node_ids: list[str]) -> list[str]:
        """Read partition plan from .tptpkg and return layer IDs assigned to affected nodes."""
        partition_path = self.tptpkg_path / "mosaic" / "partition.json"
        if not partition_path.exists():
            return []
        try:
            data = json.loads(partition_path.read_text())
            layers = []
            for partition in data.get("partitions", []):
                if partition.get("node_id") in node_ids:
                    layers.extend(partition.get("layer_ids", []))
            return layers
        except (json.JSONDecodeError, KeyError):
            return []

    def _run_incremental_recompile(self, affected_layers: list[str]) -> bool:
        try:
            result = subprocess.run(
                ["tpt-catalyst", "pack", str(self.tptpkg_path), "--incremental"],
                capture_output=True,
                text=True,
                timeout=600,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False

    def _run_ota_flash(self, affected_nodes: list[str]) -> bool:
        try:
            result = subprocess.run(
                ["tpt-alloy", "ota", "--pkg", str(self.tptpkg_path), "--nodes", ",".join(affected_nodes)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False

    def _heal(self, violations: list[tuple[str, str, float, float]]) -> None:
        if not violations:
            return

        # Group by unique nodes
        affected_nodes = list({v[0] for v in violations})
        trigger_metric = violations[0][1]
        trigger_value = violations[0][2]
        threshold = violations[0][3]
        affected_layers = self._identify_affected_layers(affected_nodes)

        event = HealingEvent(
            trigger_metric=trigger_metric,
            trigger_value=trigger_value,
            threshold=threshold,
            affected_nodes=affected_nodes,
            affected_layers=affected_layers,
            recompile_started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            status="recompiling",
        )
        self._healing_log.append(event)
        if self.on_healing_event:
            self.on_healing_event(event)

        ok = self._run_incremental_recompile(affected_layers)
        if ok:
            event.status = "flashing"
            if self.on_healing_event:
                self.on_healing_event(event)
            ok = self._run_ota_flash(affected_nodes)

        event.recompile_completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        event.status = "complete" if ok else "failed"
        if not ok:
            event.error = "Recompile or OTA flash failed — check tpt-catalyst and tpt-alloy logs"
        if self.on_healing_event:
            self.on_healing_event(event)

    def _watch_loop(self) -> None:
        while self._running:
            time.sleep(self.thresholds.check_interval_s)
            if not self._running:
                break
            violations = self._evaluate()
            if violations:
                self._heal(violations)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    @property
    def healing_log(self) -> list[HealingEvent]:
        return list(self._healing_log)
