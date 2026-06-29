"""Federated Learning Orchestrator — coordinates training rounds across TPT hardware nodes."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .config import FederatedConfig, AggregationStrategy, GradientCompression
from .compression import GradientCompressor, CompressedGradient


@dataclass
class RoundMetrics:
    round_num: int
    participants: int
    loss_delta: float
    accuracy_delta: float
    avg_compression_ratio: float
    duration_s: float
    recompiled: bool = False


@dataclass
class FLSession:
    config: FederatedConfig
    rounds_completed: int = 0
    round_metrics: list[RoundMetrics] = field(default_factory=list)
    final_loss: float | None = None
    status: str = "idle"  # idle | training | complete | failed

    def to_dict(self) -> dict[str, Any]:
        return {
            "rounds_completed": self.rounds_completed,
            "round_metrics": [asdict(m) for m in self.round_metrics],
            "final_loss": self.final_loss,
            "status": self.status,
        }


def _collect_gradients(node_url: str, round_num: int, config: FederatedConfig) -> dict[str, list[float]] | None:
    """
    Request gradient upload from a participant node.
    The node must be running TPT firmware with TPT_FL_MODE enabled.
    Returns layer_id → gradient list, or None on timeout/failure.
    """
    try:
        result = subprocess.run(
            ["tpt-fl-agent", "collect-gradients",
             "--node", node_url,
             "--round", str(round_num),
             "--epochs", str(config.local_epochs),
             "--lr", str(config.learning_rate),
             "--batch-size", str(config.batch_size),
             "--timeout", str(int(config.round_timeout_s))],
            capture_output=True, text=True, timeout=config.round_timeout_s + 10,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, json.JSONDecodeError):
        pass
    return None


def _push_weights(node_url: str, weights: dict[str, list[float]], round_num: int) -> bool:
    """Push aggregated weights back to a participant node."""
    try:
        result = subprocess.run(
            ["tpt-fl-agent", "push-weights", "--node", node_url, "--round", str(round_num)],
            input=json.dumps(weights),
            capture_output=True, text=True, timeout=60,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False


def _fedavg(
    all_gradients: list[dict[str, list[float]]],
    dataset_sizes: list[int],
) -> dict[str, list[float]]:
    """Weighted FedAvg aggregation."""
    total = sum(dataset_sizes)
    weights = [s / total for s in dataset_sizes]
    aggregated: dict[str, list[float]] = {}
    layer_ids = all_gradients[0].keys() if all_gradients else []
    for lid in layer_ids:
        vecs = [g[lid] for g in all_gradients if lid in g]
        if not vecs:
            continue
        n = max(len(v) for v in vecs)
        avg = [
            sum(weights[i] * (vecs[i][j] if j < len(vecs[i]) else 0.0) for i in range(len(vecs)))
            for j in range(n)
        ]
        aggregated[lid] = avg
    return aggregated


def _fedprox(
    all_gradients: list[dict[str, list[float]]],
    dataset_sizes: list[int],
    global_weights: dict[str, list[float]],
    mu: float,
) -> dict[str, list[float]]:
    """FedProx aggregation with proximal regularization term."""
    avg = _fedavg(all_gradients, dataset_sizes)
    # Add proximal term: push aggregated gradient closer to global weights
    for lid, grad in avg.items():
        if lid in global_weights:
            gw = global_weights[lid]
            avg[lid] = [g - mu * (g - (gw[i] if i < len(gw) else 0.0)) for i, g in enumerate(grad)]
    return avg


class FLOrchestrator:
    def __init__(self, config: FederatedConfig) -> None:
        self.config = config
        self._compressor = (
            GradientCompressor(topk_fraction=0.1)
            if config.gradient_compression != GradientCompression.NONE
            else None
        )
        self._global_weights: dict[str, list[float]] = {}

    def run(self) -> FLSession:
        session = FLSession(config=self.config, status="training")
        tptpkg = Path(self.config.tptpkg_path)

        for round_num in range(1, self.config.rounds + 1):
            t0 = time.time()
            print(f"Round {round_num}/{self.config.rounds}...")

            participant_gradients: list[dict[str, list[float]]] = []
            dataset_sizes: list[int] = []
            compression_ratios: list[float] = []

            for node_url in self.config.data_sources:
                raw = _collect_gradients(node_url, round_num, self.config)
                if raw is None:
                    print(f"  Node {node_url}: no response (skipped)")
                    continue

                dataset_size = int(raw.pop("__dataset_size__", 100))
                dataset_sizes.append(dataset_size)

                if self._compressor:
                    compressed = {
                        lid: self._compressor.compress(lid, grad)
                        for lid, grad in raw.items()
                    }
                    decompressed = {lid: c.decompress() for lid, c in compressed.items()}
                    ratios = [c.compression_ratio for c in compressed.values()]
                    if ratios:
                        compression_ratios.append(sum(ratios) / len(ratios))
                    participant_gradients.append(decompressed)
                else:
                    participant_gradients.append(raw)

            if len(participant_gradients) < self.config.min_participants:
                print(f"  Insufficient participants ({len(participant_gradients)} < {self.config.min_participants}); skipping round")
                continue

            # Aggregate
            if self.config.strategy == AggregationStrategy.FEDAVG:
                aggregated = _fedavg(participant_gradients, dataset_sizes or [1] * len(participant_gradients))
            else:
                aggregated = _fedprox(
                    participant_gradients,
                    dataset_sizes or [1] * len(participant_gradients),
                    self._global_weights,
                    self.config.fedprox_mu,
                )

            # Apply aggregated gradients to global weights
            for lid, grad in aggregated.items():
                if lid not in self._global_weights:
                    self._global_weights[lid] = [0.0] * len(grad)
                gw = self._global_weights[lid]
                self._global_weights[lid] = [
                    gw[i] - self.config.learning_rate * (grad[i] if i < len(grad) else 0.0)
                    for i in range(len(gw))
                ]

            # Push updated weights back
            for node_url in self.config.data_sources:
                _push_weights(node_url, self._global_weights, round_num)

            recompiled = False
            if round_num % self.config.recompile_after_rounds == 0:
                print(f"  Triggering incremental recompile after round {round_num}...")
                try:
                    result = subprocess.run(
                        ["tpt-catalyst", "pack", str(tptpkg), "--incremental"],
                        capture_output=True, text=True, timeout=600,
                    )
                    recompiled = result.returncode == 0
                except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                    pass
                if recompiled:
                    # OTA flash updated package
                    subprocess.run(
                        ["tpt-alloy", "ota", "--pkg", str(tptpkg),
                         "--nodes", ",".join(self.config.data_sources)],
                        capture_output=True, timeout=300,
                    )

            duration = time.time() - t0
            metrics = RoundMetrics(
                round_num=round_num,
                participants=len(participant_gradients),
                loss_delta=0.0,  # populated from validation output when available
                accuracy_delta=0.0,
                avg_compression_ratio=(
                    sum(compression_ratios) / len(compression_ratios)
                    if compression_ratios else 1.0
                ),
                duration_s=round(duration, 2),
                recompiled=recompiled,
            )
            session.round_metrics.append(metrics)
            session.rounds_completed = round_num
            print(f"  Done in {duration:.1f}s — {len(participant_gradients)} participants, "
                  f"compression={metrics.avg_compression_ratio:.1f}x")

        session.status = "complete"
        return session
