"""Hardware driver specification — board identity, pin map, constraints, telemetry."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PinMapping:
    name: str
    pin_number: int
    function: str
    direction: str = "bidirectional"
    voltage: float = 3.3


@dataclass
class SynthesisConstraints:
    max_clock_mhz: float = 200.0
    max_luts: int = 0
    max_dsp_slices: int = 0
    max_bram_kbits: int = 0
    timing_margin_ns: float = 1.0


@dataclass
class BomEntry:
    part_number: str
    description: str
    quantity: int = 1
    supplier: str = ""
    supplier_sku: str = ""
    unit_price_usd: float = 0.0


@dataclass
class PowerProfile:
    idle_mw: float = 0.0
    active_mw: float = 0.0
    peak_mw: float = 0.0
    voltage_v: float = 3.3


@dataclass
class DriverManifest:
    name: str
    version: str
    hardware_type: str
    description: str = ""
    pins: list[PinMapping] = field(default_factory=list)
    synthesis: SynthesisConstraints = field(default_factory=SynthesisConstraints)
    bom: list[BomEntry] = field(default_factory=list)
    power: PowerProfile = field(default_factory=PowerProfile)
    flash_protocol: str = "serial"
    telemetry_adapter: str = "default"
    metadata: dict[str, Any] = field(default_factory=dict)
    # Certification fields — set by the automated certification pipeline, not by contributors
    verified: bool = False
    signature: str = ""       # Ed25519 signature (hex) over canonical JSON of to_dict()
    certified_at: str = ""    # ISO 8601 timestamp of when certification ran
    certification_pipeline: str = ""  # git SHA of certify.py that signed this

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "hardware_type": self.hardware_type,
            "description": self.description,
            "pins": [{"name": p.name, "pin": p.pin_number, "function": p.function,
                       "direction": p.direction, "voltage": p.voltage} for p in self.pins],
            "synthesis": {
                "max_clock_mhz": self.synthesis.max_clock_mhz,
                "max_luts": self.synthesis.max_luts,
                "max_dsp_slices": self.synthesis.max_dsp_slices,
                "max_bram_kbits": self.synthesis.max_bram_kbits,
            },
            "bom": [{"part_number": b.part_number, "description": b.description,
                      "quantity": b.quantity, "supplier": b.supplier,
                      "sku": b.supplier_sku, "price": b.unit_price_usd} for b in self.bom],
            "power": {
                "idle_mw": self.power.idle_mw,
                "active_mw": self.power.active_mw,
                "peak_mw": self.power.peak_mw,
                "voltage": self.power.voltage_v,
            },
            "flash_protocol": self.flash_protocol,
            "telemetry_adapter": self.telemetry_adapter,
            "verified": self.verified,
            "signature": self.signature,
            "certified_at": self.certified_at,
            "certification_pipeline": self.certification_pipeline,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DriverManifest:
        pins = [PinMapping(
            name=p["name"], pin_number=p["pin"], function=p["function"],
            direction=p.get("direction", "bidirectional"), voltage=p.get("voltage", 3.3),
        ) for p in data.get("pins", [])]

        syn = data.get("synthesis", {})
        synthesis = SynthesisConstraints(
            max_clock_mhz=syn.get("max_clock_mhz", 200.0),
            max_luts=syn.get("max_luts", 0),
            max_dsp_slices=syn.get("max_dsp_slices", 0),
            max_bram_kbits=syn.get("max_bram_kbits", 0),
        )

        bom = [BomEntry(
            part_number=b["part_number"], description=b["description"],
            quantity=b.get("quantity", 1), supplier=b.get("supplier", ""),
            supplier_sku=b.get("sku", ""), unit_price_usd=b.get("price", 0.0),
        ) for b in data.get("bom", [])]

        pw = data.get("power", {})
        power = PowerProfile(
            idle_mw=pw.get("idle_mw", 0.0),
            active_mw=pw.get("active_mw", 0.0),
            peak_mw=pw.get("peak_mw", 0.0),
            voltage_v=pw.get("voltage", 3.3),
        )

        return cls(
            name=data["name"], version=data["version"],
            hardware_type=data["hardware_type"],
            description=data.get("description", ""),
            pins=pins, synthesis=synthesis, bom=bom, power=power,
            flash_protocol=data.get("flash_protocol", "serial"),
            telemetry_adapter=data.get("telemetry_adapter", "default"),
            verified=data.get("verified", False),
            signature=data.get("signature", ""),
            certified_at=data.get("certified_at", ""),
            certification_pipeline=data.get("certification_pipeline", ""),
        )

    def to_toml(self) -> str:
        lines = [
            f'[driver]',
            f'name = "{self.name}"',
            f'version = "{self.version}"',
            f'hardware_type = "{self.hardware_type}"',
            f'description = "{self.description}"',
            f'flash_protocol = "{self.flash_protocol}"',
            f'telemetry_adapter = "{self.telemetry_adapter}"',
            '',
            '[synthesis]',
            f'max_clock_mhz = {self.synthesis.max_clock_mhz}',
            f'max_luts = {self.synthesis.max_luts}',
            f'max_dsp_slices = {self.synthesis.max_dsp_slices}',
            f'max_bram_kbits = {self.synthesis.max_bram_kbits}',
            '',
            '[power]',
            f'idle_mw = {self.power.idle_mw}',
            f'active_mw = {self.power.active_mw}',
            f'peak_mw = {self.power.peak_mw}',
            f'voltage_v = {self.power.voltage_v}',
        ]

        if self.bom:
            lines.append('')
            lines.append('[[bom]]')
            for b in self.bom:
                lines.append(f'part_number = "{b.part_number}"')
                lines.append(f'description = "{b.description}"')
                lines.append(f'quantity = {b.quantity}')
                lines.append(f'supplier = "{b.supplier}"')
                lines.append(f'supplier_sku = "{b.supplier_sku}"')
                lines.append(f'unit_price_usd = {b.unit_price_usd}')
                lines.append('')

        return "\n".join(lines)
