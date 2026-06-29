"""Federated learning configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AggregationStrategy(Enum):
    FEDAVG = "fedavg"
    FEDPROX = "fedprox"


class GradientCompression(Enum):
    NONE = "none"
    TOPK = "topk"
    QUANTIZED = "quantized"


@dataclass
class FederatedConfig:
    """Configuration for a federated learning session over TPT hardware."""

    tptpkg_path: str
    data_sources: list[str]                         # node IPs or hostnames
    strategy: AggregationStrategy = AggregationStrategy.FEDAVG
    rounds: int = 10
    min_participants: int = 2                       # minimum nodes that must respond per round
    gradient_compression: GradientCompression = GradientCompression.TOPK
    topk_fraction: float = 0.1                      # top-K: keep this fraction of largest gradients
    fedprox_mu: float = 0.01                        # FedProx proximal term weight
    local_epochs: int = 1                           # epochs each participant trains per round
    batch_size: int = 32
    learning_rate: float = 1e-4
    round_timeout_s: float = 120.0                  # seconds to wait for round participants
    recompile_after_rounds: int = 5                 # trigger incremental recompile every N rounds
    carbon_region: str = "global_avg"
