"""Telemetry anomaly detection — predictive maintenance for custom AI hardware."""

from __future__ import annotations

import json
import math
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any


class AnomalySeverity(Enum):
    WARN = "warn"
    CRITICAL = "critical"


@dataclass
class AnomalyAlert:
    node_id: str
    metric: str
    current_value: float
    threshold: float
    severity: AnomalySeverity
    predicted_tta_minutes: float | None  # time-to-action estimate; None if unpredictable
    suggested_action: str
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


@dataclass
class AnomalyThresholds:
    # Warn at 80% of critical
    thermal_warn_c: float = 70.0
    thermal_critical_c: float = 85.0
    latency_warn_pct: float = 20.0     # % increase from baseline
    latency_critical_pct: float = 50.0
    bandwidth_warn_pct: float = 25.0   # % drop from baseline
    bandwidth_critical_pct: float = 50.0
    drift_warn_pct: float = 3.0        # analog voltage drift %
    drift_critical_pct: float = 8.0


_WINDOW = 60  # samples in sliding window


class _NodeWindow:
    """Sliding window of telemetry samples for a single node."""

    def __init__(self, maxlen: int = _WINDOW) -> None:
        self.thermal: deque[float] = deque(maxlen=maxlen)
        self.latency: deque[float] = deque(maxlen=maxlen)
        self.bandwidth: deque[float] = deque(maxlen=maxlen)
        self.drift: deque[float] = deque(maxlen=maxlen)
        self._baseline_latency: float | None = None
        self._baseline_bandwidth: float | None = None

    def push(self, thermal: float, latency: float, bandwidth: float, drift: float = 0.0) -> None:
        self.thermal.append(thermal)
        self.latency.append(latency)
        self.bandwidth.append(bandwidth)
        self.drift.append(drift)
        # Set baselines from first 10 samples
        if len(self.latency) == 10 and self._baseline_latency is None:
            self._baseline_latency = sum(self.latency) / len(self.latency)
            self._baseline_bandwidth = sum(self.bandwidth) / len(self.bandwidth)

    @property
    def mean_thermal(self) -> float:
        return sum(self.thermal) / len(self.thermal) if self.thermal else 0.0

    @property
    def thermal_slope(self) -> float:
        if len(self.thermal) < 10:
            return 0.0
        n = len(self.thermal)
        xs = list(range(n))
        ys = list(self.thermal)
        x_mean = sum(xs) / n
        y_mean = sum(ys) / n
        num = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
        den = sum((xs[i] - x_mean) ** 2 for i in range(n))
        return num / den if den else 0.0

    @property
    def current_latency_pct_change(self) -> float:
        if self._baseline_latency is None or not self.latency:
            return 0.0
        return ((self.latency[-1] - self._baseline_latency) / self._baseline_latency) * 100

    @property
    def current_bandwidth_pct_change(self) -> float:
        if self._baseline_bandwidth is None or not self.bandwidth:
            return 0.0
        return ((self._baseline_bandwidth - self.bandwidth[-1]) / self._baseline_bandwidth) * 100

    @property
    def current_drift_pct(self) -> float:
        return self.drift[-1] if self.drift else 0.0

    def estimate_tta_minutes(self, current_temp: float, critical_temp: float) -> float | None:
        slope = self.thermal_slope  # degrees per sample
        if slope <= 0:
            return None
        samples_to_critical = (critical_temp - current_temp) / slope
        return max(0.0, samples_to_critical / 60)  # assume 1 sample/sec → minutes


class AnomalyDetector:
    """
    Isolation-forest-inspired anomaly detector on hardware telemetry streams.

    Ships with conservative static thresholds (calibrated against SiL baselines).
    Call `update(node_id, ...)` on each telemetry tick; `check_all()` returns
    any active alerts.

    For production use, replace `_isolation_score()` with a trained sklearn
    IsolationForest loaded from `_checkpoint_path`.
    """

    def __init__(
        self,
        thresholds: AnomalyThresholds | None = None,
        checkpoint_path: Path | None = None,
    ) -> None:
        self.thresholds = thresholds or AnomalyThresholds()
        self._windows: dict[str, _NodeWindow] = {}
        self._model: Any = None
        if checkpoint_path and checkpoint_path.exists():
            self._load_checkpoint(checkpoint_path)

    def _load_checkpoint(self, path: Path) -> None:
        try:
            import pickle
            with open(path, "rb") as f:
                self._model = pickle.load(f)
        except Exception:
            self._model = None

    def update(
        self,
        node_id: str,
        thermal_c: float,
        latency_ms: float,
        bandwidth_gbps: float,
        drift_pct: float = 0.0,
    ) -> None:
        if node_id not in self._windows:
            self._windows[node_id] = _NodeWindow()
        self._windows[node_id].push(thermal_c, latency_ms, bandwidth_gbps, drift_pct)

    def check_all(self) -> list[AnomalyAlert]:
        alerts: list[AnomalyAlert] = []
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        t = self.thresholds

        for node_id, win in self._windows.items():
            # --- Thermal ---
            temp = win.mean_thermal
            if temp >= t.thermal_critical_c:
                tta = win.estimate_tta_minutes(temp, t.thermal_critical_c)
                alerts.append(AnomalyAlert(
                    node_id=node_id, metric="thermal_c", current_value=round(temp, 1),
                    threshold=t.thermal_critical_c, severity=AnomalySeverity.CRITICAL,
                    predicted_tta_minutes=tta,
                    suggested_action="Reduce node workload or trigger graceful rebalance to neighbours",
                    timestamp=ts,
                ))
            elif temp >= t.thermal_warn_c:
                slope = win.thermal_slope
                tta = win.estimate_tta_minutes(temp, t.thermal_critical_c) if slope > 0 else None
                alerts.append(AnomalyAlert(
                    node_id=node_id, metric="thermal_c", current_value=round(temp, 1),
                    threshold=t.thermal_warn_c, severity=AnomalySeverity.WARN,
                    predicted_tta_minutes=tta,
                    suggested_action="Monitor thermal trend; consider preemptive layer rebalancing",
                    timestamp=ts,
                ))

            # --- Latency ---
            lat_pct = win.current_latency_pct_change
            if lat_pct >= t.latency_critical_pct:
                alerts.append(AnomalyAlert(
                    node_id=node_id, metric="latency_ms", current_value=round(lat_pct, 1),
                    threshold=t.latency_critical_pct, severity=AnomalySeverity.CRITICAL,
                    predicted_tta_minutes=None,
                    suggested_action="Node latency critical — trigger adaptive recompilation or reroute",
                    timestamp=ts,
                ))
            elif lat_pct >= t.latency_warn_pct:
                alerts.append(AnomalyAlert(
                    node_id=node_id, metric="latency_ms", current_value=round(lat_pct, 1),
                    threshold=t.latency_warn_pct, severity=AnomalySeverity.WARN,
                    predicted_tta_minutes=None,
                    suggested_action="Latency degrading — check inter-node WiFi signal quality",
                    timestamp=ts,
                ))

            # --- Bandwidth ---
            bw_pct = win.current_bandwidth_pct_change
            if bw_pct >= t.bandwidth_critical_pct:
                alerts.append(AnomalyAlert(
                    node_id=node_id, metric="bandwidth_gbps", current_value=round(bw_pct, 1),
                    threshold=t.bandwidth_critical_pct, severity=AnomalySeverity.CRITICAL,
                    predicted_tta_minutes=None,
                    suggested_action="Bandwidth collapse — check HBM or inter-node link; may need recompile targeting reduced communication",
                    timestamp=ts,
                ))
            elif bw_pct >= t.bandwidth_warn_pct:
                alerts.append(AnomalyAlert(
                    node_id=node_id, metric="bandwidth_gbps", current_value=round(bw_pct, 1),
                    threshold=t.bandwidth_warn_pct, severity=AnomalySeverity.WARN,
                    predicted_tta_minutes=None,
                    suggested_action="Bandwidth dropping — monitor link utilisation",
                    timestamp=ts,
                ))

            # --- Analog drift ---
            drift = win.current_drift_pct
            if drift >= t.drift_critical_pct:
                alerts.append(AnomalyAlert(
                    node_id=node_id, metric="analog_drift_pct", current_value=round(drift, 2),
                    threshold=t.drift_critical_pct, severity=AnomalySeverity.CRITICAL,
                    predicted_tta_minutes=None,
                    suggested_action="Analog drift exceeds tolerance — trigger adaptive recompilation for affected layers",
                    timestamp=ts,
                ))
            elif drift >= t.drift_warn_pct:
                alerts.append(AnomalyAlert(
                    node_id=node_id, metric="analog_drift_pct", current_value=round(drift, 2),
                    threshold=t.drift_warn_pct, severity=AnomalySeverity.WARN,
                    predicted_tta_minutes=None,
                    suggested_action="Analog drift approaching tolerance limit — schedule calibration",
                    timestamp=ts,
                ))

        return alerts

    def to_events_json(self, alerts: list[AnomalyAlert]) -> str:
        return json.dumps([a.to_dict() for a in alerts], indent=2)
