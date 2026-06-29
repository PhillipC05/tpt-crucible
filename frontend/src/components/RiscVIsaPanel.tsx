"use client";

interface CustomOp {
  mnemonic: string;
  opcode: string;
  funct3: number;
  funct7: number;
  latency: number;
  speedup: number;
  description: string;
}

const sampleOps: CustomOp[] = [
  { mnemonic: "vmmul", opcode: "0x0B", funct3: 0, funct7: 1, latency: 4, speedup: 2.5, description: "Vector matrix multiply" },
  { mnemonic: "vmmulrelu", opcode: "0x0B", funct3: 1, funct7: 1, latency: 5, speedup: 3.0, description: "Fused matmul + ReLU" },
  { mnemonic: "vmmulgelu", opcode: "0x0B", funct3: 2, funct7: 1, latency: 6, speedup: 2.8, description: "Fused matmul + GELU" },
  { mnemonic: "vaddrelu", opcode: "0x0B", funct3: 3, funct7: 1, latency: 3, speedup: 2.0, description: "Fused add + ReLU" },
  { mnemonic: "vsoftmax", opcode: "0x0B", funct3: 4, funct7: 1, latency: 8, speedup: 1.5, description: "Vector softmax" },
  { mnemonic: "vlayernorm", opcode: "0x0B", funct3: 5, funct7: 1, latency: 6, speedup: 1.8, description: "Layer normalization" },
];

export function RiscVIsaPanel() {
  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">RISC-V CUSTOM ISA</h3>
      <div className="space-y-1">
        {sampleOps.map((op) => (
          <div key={op.mnemonic} className="flex items-center gap-2 text-xs p-1.5 rounded bg-bg-tertiary hover:bg-bg-primary">
            <span className="font-mono text-accent-cyan w-20">{op.mnemonic}</span>
            <span className="text-text-secondary w-12">{op.opcode}</span>
            <span className="text-text-secondary w-8">{op.latency}c</span>
            <span className="text-accent-green font-mono w-10">{op.speedup}x</span>
            <span className="text-text-secondary flex-1 truncate">{op.description}</span>
          </div>
        ))}
      </div>
      <div className="mt-3 text-[10px] text-text-secondary">
        Estimated speedup: {(sampleOps.reduce((sum, op) => sum + op.speedup, 0) / sampleOps.length).toFixed(1)}x average
      </div>
    </div>
  );
}
