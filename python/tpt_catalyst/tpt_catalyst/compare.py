"""Cross-hardware benchmark comparison — run same model through all SiL backends and produce a Pareto report."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .carbon import estimate_carbon, GRID_INTENSITY_GCO2_PER_KWH
from .compat import HardwareTarget


# Baseline hardware profiles used when SiL is unavailable.
# Values are conservative medians derived from datasheets and SiL benchmarks.
_HARDWARE_PROFILES: dict[str, dict[str, float]] = {
    "alloy": {
        "tokens_per_sec_base": 8.5,
        "power_watts": 14.4,       # 16× ESP32 @ 900 mW each
        "cost_usd_hardware": 32.0,
        "latency_ms_per_token": 118.0,
    },
    "fusion": {
        "tokens_per_sec_base": 420.0,
        "power_watts": 75.0,       # Alveo U250 active
        "cost_usd_hardware": 8500.0,
        "latency_ms_per_token": 2.4,
    },
    "element": {
        "tokens_per_sec_base": 55.0,
        "power_watts": 2.8,        # custom analog PCB
        "cost_usd_hardware": 150.0,
        "latency_ms_per_token": 18.0,
    },
    "cim": {
        "tokens_per_sec_base": 280.0,
        "power_watts": 8.0,
        "cost_usd_hardware": 1200.0,
        "latency_ms_per_token": 3.6,
    },
    "neuromorphic": {
        "tokens_per_sec_base": 180.0,
        "power_watts": 1.2,        # Intel Loihi 2
        "cost_usd_hardware": 3500.0,
        "latency_ms_per_token": 5.5,
    },
    "photonic": {
        "tokens_per_sec_base": 2100.0,
        "power_watts": 12.0,
        "cost_usd_hardware": 25000.0,
        "latency_ms_per_token": 0.5,
    },
}

_SUPPORTED_TARGETS = list(_HARDWARE_PROFILES.keys())


@dataclass
class ComparisonConstraints:
    max_latency_ms: float | None = None
    max_power_w: float | None = None
    max_cost_usd: float | None = None
    min_accuracy: float | None = None
    carbon_region: str = "global_avg"
    inferences_per_day: int = 1000


@dataclass
class TargetResult:
    target: str
    tokens_per_sec: float
    latency_ms_per_token: float
    power_watts: float
    cost_usd_hardware: float
    cost_usd_per_inference: float
    carbon_gco2_per_inference: float
    accuracy_delta: float
    meets_constraints: bool
    sil_used: bool
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ComparisonReport:
    model_path: str
    constraints: dict[str, Any]
    results: list[TargetResult] = field(default_factory=list)
    recommended_target: str | None = None
    pareto_front: list[str] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_path": self.model_path,
            "constraints": self.constraints,
            "results": [r.to_dict() for r in self.results],
            "recommended_target": self.recommended_target,
            "pareto_front": self.pareto_front,
            "generated_at": self.generated_at,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def print_table(self) -> None:
        header = f"{'Target':<16} {'TPS':>8} {'Latency ms':>12} {'Power W':>10} {'Cost/inf':>12} {'Carbon gCO2':>13} {'Meets?':>7}"
        print(header)
        print("-" * len(header))
        for r in sorted(self.results, key=lambda x: -x.tokens_per_sec):
            mark = "✓" if r.meets_constraints else "✗"
            star = " ★" if r.target == self.recommended_target else ""
            print(
                f"{r.target:<16} {r.tokens_per_sec:>8.1f} {r.latency_ms_per_token:>12.2f} "
                f"{r.power_watts:>10.1f} {r.cost_usd_per_inference:>12.6f} "
                f"{r.carbon_gco2_per_inference:>13.6f} {mark:>7}{star}"
            )
        if self.recommended_target:
            print(f"\nRecommended: {self.recommended_target}")
        if self.pareto_front:
            print(f"Pareto front: {', '.join(self.pareto_front)}")


def _try_sil_run(tptir_path: Path, target: str, timeout: int = 120) -> dict[str, float] | None:
    """Attempt to run SiL via tpt-emulate and return metrics. Returns None on failure."""
    try:
        result = subprocess.run(
            ["tpt-emulate", str(tptir_path), "--hardware", target, "--benchmark", "--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                "tokens_per_sec": float(data.get("tokens_per_sec", 0)),
                "latency_ms_per_token": float(data.get("latency_ms_per_token", 0)),
                "power_watts": float(data.get("power_watts", 0)),
                "accuracy_delta": float(data.get("accuracy_delta", 0.0)),
            }
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, json.JSONDecodeError, KeyError, ValueError):
        pass
    return None


def _profile_based_result(
    target: str,
    constraints: ComparisonConstraints,
    node_count: int = 16,
) -> TargetResult:
    profile = _HARDWARE_PROFILES[target]
    tps = profile["tokens_per_sec_base"]

    # Alloy scales with node count
    if target == "alloy":
        tps = tps * (node_count / 16)

    latency = profile["latency_ms_per_token"]
    power = profile["power_watts"]
    hw_cost = profile["cost_usd_hardware"]

    # Cost per inference: amortize hardware over inferences_per_day × 365 × 3 years
    lifetime_inferences = constraints.inferences_per_day * 365 * 3
    cost_per_inf = hw_cost / max(lifetime_inferences, 1)

    # Carbon per inference
    inference_time_s = latency / 1000
    carbon = estimate_carbon(
        target=target,
        power_watts=power,
        inference_time_s=inference_time_s,
        region=constraints.carbon_region,
    )

    accuracy_delta = -0.02 if target == "element" else 0.0

    meets = True
    if constraints.max_latency_ms is not None and latency > constraints.max_latency_ms:
        meets = False
    if constraints.max_power_w is not None and power > constraints.max_power_w:
        meets = False
    if constraints.max_cost_usd is not None and hw_cost > constraints.max_cost_usd:
        meets = False
    if constraints.min_accuracy is not None and (1.0 + accuracy_delta) < constraints.min_accuracy:
        meets = False

    return TargetResult(
        target=target,
        tokens_per_sec=tps,
        latency_ms_per_token=latency,
        power_watts=power,
        cost_usd_hardware=hw_cost,
        cost_usd_per_inference=cost_per_inf,
        carbon_gco2_per_inference=carbon.carbon_gco2,
        accuracy_delta=accuracy_delta,
        meets_constraints=meets,
        sil_used=False,
        notes="Profile-based estimate (SiL not available)",
    )


def _compute_pareto_front(results: list[TargetResult]) -> list[str]:
    """Return targets on the Pareto front: not dominated on (tps, -latency, -power, -cost)."""
    front = []
    for candidate in results:
        dominated = False
        for other in results:
            if other.target == candidate.target:
                continue
            if (
                other.tokens_per_sec >= candidate.tokens_per_sec
                and other.latency_ms_per_token <= candidate.latency_ms_per_token
                and other.power_watts <= candidate.power_watts
                and other.cost_usd_hardware <= candidate.cost_usd_hardware
                and (
                    other.tokens_per_sec > candidate.tokens_per_sec
                    or other.latency_ms_per_token < candidate.latency_ms_per_token
                    or other.power_watts < candidate.power_watts
                    or other.cost_usd_hardware < candidate.cost_usd_hardware
                )
            ):
                dominated = True
                break
        if not dominated:
            front.append(candidate.target)
    return front


def _recommend(results: list[TargetResult], constraints: ComparisonConstraints) -> str | None:
    qualifying = [r for r in results if r.meets_constraints]
    if not qualifying:
        qualifying = results  # relax constraints if nothing qualifies

    # Score = normalized TPS (40%) - normalized latency (30%) - normalized power (20%) - normalized cost (10%)
    max_tps = max(r.tokens_per_sec for r in qualifying) or 1
    max_lat = max(r.latency_ms_per_token for r in qualifying) or 1
    max_pow = max(r.power_watts for r in qualifying) or 1
    max_cost = max(r.cost_usd_hardware for r in qualifying) or 1

    def score(r: TargetResult) -> float:
        return (
            0.40 * (r.tokens_per_sec / max_tps)
            - 0.30 * (r.latency_ms_per_token / max_lat)
            - 0.20 * (r.power_watts / max_pow)
            - 0.10 * (r.cost_usd_hardware / max_cost)
        )

    best = max(qualifying, key=score)
    return best.target


class ComparisonRunner:
    def __init__(
        self,
        targets: list[str] | None = None,
        use_sil: bool = True,
        sil_timeout: int = 120,
    ) -> None:
        self.targets = targets or _SUPPORTED_TARGETS
        self.use_sil = use_sil
        self.sil_timeout = sil_timeout

    def run(
        self,
        tptir_path: Path | str,
        constraints: ComparisonConstraints | None = None,
        node_count: int = 16,
    ) -> ComparisonReport:
        tptir_path = Path(tptir_path)
        constraints = constraints or ComparisonConstraints()

        report = ComparisonReport(
            model_path=str(tptir_path),
            constraints={
                "max_latency_ms": constraints.max_latency_ms,
                "max_power_w": constraints.max_power_w,
                "max_cost_usd": constraints.max_cost_usd,
                "min_accuracy": constraints.min_accuracy,
                "carbon_region": constraints.carbon_region,
                "inferences_per_day": constraints.inferences_per_day,
            },
            generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        for target in self.targets:
            if target not in _HARDWARE_PROFILES:
                continue

            sil_data = None
            if self.use_sil:
                sil_data = _try_sil_run(tptir_path, target, timeout=self.sil_timeout)

            if sil_data:
                inference_time_s = sil_data["latency_ms_per_token"] / 1000
                carbon = estimate_carbon(
                    target=target,
                    power_watts=sil_data["power_watts"],
                    inference_time_s=inference_time_s,
                    region=constraints.carbon_region,
                )
                profile = _HARDWARE_PROFILES[target]
                lifetime_inferences = constraints.inferences_per_day * 365 * 3
                cost_per_inf = profile["cost_usd_hardware"] / max(lifetime_inferences, 1)

                meets = True
                lat = sil_data["latency_ms_per_token"]
                pow_ = sil_data["power_watts"]
                if constraints.max_latency_ms is not None and lat > constraints.max_latency_ms:
                    meets = False
                if constraints.max_power_w is not None and pow_ > constraints.max_power_w:
                    meets = False
                if constraints.max_cost_usd is not None and profile["cost_usd_hardware"] > constraints.max_cost_usd:
                    meets = False
                accuracy = sil_data["accuracy_delta"]
                if constraints.min_accuracy is not None and (1.0 + accuracy) < constraints.min_accuracy:
                    meets = False

                result = TargetResult(
                    target=target,
                    tokens_per_sec=sil_data["tokens_per_sec"],
                    latency_ms_per_token=lat,
                    power_watts=pow_,
                    cost_usd_hardware=profile["cost_usd_hardware"],
                    cost_usd_per_inference=cost_per_inf,
                    carbon_gco2_per_inference=carbon.carbon_gco2,
                    accuracy_delta=accuracy,
                    meets_constraints=meets,
                    sil_used=True,
                )
            else:
                result = _profile_based_result(target, constraints, node_count=node_count)

            report.results.append(result)

        report.pareto_front = _compute_pareto_front(report.results)
        report.recommended_target = _recommend(report.results, constraints)
        return report
