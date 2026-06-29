"use client";

interface RegressionProps {
  baseline: number;
  current: number;
  threshold?: number;
}

export function RegressionBadge({ baseline, current, threshold = 0.02 }: RegressionProps) {
  const delta = current - baseline;
  const improved = delta > 0.01;
  const regressed = delta < -threshold;

  const color = improved ? "text-accent-green" : regressed ? "text-accent-red" : "text-text-secondary";
  const bg = improved ? "bg-accent-green/20" : regressed ? "bg-accent-red/20" : "bg-bg-tertiary";
  const icon = improved ? "\u25B2" : regressed ? "\u25BC" : "=";

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${bg} ${color}`}>
      <span>{icon}</span>
      <span>{(delta * 100).toFixed(1)}%</span>
    </span>
  );
}
