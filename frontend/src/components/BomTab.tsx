"use client";

import { useState } from "react";

interface BomItem {
  part_number: string;
  description: string;
  quantity: number;
  unit_price: number;
  supplier: string;
  total_price: number;
}

const sampleBom: BomItem[] = [
  { part_number: "ESP32-WROOM-32", description: "ESP32 WiFi/BT Module", quantity: 16, unit_price: 3.50, supplier: "DigiKey", total_price: 56.00 },
  { part_number: "AS4C256M16D4A", description: "DDR4 SDRAM 4Gb", quantity: 4, unit_price: 12.50, supplier: "Mouser", total_price: 50.00 },
  { part_number: "R_0603_1K", description: "1K Resistor 0603", quantity: 128, unit_price: 0.01, supplier: "LCSC", total_price: 1.28 },
  { part_number: "C_0603_100nF", description: "100nF Capacitor 0603", quantity: 128, unit_price: 0.005, supplier: "LCSC", total_price: 0.64 },
  { part_number: "TPS54331", description: "3.3V DC-DC Converter", quantity: 16, unit_price: 1.25, supplier: "DigiKey", total_price: 20.00 },
];

export function BomTab() {
  const [bom] = useState<BomItem[]>(sampleBom);
  const [sortBy, setSortBy] = useState<"quantity" | "price">("price");
  const [filter, setFilter] = useState("");

  const filtered = bom
    .filter((item) => !filter || item.supplier.toLowerCase().includes(filter.toLowerCase()))
    .sort((a, b) => sortBy === "price" ? b.total_price - a.total_price : b.quantity - a.quantity);

  const totalCost = bom.reduce((sum, item) => sum + item.total_price, 0);
  const totalComponents = bom.reduce((sum, item) => sum + item.quantity, 0);

  const exportCsv = () => {
    const header = "Part Number,Description,Quantity,Unit Price,Supplier,Total Price\n";
    const rows = bom.map((item) =>
      `${item.part_number},${item.description},${item.quantity},${item.unit_price.toFixed(2)},${item.supplier},${item.total_price.toFixed(2)}`
    ).join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "bom.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-accent-cyan">BILL OF MATERIALS</h3>
        <button onClick={exportCsv} className="px-3 py-1.5 rounded bg-accent-cyan/20 text-accent-cyan text-xs border border-accent-cyan/50">
          Export CSV
        </button>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="stat-card text-center">
          <div className="stat-label">Total Cost</div>
          <div className="stat-value text-accent-amber">${totalCost.toFixed(2)}</div>
        </div>
        <div className="stat-card text-center">
          <div className="stat-label">Total Parts</div>
          <div className="stat-value text-accent-cyan">{totalComponents}</div>
        </div>
        <div className="stat-card text-center">
          <div className="stat-label">Unique Parts</div>
          <div className="stat-value">{bom.length}</div>
        </div>
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Filter by supplier..."
          className="flex-1 px-3 py-1.5 rounded bg-bg-tertiary border border-border text-xs text-text-primary placeholder-text-secondary"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <button
          onClick={() => setSortBy(sortBy === "price" ? "quantity" : "price")}
          className="px-3 py-1.5 rounded bg-bg-tertiary border border-border text-xs text-text-secondary hover:text-text-primary"
        >
          Sort by {sortBy === "price" ? "Qty" : "Price"}
        </button>
      </div>

      <div className="stat-card overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-text-secondary border-b border-border">
              <th className="text-left py-2 px-2">Part Number</th>
              <th className="text-left py-2 px-2">Description</th>
              <th className="text-right py-2 px-2">Qty</th>
              <th className="text-right py-2 px-2">Unit $</th>
              <th className="text-right py-2 px-2">Total $</th>
              <th className="text-left py-2 px-2">Supplier</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr key={item.part_number} className="border-b border-border/50 hover:bg-bg-tertiary">
                <td className="py-2 px-2 font-mono text-accent-cyan">{item.part_number}</td>
                <td className="py-2 px-2">{item.description}</td>
                <td className="py-2 px-2 text-right">{item.quantity}</td>
                <td className="py-2 px-2 text-right">${item.unit_price.toFixed(2)}</td>
                <td className="py-2 px-2 text-right text-accent-amber">${item.total_price.toFixed(2)}</td>
                <td className="py-2 px-2">
                  <span className="px-1.5 py-0.5 rounded bg-bg-tertiary text-[10px]">{item.supplier}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
