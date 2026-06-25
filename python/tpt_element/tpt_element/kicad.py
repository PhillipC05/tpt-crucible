"""KiCad PCB file export for analog circuit designs."""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .weight_map import PhysicalComponent, ComponentType


@dataclass
class KiCadComponent:
    reference: str
    value: str
    footprint: str
    x: float
    y: float
    rotation: float = 0.0


class KiCadExporter:
    """Generate KiCad PCB files from analog circuit designs."""

    def __init__(self, board_width_mm: float = 100.0, board_height_mm: float = 80.0):
        self.board_width = board_width_mm
        self.board_height = board_height_mm
        self.components: list[KiCadComponent] = []
        self._ref_counter = 1

    def add_components(self, components: list[PhysicalComponent]) -> None:
        for comp in components:
            ref = self._next_reference(comp.component_type)
            footprint = self._get_footprint(comp)
            value = self._get_value(comp)
            x, y = self._compute_position(comp)

            self.components.append(KiCadComponent(
                reference=ref,
                value=value,
                footprint=footprint,
                x=x,
                y=y,
            ))

    def _next_reference(self, comp_type: ComponentType) -> str:
        prefix = {"resistor": "R", "opamp_gain": "U", "memristor": "RM"}.get(comp_type.value, "X")
        ref = f"{prefix}{self._ref_counter}"
        self._ref_counter += 1
        return ref

    def _get_footprint(self, comp: PhysicalComponent) -> str:
        if comp.component_type == ComponentType.RESISTOR:
            return "Resistor_SMD:R_0603_1608Metric"
        elif comp.component_type == ComponentType.OPAMP_GAIN:
            return "Package_SO:TSSOP-8_4.4x3mm_P0.65mm"
        return "Resistor_SMD:R_0805_2012Metric"

    def _get_value(self, comp: PhysicalComponent) -> str:
        if comp.component_type == ComponentType.RESISTOR:
            if comp.value >= 1e6:
                return f"{comp.value/1e6:.1f}M"
            elif comp.value >= 1e3:
                return f"{comp.value/1e3:.1f}K"
            return f"{comp.value:.1f}"
        return f"{comp.value:.4f}"

    def _compute_position(self, comp: PhysicalComponent) -> tuple[float, float]:
        row, col = comp.position
        x_spacing = self.board_width / 10
        y_spacing = self.board_height / 10
        x = 15 + col * x_spacing
        y = 15 + row * y_spacing
        return (round(x, 2), round(y, 2))

    def generate_kicad_pcb(self) -> str:
        lines = [
            "(kicad_pcb (version 20240108) (generator tpt-element)",
            f'  (general (thickness 1.6))',
            f'  (paper "A4")',
            f'  (layers',
            f'    (0 "F.Cu" signal)',
            f'    (31 "B.Cu" signal)',
            f'    (32 "B.Adhes" user "B.Adhesive")',
            f'    (33 "F.Adhes" user "F.Adhesive")',
            f'    (34 "B.Paste" user)',
            f'    (35 "F.Paste" user)',
            f'    (36 "B.SilkS" user "B.Silkscreen")',
            f'    (37 "F.SilkS" user "F.Silkscreen")',
            f'    (38 "B.Mask" user "B.Mask")',
            f'    (39 "F.Mask" user "F.Mask")',
            f'  )',
            f'  (net 0 "")',
        ]

        for comp in self.components:
            lines.extend([
                f'  (footprint "{comp.footprint}"',
                f'    (layer "F.Cu")',
                f'    (at {comp.x} {comp.y} {comp.rotation})',
                f'    (property "Reference" "{comp.reference}" (at 0 -2.54 0) (layer "F.SilkS") (effects (font (size 1.27 1.27))))',
                f'    (property "Value" "{comp.value}" (at 0 2.54 0) (layer "F.Fab") (effects (font (size 1.27 1.27))))',
                f'  )',
            ])

        lines.append(")")
        return "\n".join(lines)

    def generate_schematic(self) -> str:
        lines = [
            "(kicad_sch (version 20231120) (generator tpt-element)",
            '  (uuid "00000000-0000-0000-0000-000000000001")',
            '  (paper "A4")',
        ]

        x_offset = 50
        for i, comp in enumerate(self.components):
            y_offset = 50 + i * 20
            lines.extend([
                f'  (symbol (lib_id "Device:{comp.footprint.split(":")[1] if ":" in comp.footprint else "R"})',
                f'    (at {x_offset} {y_offset} 0)',
                f'    (unit 1)',
                f'    (property "Reference" "{comp.reference}" (at {x_offset} {y_offset - 5} 0) (effects (font (size 1.27 1.27))))',
                f'    (property "Value" "{comp.value}" (at {x_offset} {y_offset + 5} 0) (effects (font (size 1.27 1.27))))',
                f'  )',
            ])

        lines.append(")")
        return "\n".join(lines)

    def save(self, output_dir: Path) -> dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)

        pcb_path = output_dir / "circuit.kicad_pcb"
        pcb_path.write_text(self.generate_kicad_pcb())

        sch_path = output_dir / "circuit.kicad_sch"
        sch_path.write_text(self.generate_schematic())

        return {"pcb": pcb_path, "schematic": sch_path}
