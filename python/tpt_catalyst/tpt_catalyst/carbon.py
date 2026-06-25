"""Carbon-aware compilation — estimate and minimize carbon footprint."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any


GRID_INTENSITY_GCO2_PER_KWH: dict[str, float] = {
    "us": 386.0,
    "us-ca": 210.0,
    "us-wa": 80.0,
    "eu": 230.0,
    "eu-fr": 55.0,
    "eu-de": 350.0,
    "eu-no": 10.0,
    "eu-se": 13.0,
    "uk": 220.0,
    "cn": 555.0,
    "in": 708.0,
    "jp": 460.0,
    "kr": 415.0,
    "au": 530.0,
    "br": 75.0,
    "global_avg": 475.0,
}


@dataclass
class CarbonEstimate:
    target: str
    power_watts: float
    inference_time_s: float
    energy_wh: float
    carbon_gco2: float
    region: str
    cost_usd: float

    @property
    def carbon_kg(self) -> float:
        return self.carbon_gco2 / 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "power_watts": round(self.power_watts, 2),
            "inference_time_s": round(self.inference_time_s, 3),
            "energy_wh": round(self.energy_wh, 6),
            "carbon_gco2": round(self.carbon_gco2, 4),
            "carbon_kg": round(self.carbon_kg, 6),
            "region": self.region,
            "cost_usd": round(self.cost_usd, 6),
        }


def estimate_carbon(
    target: str,
    power_watts: float,
    inference_time_s: float,
    region: str = "global_avg",
    electricity_rate_kwh: float = 0.12,
    embodied_carbon_gco2: float = 0.0,
) -> CarbonEstimate:
    energy_wh = (power_watts * inference_time_s) / 3600
    energy_kwh = energy_wh / 1000
    intensity = GRID_INTENSITY_GCO2_PER_KWH.get(region, GRID_INTENSITY_GCO2_PER_KWH["global_avg"])
    carbon_gco2 = energy_kwh * intensity + embodied_carbon_gco2
    cost_usd = energy_kwh * electricity_rate_kwh

    return CarbonEstimate(
        target=target,
        power_watts=power_watts,
        inference_time_s=inference_time_s,
        energy_wh=energy_wh,
        carbon_gco2=carbon_gco2,
        region=region,
        cost_usd=cost_usd,
    )


def select_lowest_carbon_target(estimates: list[CarbonEstimate]) -> CarbonEstimate | None:
    if not estimates:
        return None
    return min(estimates, key=lambda e: e.carbon_gco2)


def compare_targets(
    targets: list[dict[str, Any]],
    inference_time_s: float,
    region: str = "global_avg",
) -> list[CarbonEstimate]:
    estimates = []
    for t in targets:
        est = estimate_carbon(
            target=t["name"],
            power_watts=t["power_watts"],
            inference_time_s=inference_time_s,
            region=region,
        )
        estimates.append(est)
    return estimates
