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
    carbon_overhead_gco2: float = 0.0


@dataclass
class CimArraySpec:
    array_rows: int = 1024
    array_cols: int = 1024
    bit_precision: int = 8
    num_arrays: int = 1
    wavelength_nm: int = 0


@dataclass
class NeuromorphicSpec:
    chip_type: str = "loihi"
    num_cores: int = 128
    synapses_per_core: int = 1024
    learning_rules: list[str] = field(default_factory=lambda: ["stdp"])


@dataclass
class PhotonicSpec:
    mesh_size: int = 8
    wavelength_nm: int = 1550
    modulation: str = "thermal"
    phase_bits: int = 8


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
    cim_array: CimArraySpec | None = None
    neuromorphic: NeuromorphicSpec | None = None
    photonic: PhotonicSpec | None = None
    checkpoint_storage: str | None = None
    power_monitor_pin: str | None = None

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
                "carbon_overhead_gco2": self.power.carbon_overhead_gco2,
            },
            "flash_protocol": self.flash_protocol,
            "telemetry_adapter": self.telemetry_adapter,
            "cim_array": {"array_rows": self.cim_array.array_rows, "array_cols": self.cim_array.array_cols,
                         "bit_precision": self.cim_array.bit_precision} if self.cim_array else None,
            "neuromorphic": {"chip_type": self.neuromorphic.chip_type, "num_cores": self.neuromorphic.num_cores} if self.neuromorphic else None,
            "photonic": {"mesh_size": self.photonic.mesh_size, "wavelength_nm": self.photonic.wavelength_nm} if self.photonic else None,
            "checkpoint_storage": self.checkpoint_storage,
            "power_monitor_pin": self.power_monitor_pin,
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
            carbon_overhead_gco2=pw.get("carbon_overhead_gco2", 0.0),
        )

        cim = data.get("cim_array")
        cim_array = CimArraySpec(**cim) if cim else None

        neu = data.get("neuromorphic")
        neuromorphic = NeuromorphicSpec(**neu) if neu else None

        phot = data.get("photonic")
        photonic = PhotonicSpec(**phot) if phot else None

        return cls(
            name=data["name"], version=data["version"],
            hardware_type=data["hardware_type"],
            description=data.get("description", ""),
            pins=pins, synthesis=synthesis, bom=bom, power=power,
            flash_protocol=data.get("flash_protocol", "serial"),
            telemetry_adapter=data.get("telemetry_adapter", "default"),
            cim_array=cim_array, neuromorphic=neuromorphic, photonic=photonic,
            checkpoint_storage=data.get("checkpoint_storage"),
            power_monitor_pin=data.get("power_monitor_pin"),
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
