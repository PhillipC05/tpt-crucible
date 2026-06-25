"""AI Driver Generator — extract driver specs from datasheets using LLM."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json
import re

from .driver import DriverManifest, SynthesisConstraints, PowerProfile, BomEntry, PinMapping


@dataclass
class DatasheetInfo:
    chip_name: str = ""
    manufacturer: str = ""
    package: str = ""
    pin_count: int = 0
    voltage_range: str = ""
    clock_speed_mhz: float = 0
    flash_size_kb: int = 0
    ram_size_kb: int = 0
    peripherals: list[str] = field(default_factory=list)
    pins: list[dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""


class AIDriverGenerator:
    """Generate driver manifests from datasheet text using LLM."""

    def __init__(self):
        self._extraction_patterns = {
            "voltage": r"(?:supply|operating)\s+(?:voltage|V)\s*[:=]?\s*([\d.]+)\s*(?:V|-[\d.]+\s*V)",
            "clock": r"(?:clock|frequency|speed)\s*[:=]?\s*(\d+)\s*(?:MHz|MHz)",
            "flash": r"(?:flash|storage)\s*[:=]?\s*(\d+)\s*(?:KB|MB)",
            "ram": r"(?:RAM|SRAM|memory)\s*[:=]?\s*(\d+)\s*(?:KB|MB)",
            "pins": r"(?:pin|pinout)\s*(?:count)?\s*[:=]?\s*(\d+)",
        }

    def extract_from_text(self, text: str) -> DatasheetInfo:
        info = DatasheetInfo(raw_text=text)

        voltage_match = re.search(self._extraction_patterns["voltage"], text, re.IGNORECASE)
        if voltage_match:
            info.voltage_range = voltage_match.group(1) + "V"

        clock_match = re.search(self._extraction_patterns["clock"], text, re.IGNORECASE)
        if clock_match:
            info.clock_speed_mhz = float(clock_match.group(1))

        flash_match = re.search(self._extraction_patterns["flash"], text, re.IGNORECASE)
        if flash_match:
            info.flash_size_kb = int(flash_match.group(1))

        ram_match = re.search(self._extraction_patterns["ram"], text, re.IGNORECASE)
        if ram_match:
            info.ram_size_kb = int(ram_match.group(1))

        pins_match = re.search(self._extraction_patterns["pins"], text, re.IGNORECASE)
        if pins_match:
            info.pin_count = int(pins_match.group(1))

        peripheral_keywords = ["UART", "SPI", "I2C", "GPIO", "ADC", "PWM", "USB", "WiFi", "Bluetooth", "CAN"]
        for kw in peripheral_keywords:
            if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
                info.peripherals.append(kw)

        return info

    def generate_manifest(self, info: DatasheetInfo, name: str) -> DriverManifest:
        if "WiFi" in info.peripherals:
            flash_protocol = "ota_wifi"
        elif info.flash_size_kb > 1024:
            flash_protocol = "jtag"
        else:
            flash_protocol = "serial"

        return DriverManifest(
            name=name,
            version="0.1.0",
            hardware_type="mcu",
            description=f"{info.chip_name or name} auto-generated driver",
            synthesis=SynthesisConstraints(
                max_clock_mhz=info.clock_speed_mhz or 240,
            ),
            power=PowerProfile(
                idle_mw=50.0,
                active_mw=200.0,
                peak_mw=500.0,
                voltage_v=float(info.voltage_range.replace("V", "")) if info.voltage_range else 3.3,
            ),
            flash_protocol=flash_protocol,
            telemetry_adapter="serial",
        )

    def generate_llm_prompt(self, text: str) -> str:
        return (
            "Extract hardware specifications from this datasheet text. "
            "Return JSON with fields: chip_name, manufacturer, package, pin_count, "
            "voltage_range, clock_speed_mhz, flash_size_kb, ram_size_kb, peripherals (list), "
            "pins (list of {name, number, function}).\n\n"
            f"Datasheet text:\n{text[:4000]}"
        )

    def parse_llm_response(self, response: str) -> DatasheetInfo:
        try:
            data = json.loads(response)
            return DatasheetInfo(
                chip_name=data.get("chip_name", ""),
                manufacturer=data.get("manufacturer", ""),
                package=data.get("package", ""),
                pin_count=data.get("pin_count", 0),
                voltage_range=data.get("voltage_range", ""),
                clock_speed_mhz=data.get("clock_speed_mhz", 0),
                flash_size_kb=data.get("flash_size_kb", 0),
                ram_size_kb=data.get("ram_size_kb", 0),
                peripherals=data.get("peripherals", []),
                pins=data.get("pins", []),
            )
        except (json.JSONDecodeError, KeyError):
            return DatasheetInfo()
