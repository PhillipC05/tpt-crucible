"use client";

interface PackageLockBadgeProps {
  locked?: boolean;
  hardwareIds?: string[];
  lockType?: string;
}

export function PackageLockBadge({
  locked = false,
  hardwareIds = [],
  lockType = "hardware_bound",
}: PackageLockBadgeProps) {
  if (!locked) return null;

  return (
    <div className="stat-card">
      <div className="flex items-center gap-2 mb-2">
        <svg className="w-4 h-4 text-accent-amber" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
        </svg>
        <h3 className="text-sm font-bold text-accent-amber">LOCKED PACKAGE</h3>
      </div>
      <div className="text-[10px] text-text-secondary mb-2">
        Type: {lockType}
      </div>
      <div className="space-y-1">
        {hardwareIds.map((id) => (
          <div key={id} className="flex items-center gap-2 text-[10px]">
            <div className="w-1.5 h-1.5 rounded-full bg-accent-amber" />
            <span className="font-mono text-text-primary">{id}</span>
          </div>
        ))}
      </div>
      <div className="mt-2 text-[9px] text-text-secondary">
        Package will refuse to load on non-matching hardware.
      </div>
    </div>
  );
}
