"use client";

interface ZephyrProps {
  rtosVersion?: string;
  supportedBoards?: string[];
}

export function ZephyrTargetCard({ rtosVersion = "3.5", supportedBoards = ["ESP32", "RP2040"] }: ZephyrProps) {
  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">ZEPHYR RTOS</h3>
      <div className="space-y-2 text-xs">
        <div className="flex justify-between">
          <span className="text-text-secondary">RTos Version</span>
          <span>{rtosVersion}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-secondary">Supported Boards</span>
          <span>{supportedBoards.join(", ")}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-secondary">Build System</span>
          <span>CMake + West</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-secondary">Flash Protocol</span>
          <span>JTAG / SWD</span>
        </div>
      </div>
      <div className="mt-3 p-2 bg-bg-tertiary rounded text-[10px] text-text-secondary">
        Zephyr RTOS support enables custom RISC-V targets with deterministic real-time guarantees.
        Requires Zephyr SDK installed separately.
      </div>
    </div>
  );
}
