"""Compilation Tournament — sweep optimization space and build a Pareto frontier of configs."""

from __future__ import annotations

import itertools
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .compare import ComparisonConstraints, _try_sil_run, _HARDWARE_PROFILES, _profile_based_result


@dataclass
class TournamentConstraints:
    max_latency_ms: float | None = None
    max_power_w: float | None = None
    max_cost_usd: float | None = None
    min_accuracy: float | None = None
    carbon_region: str = "global_avg"
    inferences_per_day: int = 1000


@dataclass
class TournamentConfig:
    targets: list[str] = field(default_factory=lambda: ["alloy", "fusion", "element"])
    quantization_schemes: list[str] = field(default_factory=lambda: ["int4", "int8", "float"])
    synthesis_modes: list[str] = field(default_factory=lambda: ["overlay", "full"])
    node_counts: list[int] = field(default_factory=lambda: [8, 16, 32])


@dataclass
class ParetoPoint:
    target: str
    quantization: str
    synthesis_mode: str
    node_count: int
    tokens_per_sec: float
    latency_ms_per_token: float
    power_watts: float
    cost_usd_hardware: float
    cost_usd_per_inference: float
    carbon_gco2_per_inference: float
    accuracy_delta: float
    meets_constraints: bool
    config_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def score(self) -> float:
        return self.tokens_per_sec / max(self.latency_ms_per_token, 0.001)


@dataclass
class TournamentReport:
    model_path: str
    constraints: dict[str, Any]
    points: list[ParetoPoint] = field(default_factory=list)
    pareto_front: list[str] = field(default_factory=list)
    recommended: ParetoPoint | None = None
    total_configs_evaluated: int = 0
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_path": self.model_path,
            "constraints": self.constraints,
            "points": [p.to_dict() for p in self.points],
            "pareto_front": self.pareto_front,
            "recommended": self.recommended.to_dict() if self.recommended else None,
            "total_configs_evaluated": self.total_configs_evaluated,
            "generated_at": self.generated_at,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def print_table(self) -> None:
        header = (
            f"{'Target':<12} {'Quant':<8} {'Mode':<10} {'Nodes':>6} "
            f"{'TPS':>8} {'Lat ms':>8} {'Power W':>8} {'Meets?':>7}"
        )
        print(header)
        print("-" * len(header))
        for p in sorted(self.points, key=lambda x: -x.score):
            mark = "✓" if p.meets_constraints else "✗"
            star = " ★" if self.recommended and p.config_id == self.recommended.config_id else ""
            print(
                f"{p.target:<12} {p.quantization:<8} {p.synthesis_mode:<10} {p.node_count:>6} "
                f"{p.tokens_per_sec:>8.1f} {p.latency_ms_per_token:>8.2f} "
                f"{p.power_watts:>8.1f} {mark:>7}{star}"
            )
        if self.recommended:
            print(f"\nRecommended config: {self.recommended.config_id}")
        print(f"Total configurations evaluated: {self.total_configs_evaluated}")


# Tuning multipliers: how quantization and synthesis mode affect performance
_QUANT_MULTIPLIERS: dict[str, dict[str, float]] = {
    "int4": {"tps": 1.25, "accuracy_delta": -0.02, "power": 0.85},
    "int8": {"tps": 1.10, "accuracy_delta": -0.008, "power": 0.92},
    "float": {"tps": 1.0, "accuracy_delta": 0.0, "power": 1.0},
}

_SYNTH_MULTIPLIERS: dict[str, dict[str, float]] = {
    "overlay": {"tps": 1.15, "latency": 0.90},
    "full": {"tps": 1.0, "latency": 1.0},
}


def _evaluate_config(
    tptir_path: Path,
    target: str,
    quant: str,
    synthesis_mode: str,
    node_count: int,
    constraints: TournamentConstraints,
    use_sil: bool = False,
) -> ParetoPoint:
    from .carbon import estimate_carbon

    profile = _HARDWARE_PROFILES.get(target, _HARDWARE_PROFILES["alloy"])
    qm = _QUANT_MULTIPLIERS.get(quant, _QUANT_MULTIPLIERS["float"])
    sm = _SYNTH_MULTIPLIERS.get(synthesis_mode, _SYNTH_MULTIPLIERS["full"])

    base_tps = profile["tokens_per_sec_base"]
    if target == "alloy":
        base_tps = base_tps * (node_count / 16)

    tps = base_tps * qm["tps"] * sm["tps"]
    latency = profile["latency_ms_per_token"] * sm["latency"]
    power = profile["power_watts"] * qm["power"]
    hw_cost = profile["cost_usd_hardware"]
    accuracy_delta = qm["accuracy_delta"]

    if use_sil:
        sil_data = _try_sil_run(tptir_path, target, timeout=60)
        if sil_data:
            tps = sil_data["tokens_per_sec"] * qm["tps"] * sm["tps"]
            latency = sil_data["latency_ms_per_token"] * sm["latency"]
            power = sil_data["power_watts"] * qm["power"]
            accuracy_delta = sil_data["accuracy_delta"] + qm["accuracy_delta"]

    lifetime_inferences = constraints.inferences_per_day * 365 * 3
    cost_per_inf = hw_cost / max(lifetime_inferences, 1)

    carbon = estimate_carbon(
        target=target,
        power_watts=power,
        inference_time_s=latency / 1000,
        region=constraints.carbon_region,
    )

    meets = True
    if constraints.max_latency_ms is not None and latency > constraints.max_latency_ms:
        meets = False
    if constraints.max_power_w is not None and power > constraints.max_power_w:
        meets = False
    if constraints.max_cost_usd is not None and hw_cost > constraints.max_cost_usd:
        meets = False
    if constraints.min_accuracy is not None and (1.0 + accuracy_delta) < constraints.min_accuracy:
        meets = False

    config_id = f"{target}-{quant}-{synthesis_mode}-n{node_count}"

    return ParetoPoint(
        target=target,
        quantization=quant,
        synthesis_mode=synthesis_mode,
        node_count=node_count,
        tokens_per_sec=round(tps, 2),
        latency_ms_per_token=round(latency, 3),
        power_watts=round(power, 2),
        cost_usd_hardware=hw_cost,
        cost_usd_per_inference=round(cost_per_inf, 8),
        carbon_gco2_per_inference=round(carbon.carbon_gco2, 8),
        accuracy_delta=round(accuracy_delta, 4),
        meets_constraints=meets,
        config_id=config_id,
    )


def _build_pareto(points: list[ParetoPoint]) -> list[str]:
    front = []
    for candidate in points:
        dominated = False
        for other in points:
            if other.config_id == candidate.config_id:
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
            front.append(candidate.config_id)
    return front


def _pick_recommended(points: list[ParetoPoint], constraints: TournamentConstraints) -> ParetoPoint | None:
    qualifying = [p for p in points if p.meets_constraints] or points
    if not qualifying:
        return None
    max_tps = max(p.tokens_per_sec for p in qualifying) or 1
    max_lat = max(p.latency_ms_per_token for p in qualifying) or 1
    max_pow = max(p.power_watts for p in qualifying) or 1
    max_cost = max(p.cost_usd_hardware for p in qualifying) or 1

    def score(p: ParetoPoint) -> float:
        return (
            0.40 * (p.tokens_per_sec / max_tps)
            - 0.30 * (p.latency_ms_per_token / max_lat)
            - 0.20 * (p.power_watts / max_pow)
            - 0.10 * (p.cost_usd_hardware / max_cost)
        )

    return max(qualifying, key=score)


class TournamentRunner:
    def __init__(
        self,
        config: TournamentConfig | None = None,
        use_sil: bool = False,
        verbose: bool = True,
    ) -> None:
        self.config = config or TournamentConfig()
        self.use_sil = use_sil
        self.verbose = verbose

    def run(
        self,
        tptir_path: Path | str,
        constraints: TournamentConstraints | None = None,
    ) -> TournamentReport:
        tptir_path = Path(tptir_path)
        constraints = constraints or TournamentConstraints()

        report = TournamentReport(
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

        configs = list(itertools.product(
            self.config.targets,
            self.config.quantization_schemes,
            self.config.synthesis_modes,
            self.config.node_counts,
        ))
        report.total_configs_evaluated = len(configs)

        for target, quant, synth_mode, nodes in configs:
            if target not in _HARDWARE_PROFILES:
                continue
            # Skip node_count variation for non-swarm targets
            if target != "alloy" and nodes != self.config.node_counts[0]:
                continue
            if self.verbose:
                print(f"  Evaluating {target}/{quant}/{synth_mode}/n{nodes}...", end="\r")

            point = _evaluate_config(
                tptir_path, target, quant, synth_mode, nodes, constraints, self.use_sil
            )
            report.points.append(point)

        if self.verbose:
            print(" " * 60, end="\r")

        report.pareto_front = _build_pareto(report.points)
        report.recommended = _pick_recommended(report.points, constraints)
        return report
