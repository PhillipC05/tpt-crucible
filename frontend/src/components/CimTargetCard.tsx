"use client";

interface CimTargetCardProps {
  arrayRows?: number;
  arrayCols?: number;
  bitPrecision?: number;
  utilization?: number;
}

export function CimTargetCard({
  arrayRows = 1024,
  arrayCols = 1024,
  bitPrecision = 8,
  utilization = 0.65,
}: CimTargetCardProps) {
  const macUnits = arrayRows * arrayCols;
  const memoryKB = (macUnits * bitPrecision) / 8 / 1024;

  return (
    <div className="stat-card">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-bold text-accent-cyan">CIM ARRAY</h3>
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-accent-amber/20 text-accent-amber">
          COMPUTE-IN-MEMORY
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-[11px] mb-3">
        <div>
          <span className="text-text-secondary">Dimensions</span>
          <div className="font-mono text-text-primary">
            {arrayRows}x{arrayCols}
          </div>
        </div>
        <div>
          <span className="text-text-secondary">Precision</span>
          <div className="font-mono text-text-primary">{bitPrecision}-bit</div>
        </div>
        <div>
          <span className="text-text-secondary">MAC Units</span>
          <div className="font-mono text-text-primary">{macUnits.toLocaleString()}</div>
        </div>
        <div>
          <span className="text-text-secondary">Memory</span>
          <div className="font-mono text-text-primary">{memoryKB.toLocaleString()} KB</div>
        </div>
      </div>
      <div className="w-full h-2 bg-bg-tertiary rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            utilization >= 0.8 ? "bg-accent-green" : utilization >= 0.5 ? "bg-accent-amber" : "bg-accent-red"
          }`}
          style={{ width: `${utilization * 100}%` }}
        />
      </div>
      <div className="text-[10px] text-text-secondary mt-1 font-mono">
        Array utilization: {(utilization * 100).toFixed(0)}%
      </div>
    </div>
  );
}
