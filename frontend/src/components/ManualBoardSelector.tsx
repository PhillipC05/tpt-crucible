"use client";

import { useState } from "react";

interface BoardOption {
  name: string;
  type: string;
  description: string;
  cost: string;
}

const boards: BoardOption[] = [
  { name: "Xilinx Alveo U250", type: "fpga", description: "High-performance FPGA with HBM", cost: "$8,500" },
  { name: "Xilinx Alveo U280", type: "fpga", description: "Mid-range FPGA with HBM", cost: "$5,200" },
  { name: "ESP32", type: "mcu", description: "WiFi/BT microcontroller, 520KB SRAM", cost: "$3" },
  { name: "ESP32-S3", type: "mcu", description: "Enhanced ESP32 with AI acceleration", cost: "$4" },
  { name: "RP2040", type: "mcu", description: "Dual-core ARM Cortex-M0+", cost: "$1" },
  { name: "Custom Analog", type: "analog", description: "Custom analog compute PCB", cost: "$150" },
];

interface ManualBoardSelectorProps {
  onSelect?: (board: BoardOption) => void;
}

export function ManualBoardSelector({ onSelect }: ManualBoardSelectorProps) {
  const [selected, setSelected] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const filtered = boards.filter(
    (b) =>
      b.name.toLowerCase().includes(filter.toLowerCase()) ||
      b.type.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-2">SELECT BOARD</h3>
      <input
        type="text"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        placeholder="Search boards..."
        className="w-full px-2 py-1 rounded bg-bg-tertiary border border-border text-xs text-text-primary placeholder-text-secondary mb-2"
      />
      <div className="space-y-1 max-h-[200px] overflow-y-auto">
        {filtered.map((board) => (
          <button
            key={board.name}
            onClick={() => { setSelected(board.name); onSelect?.(board); }}
            className={`w-full p-2 rounded border text-left transition-colors ${
              selected === board.name
                ? "border-accent-cyan bg-accent-cyan/10"
                : "border-border bg-bg-tertiary hover:border-accent-cyan/50"
            }`}
          >
            <div className="flex justify-between items-center">
              <span className="text-xs font-bold text-text-primary">{board.name}</span>
              <span className="text-[10px] text-accent-amber">{board.cost}</span>
            </div>
            <div className="text-[10px] text-text-secondary">{board.description}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
