"use client";

interface PcbComponent {
  id: string;
  type: string;
  x: number;
  y: number;
  rotation: number;
}

const sampleComponents: PcbComponent[] = [
  { id: "R1", type: "resistor", x: 10, y: 20, rotation: 0 },
  { id: "R2", type: "resistor", x: 30, y: 20, rotation: 0 },
  { id: "C1", type: "capacitor", x: 50, y: 20, rotation: 90 },
  { id: "U1", type: "opamp", x: 25, y: 40, rotation: 0 },
  { id: "R3", type: "resistor", x: 10, y: 60, rotation: 0 },
  { id: "R4", type: "resistor", x: 30, y: 60, rotation: 0 },
];

const typeColors: Record<string, string> = {
  resistor: "fill-accent-cyan",
  capacitor: "fill-accent-amber",
  opamp: "fill-accent-green",
};

export function PcbVisualizer() {
  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">PCB LAYOUT</h3>
      <div className="relative bg-bg-tertiary rounded border border-border overflow-hidden" style={{ height: "200px" }}>
        <svg width="100%" height="100%" viewBox="0 0 80 80">
          <defs>
            <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
              <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#30363d" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="80" height="80" fill="url(#grid)" />
          {sampleComponents.map((comp) => (
            <g key={comp.id} transform={`translate(${comp.x}, ${comp.y}) rotate(${comp.rotation})`}>
              <rect
                x={-3}
                y={-2}
                width={6}
                height={4}
                className={typeColors[comp.type]}
                rx="0.5"
              />
              <text
                x={0}
                y={-3}
                textAnchor="middle"
                fontSize="2.5"
                fill="#c9d1d9"
              >
                {comp.id}
              </text>
            </g>
          ))}
        </svg>
      </div>
      <div className="flex justify-between mt-2 text-[10px] text-text-secondary">
        <span>{sampleComponents.length} components</span>
        <span>100x80mm</span>
      </div>
    </div>
  );
}
