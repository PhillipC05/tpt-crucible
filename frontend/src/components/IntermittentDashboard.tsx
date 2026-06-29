"use client";

interface CheckpointData {
  layer_name: string;
  energy_mj: number;
  has_checkpoint: boolean;
  storage_offset: number;
}

const sampleCheckpoints: CheckpointData[] = [
  { layer_name: "layer_0_q_proj", energy_mj: 0.5, has_checkpoint: true, storage_offset: 0 },
  { layer_name: "layer_0_attn", energy_mj: 1.2, has_checkpoint: false, storage_offset: 4096 },
  { layer_name: "layer_0_ffn", energy_mj: 0.8, has_checkpoint: true, storage_offset: 8192 },
  { layer_name: "layer_1_q_proj", energy_mj: 0.5, has_checkpoint: false, storage_offset: 12288 },
  { layer_name: "layer_1_attn", energy_mj: 1.1, has_checkpoint: true, storage_offset: 16384 },
];

export function IntermittentDashboard() {
  const totalEnergy = sampleCheckpoints.reduce((sum, c) => sum + c.energy_mj, 0);
  const checkpointCount = sampleCheckpoints.filter((c) => c.has_checkpoint).length;
  const budget = 100.0;

  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-amber mb-3">INTERMITTENT COMPUTING</h3>
      <div className="grid grid-cols-3 gap-3 mb-3">
        <div className="text-center">
          <div className="text-lg font-bold text-accent-cyan">{totalEnergy.toFixed(1)}</div>
          <div className="text-[10px] text-text-secondary">Total mJ</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-accent-green">{budget}</div>
          <div className="text-[10px] text-text-secondary">Budget mJ</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-accent-amber">{checkpointCount}</div>
          <div className="text-[10px] text-text-secondary">Checkpoints</div>
        </div>
      </div>
      <div className="h-2 bg-bg-tertiary rounded-full overflow-hidden mb-3">
        <div
          className={`h-full rounded-full ${totalEnergy > budget ? "bg-accent-red" : "bg-accent-green"}`}
          style={{ width: `${Math.min((totalEnergy / budget) * 100, 100)}%` }}
        />
      </div>
      <div className="space-y-1">
        {sampleCheckpoints.map((cp) => (
          <div key={cp.layer_name} className="flex items-center gap-2 text-xs">
            <div className={`w-3 h-3 rounded ${cp.has_checkpoint ? "bg-accent-cyan" : "bg-bg-tertiary"}`} />
            <span className="flex-1 text-text-primary">{cp.layer_name}</span>
            <span className="text-text-secondary">{cp.energy_mj} mJ</span>
          </div>
        ))}
      </div>
    </div>
  );
}
