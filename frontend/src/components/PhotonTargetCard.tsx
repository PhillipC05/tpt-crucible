"use client";

interface PhotonProps {
  meshSize?: number;
  wavelengthNm?: number;
  phaseAngles?: number[];
}

export function PhotonTargetCard({ meshSize = 8, wavelengthNm = 1550 }: PhotonProps) {
  return (
    <div className="stat-card relative">
      <div className="absolute top-2 right-2 px-2 py-0.5 rounded bg-accent-amber/20 text-accent-amber text-[10px] font-bold">
        EXPERIMENTAL
      </div>
      <h3 className="text-sm font-bold text-accent-cyan mb-3">PHOTONIC COMPUTE</h3>
      <div className="space-y-2 text-xs">
        <div className="flex justify-between">
          <span className="text-text-secondary">Mesh Size</span>
          <span>{meshSize}x{meshSize}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-secondary">Wavelength</span>
          <span>{wavelengthNm} nm</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-secondary">MZI Count</span>
          <span>{meshSize * meshSize}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-secondary">Modulation</span>
          <span>Thermal</span>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-8 gap-0.5">
        {Array.from({ length: meshSize * meshSize }).map((_, i) => {
          const angle = (i * 45) % 360;
          const hue = (angle / 360) * 120;
          return (
            <div
              key={i}
              className="aspect-square rounded-sm"
              style={{ backgroundColor: `hsl(${hue}, 70%, 50%)` }}
              title={`Phase: ${angle}\u00b0`}
            />
          );
        })}
      </div>
      <p className="text-[10px] text-text-secondary mt-2">Phase angle visualization (0-360\u00b0 mapped to hue)</p>
    </div>
  );
}
