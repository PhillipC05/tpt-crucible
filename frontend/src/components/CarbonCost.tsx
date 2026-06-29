"use client";

interface CarbonEstimate {
  target: string;
  carbonGco2: number;
  energyWh: number;
  region: string;
}

interface CarbonCostProps {
  estimates?: CarbonEstimate[];
  selectedTarget?: string;
}

const defaultEstimates: CarbonEstimate[] = [
  { target: "alloy", carbonGco2: 0.038, energyWh: 0.055, region: "eu" },
  { target: "fusion", carbonGco2: 0.012, energyWh: 0.018, region: "eu" },
  { target: "element", carbonGco2: 0.005, energyWh: 0.008, region: "eu" },
];

export function CarbonCostPanel({
  estimates = defaultEstimates,
  selectedTarget,
}: CarbonCostProps) {
  const sorted = [...estimates].sort((a, b) => a.carbonGco2 - b.carbonGco2);
  const lowest = sorted[0];

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">
        CARBON FOOTPRINT
      </h3>
      <div className="space-y-2">
        {sorted.map((est) => {
          const isLowest = est.target === lowest.target;
          const isSelected = est.target === selectedTarget;
          return (
            <div
              key={est.target}
              className={`flex items-center justify-between text-[11px] px-2 py-1.5 rounded ${
                isSelected ? "bg-accent-cyan/10 border border-accent-cyan/30" : ""
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="font-mono text-text-primary">{est.target}</span>
                {isLowest && (
                  <span className="text-[9px] px-1 py-0.5 bg-accent-green/20 text-accent-green rounded">
                    LOWEST
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 font-mono text-text-secondary">
                <span>{est.carbonGco2.toFixed(3)} gCO₂</span>
                <span>{est.energyWh.toFixed(4)} Wh</span>
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-2 text-[9px] text-text-secondary font-mono">
        Region: {estimates[0]?.region || "eu"} | Est. per 1k inference runs
      </div>
    </div>
  );
}
