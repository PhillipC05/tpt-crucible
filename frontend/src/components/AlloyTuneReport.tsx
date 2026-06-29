"use client";

interface TuneResult {
  parameter: string;
  default_value: string;
  tuned_value: string;
  improvement: string;
}

const sampleResults: TuneResult[] = [
  { parameter: "wifi_message_size", default_value: "1024", tuned_value: "2048", improvement: "+15% throughput" },
  { parameter: "batch_size", default_value: "8", tuned_value: "16", improvement: "+22% throughput" },
  { parameter: "retry_count", default_value: "3", tuned_value: "1", improvement: "-0.5ms latency" },
  { parameter: "uart_baud_rate", default_value: "115200", tuned_value: "460800", improvement: "-1.2ms latency" },
];

export function AlloyTuneReport() {
  return (
    <div className="stat-card">
      <h3 className="text-sm font-bold text-accent-cyan mb-3">SIL TUNING RESULTS</h3>
      <div className="space-y-2">
        {sampleResults.map((r) => (
          <div key={r.parameter} className="flex items-center gap-3 text-xs p-2 rounded bg-bg-tertiary">
            <span className="font-mono text-text-primary w-32">{r.parameter}</span>
            <span className="text-text-secondary w-16">{r.default_value}</span>
            <span className="text-accent-cyan w-16">{r.tuned_value}</span>
            <span className="text-accent-green flex-1">{r.improvement}</span>
          </div>
        ))}
      </div>
      <div className="mt-3 text-[10px] text-text-secondary">
        Estimated overall improvement: 35% throughput, 40% latency reduction
      </div>
    </div>
  );
}
