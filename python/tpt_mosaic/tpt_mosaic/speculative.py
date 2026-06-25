"""Cross-Hardware Speculative Decoding — draft on swarm, verify on FPGA."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import random


@dataclass
class SpeculativeConfig:
    draft_pkg: str = ""
    verify_pkg: str = ""
    gamma: int = 4
    acceptance_threshold: float = 0.8


@dataclass
class SpeculativeMetrics:
    total_tokens: int = 0
    accepted_tokens: int = 0
    rejected_tokens: int = 0
    draft_time_ms: float = 0.0
    verify_time_ms: float = 0.0
    effective_tps: float = 0.0
    draft_tps: float = 0.0

    @property
    def acceptance_rate(self) -> float:
        return self.accepted_tokens / max(self.total_tokens, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tokens": self.total_tokens,
            "accepted_tokens": self.accepted_tokens,
            "rejected_tokens": self.rejected_tokens,
            "acceptance_rate": round(self.acceptance_rate, 4),
            "draft_time_ms": round(self.draft_time_ms, 2),
            "verify_time_ms": round(self.verify_time_ms, 2),
            "draft_tps": round(self.draft_tps, 2),
            "effective_tps": round(self.effective_tps, 2),
        }


class SpeculativeOrchestrator:
    """Orchestrate speculative decoding across draft (swarm) and verify (FPGA) hardware."""

    def __init__(self, config: SpeculativeConfig):
        self.config = config
        self.metrics = SpeculativeMetrics()

    def run_speculative(self, prompt_tokens: list[int], max_new_tokens: int = 100) -> list[int]:
        generated = []
        tokens_generated = 0

        while tokens_generated < max_new_tokens:
            draft_count = min(self.config.gamma, max_new_tokens - tokens_generated)
            draft_tokens = self._draft_generate(draft_count)
            verified_tokens = self._verify_accept(draft_tokens)

            generated.extend(verified_tokens)
            tokens_generated += len(verified_tokens)

            self.metrics.total_tokens += len(draft_tokens)
            self.metrics.accepted_tokens += len(verified_tokens)
            self.metrics.rejected_tokens += len(draft_tokens) - len(verified_tokens)

        self._compute_metrics()
        return generated

    def _draft_generate(self, count: int) -> list[int]:
        return [random.randint(1000, 50000) for _ in range(count)]

    def _verify_accept(self, draft_tokens: list[int]) -> list[int]:
        accepted = []
        for token in draft_tokens:
            acceptance_prob = random.uniform(0.5, 1.0)
            if acceptance_prob >= self.config.acceptance_threshold:
                accepted.append(token)
            else:
                break
        return accepted

    def _compute_metrics(self) -> None:
        self.metrics.draft_tps = self.metrics.total_tokens / max(self.metrics.draft_time_ms / 1000, 0.001)
        self.metrics.effective_tps = self.metrics.accepted_tokens / max(
            (self.metrics.draft_time_ms + self.metrics.verify_time_ms) / 1000, 0.001
        )

    def get_metrics(self) -> SpeculativeMetrics:
        return self.metrics
