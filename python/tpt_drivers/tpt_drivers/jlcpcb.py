"""JLCPCB BOM + CPL export for automated PCB assembly quotes."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import csv
import io


@dataclass
class JlcpcbBomItem:
    reference: str
    value: str
    footprint: str
    quantity: int
    supplier_part: str = ""
    comment: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "Reference": self.reference,
            "Value": self.value,
            "Footprint": self.footprint,
            "Qty": self.quantity,
            "Supplier Part": self.supplier_part,
            "Comment": self.comment,
        }


@dataclass
class JlcpcbCplItem:
    reference: str
    x: float
    y: float
    rotation: float
    side: str = "top"

    def to_dict(self) -> dict[str, Any]:
        return {
            "Designator": self.reference,
            "Val": "",
            "Package": "",
            "Mid X": f"{self.x:.4f}mm",
            "Mid Y": f"{self.y:.4f}mm",
            "Rotation": f"{self.rotation:.1f}",
            "Layer": self.side,
        }


class JlcpcbExporter:
    """Generate JLCPCB-compatible BOM and CPL files."""

    def __init__(self):
        self.bom_items: list[JlcpcbBomItem] = []
        self.cpl_items: list[JlcpcbCplItem] = []

    def add_component(
        self,
        reference: str,
        value: str,
        footprint: str,
        x: float,
        y: float,
        rotation: float = 0.0,
        side: str = "top",
        supplier_part: str = "",
    ) -> None:
        self.bom_items.append(JlcpcbBomItem(
            reference=reference,
            value=value,
            footprint=footprint,
            quantity=1,
            supplier_part=supplier_part,
        ))
        self.cpl_items.append(JlcpcbCplItem(
            reference=reference,
            x=x,
            y=y,
            rotation=rotation,
            side=side,
        ))

    def add_from_kicad(self, components: list[dict[str, Any]]) -> None:
        for comp in components:
            self.add_component(
                reference=comp.get("reference", ""),
                value=comp.get("value", ""),
                footprint=comp.get("footprint", ""),
                x=comp.get("x", 0),
                y=comp.get("y", 0),
                rotation=comp.get("rotation", 0),
                side=comp.get("side", "top"),
                supplier_part=comp.get("supplier_part", ""),
            )

    def generate_bom_csv(self) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Comment", "Designator", "Footprint", "Quantity", "Supplier Part"])
        for item in self.bom_items:
            writer.writerow([item.value, item.reference, item.footprint, item.quantity, item.supplier_part])
        return output.getvalue()

    def generate_cpl_csv(self) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Designator", "Val", "Package", "Mid X", "Mid Y", "Rotation", "Layer"])
        for item in self.cpl_items:
            writer.writerow([
                item.reference, "", "",
                f"{item.x:.4f}mm", f"{item.y:.4f}mm",
                f"{item.rotation:.1f}", item.side,
            ])
        return output.getvalue()

    def save_bom(self, path: Path) -> None:
        path.write_text(self.generate_bom_csv())

    def save_cpl(self, path: Path) -> None:
        path.write_text(self.generate_cpl_csv())

    def save_all(self, output_dir: Path) -> dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        bom_path = output_dir / "bom.csv"
        cpl_path = output_dir / "cpl.csv"
        self.save_bom(bom_path)
        self.save_cpl(cpl_path)
        return {"bom": bom_path, "cpl": cpl_path}
