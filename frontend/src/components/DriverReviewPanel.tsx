"use client";

import { useState } from "react";

interface DriverField {
  key: string;
  value: string;
}

interface DriverReviewPanelProps {
  driverName?: string;
  fields?: DriverField[];
  onApprove?: (editedFields: DriverField[]) => void;
  onPublish?: () => void;
}

const defaultFields: DriverField[] = [
  { key: "name", value: "esp32-v2" },
  { key: "version", value: "1.0.0" },
  { key: "hardware_type", value: "mcu" },
  { key: "flash_protocol", value: "serial" },
  { key: "max_clock_mhz", value: "240" },
  { key: "max_luts", value: "0" },
];

export function DriverReviewPanel({
  driverName = "generated-driver",
  fields = defaultFields,
  onApprove,
  onPublish,
}: DriverReviewPanelProps) {
  const [editedFields, setEditedFields] = useState(fields);
  const [approved, setApproved] = useState(false);

  const updateField = (index: number, value: string) => {
    const next = [...editedFields];
    next[index] = { ...next[index], value };
    setEditedFields(next);
  };

  return (
    <div className="stat-card">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-bold text-accent-cyan">DRIVER REVIEW</h3>
        {approved && (
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-accent-green/20 text-accent-green">
            APPROVED
          </span>
        )}
      </div>
      <div className="text-[10px] text-text-secondary mb-2 font-mono">{driverName}</div>
      <div className="space-y-1.5 mb-3">
        {editedFields.map((field, i) => (
          <div key={field.key} className="flex items-center gap-2 text-[10px]">
            <span className="w-24 text-text-secondary font-mono">{field.key}</span>
            <input
              type="text"
              value={field.value}
              onChange={(e) => updateField(i, e.target.value)}
              className="flex-1 px-1.5 py-0.5 rounded bg-bg-tertiary border border-border text-text-primary font-mono"
            />
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => { setApproved(true); onApprove?.(editedFields); }}
          className="flex-1 px-3 py-1.5 rounded bg-accent-cyan text-bg-primary text-xs font-bold"
        >
          Approve
        </button>
        <button
          onClick={onPublish}
          disabled={!approved}
          className="flex-1 px-3 py-1.5 rounded bg-accent-green text-bg-primary text-xs font-bold disabled:opacity-30"
        >
          Publish to Registry
        </button>
      </div>
    </div>
  );
}
