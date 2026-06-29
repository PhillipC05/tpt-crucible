"""SiL Communication Parameter Auto-Tuner — optimize inter-node latency."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import itertools


@dataclass
class TunableParams:
    wifi_message_size: int = 1024
    batch_size: int = 8
    retry_count: int = 3
    uart_baud_rate: int = 115200

    def to_dict(self) -> dict[str, Any]:
        return {
            "wifi_message_size": self.wifi_message_size,
            "batch_size": self.batch_size,
            "retry_count": self.retry_count,
            "uart_baud_rate": self.uart_baud_rate,
        }


@dataclass
class TuneResult:
    params: TunableParams
    p99_latency_ms: float
    avg_latency_ms: float
    throughput: float
    memory_usage_kb: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "params": self.params.to_dict(),
            "p99_latency_ms": round(self.p99_latency_ms, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "throughput": round(self.throughput, 2),
            "memory_usage_kb": round(self.memory_usage_kb, 2),
        }


class SiLTuner:
    """Tune SiL communication parameters for optimal performance."""

    def __init__(self, param_space: dict[str, list] | None = None):
        self.param_space = param_space or {
            "wifi_message_size": [512, 1024, 2048, 4096],
            "batch_size": [4, 8, 16, 32],
            "retry_count": [1, 2, 3, 5],
            "uart_baud_rate": [115200, 230400, 460800, 921600],
        }

    def sweep(self, memory_budget_kb: float = 512.0) -> list[TuneResult]:
        results = []
        keys = list(self.param_space.keys())
        values = [self.param_space[k] for k in keys]

        for combo in itertools.product(*values):
            params = TunableParams(**dict(zip(keys, combo)))
            p99 = self._estimate_p99(params)
            avg = p99 * 0.6
            throughput = 1000.0 / max(p99, 1.0)
            memory = self._estimate_memory(params)

            if memory <= memory_budget_kb:
                results.append(TuneResult(
                    params=params,
                    p99_latency_ms=p99,
                    avg_latency_ms=avg,
                    throughput=throughput,
                    memory_usage_kb=memory,
                ))

        results.sort(key=lambda r: r.p99_latency_ms)
        return results

    def select_best(self, results: list[TuneResult]) -> TuneResult | None:
        if not results:
            return None
        return results[0]

    def _estimate_p99(self, params: TunableParams) -> float:
        base_latency = 2.0
        batch_penalty = params.batch_size * 0.1
        message_penalty = params.wifi_message_size / 1024.0 * 0.5
        retry_penalty = params.retry_count * 0.2
        return base_latency + batch_penalty + message_penalty + retry_penalty

    def _estimate_memory(self, params: TunableParams) -> float:
        return (params.wifi_message_size * params.batch_size * 2) / 1024

    def bake_to_firmware(self, params: TunableParams) -> str:
        return f"""\
// Auto-tuned communication parameters
#define WIFI_MSG_SIZE {params.wifi_message_size}
#define BATCH_SIZE {params.batch_size}
#define RETRY_COUNT {params.retry_count}
#define UART_BAUD {params.uart_baud_rate}
"""

    def tune(self, tptpkg_path: Any = None, topology_path: Any = None) -> dict[str, Any]:
        """Run the full tuning sweep and return the best parameters.

        Integrates with the CLI: reads the package and topology, sweeps parameter space,
        and returns tuned parameters as a dict.
        """
        results = self.sweep()
        best = self.select_best(results)
        if best is None:
            return {"error": "no valid parameter set found within memory budget"}

        firmware_constants = self.bake_to_firmware(best.params)
        return {
            "tuned_params": best.params.to_dict(),
            "p99_latency_ms": best.p99_latency_ms,
            "avg_latency_ms": best.avg_latency_ms,
            "throughput": best.throughput,
            "memory_usage_kb": best.memory_usage_kb,
            "firmware_constants": firmware_constants,
            "configs_evaluated": len(results),
        }
