"""Bill of Materials (BOM) generator — extract and aggregate parts lists."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from .driver import DriverManifest, BomEntry


@dataclass
class BomItem:
    part_number: str
    description: str
    quantity: int
    unit_price: float
    total_price: float
    suppliers: list[str]


class BomGenerator:
    """Generate and aggregate BOMs from driver manifests."""

    def __init__(self):
        self.items: dict[str, BomItem] = {}

    def add_driver(self, manifest: DriverManifest, node_count: int = 1) -> None:
        for entry in manifest.bom:
            key = entry.part_number
            if key in self.items:
                self.items[key].quantity += entry.quantity * node_count
                self.items[key].total_price = self.items[key].quantity * self.items[key].unit_price
                if entry.supplier and entry.supplier not in self.items[key].suppliers:
                    self.items[key].suppliers.append(entry.supplier)
            else:
                qty = entry.quantity * node_count
                self.items[key] = BomItem(
                    part_number=entry.part_number,
                    description=entry.description,
                    quantity=qty,
                    unit_price=entry.unit_price_usd,
                    total_price=qty * entry.unit_price_usd,
                    suppliers=[entry.supplier] if entry.supplier else [],
                )

    def get_total_cost(self) -> float:
        return sum(item.total_price for item in self.items.values())

    def get_total_components(self) -> int:
        return sum(item.quantity for item in self.items.values())

    def to_csv(self) -> str:
        lines = ["Part Number,Description,Quantity,Unit Price,Total Price,Suppliers"]
        for item in sorted(self.items.values(), key=lambda x: x.part_number):
            suppliers = "; ".join(item.suppliers)
            lines.append(
                f"{item.part_number},{item.description},{item.quantity},"
                f"{item.unit_price:.2f},{item.total_price:.2f},{suppliers}"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_cost_usd": round(self.get_total_cost(), 2),
            "total_components": self.get_total_components(),
            "items": [
                {
                    "part_number": item.part_number,
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price,
                    "suppliers": item.suppliers,
                }
                for item in sorted(self.items.values(), key=lambda x: x.part_number)
            ],
        }
