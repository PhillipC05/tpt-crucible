package telemetry

import "time"

type HardwareType string

const (
	HardwareFPGA        HardwareType = "fpga"
	HardwareAnalog      HardwareType = "analog"
	HardwareSwarm       HardwareType = "swarm"
	HardwareCIM         HardwareType = "cim"
	HardwareNeuromorphic HardwareType = "neuromorphic"
	HardwarePhotonic    HardwareType = "photonic"
)

type TelemetryPoint struct {
	Timestamp   time.Time    `json:"timestamp"`
	HardwareType HardwareType `json:"hardware_type"`
	NodeID      string       `json:"node_id"`
	Metrics     []Metric     `json:"metrics"`
}

type Metric struct {
	Name  string      `json:"name"`
	Value interface{} `json:"value"`
	Unit  string      `json:"unit"`
}

type TokensPerSecond struct {
	Timestamp time.Time `json:"timestamp"`
	TPS       float64   `json:"tps"`
}

type MemoryBandwidth struct {
	Timestamp    time.Time `json:"timestamp"`
	UtilizationPct float64 `json:"utilization_pct"`
	BandwidthGBs float64   `json:"bandwidth_gbs"`
}

type ThermalDrift struct {
	Timestamp   time.Time `json:"timestamp"`
	NodeID      string    `json:"node_id"`
	TempCelsius float64   `json:"temp_celsius"`
	DriftPct    float64   `json:"drift_pct"`
}

type NodeLatency struct {
	Timestamp   time.Time `json:"timestamp"`
	NodeID      string    `json:"node_id"`
	LatencyMs   float64   `json:"latency_ms"`
	MessageSize int       `json:"message_size"`
}

type SpeculativeMetrics struct {
	Timestamp      time.Time `json:"timestamp"`
	TotalTokens    int       `json:"total_tokens"`
	AcceptedTokens int       `json:"accepted_tokens"`
	RejectedTokens int       `json:"rejected_tokens"`
	AcceptanceRate float64   `json:"acceptance_rate"`
	DraftTPS       float64   `json:"draft_tps"`
	EffectiveTPS   float64   `json:"effective_tps"`
}

type CarbonMetrics struct {
	Timestamp       time.Time `json:"timestamp"`
	Target          string    `json:"target"`
	CarbonGCO2      float64   `json:"carbon_gco2"`
	EnergyWh        float64   `json:"energy_wh"`
	Region          string    `json:"region"`
}

type SpikeRate struct {
	Timestamp time.Time `json:"timestamp"`
	NodeID    string    `json:"node_id"`
	RateHz    float64   `json:"rate_hz"`
}

type SparsityMetrics struct {
	Timestamp    time.Time `json:"timestamp"`
	LayerName    string    `json:"layer_name"`
	Density      float64   `json:"density"`
	NonZeroCount int       `json:"non_zero_count"`
	Mode         string    `json:"mode"`
}

// NodeHeartbeatStatus tracks per-node liveness derived from the Alloy heartbeat protocol.
// Status is "green" (online), "amber" (degraded — missed 1-2 beats), or "red" (dead).
type NodeHeartbeatStatus struct {
	Timestamp      time.Time `json:"timestamp"`
	NodeID         string    `json:"node_id"`
	Status         string    `json:"status"`         // "green" | "amber" | "red"
	LastSeen       time.Time `json:"last_seen"`
	MissedBeats    int       `json:"missed_beats"`
	AssignedLayers []int     `json:"assigned_layers"`
	LatencyMs      float64   `json:"latency_ms"`
}

// SwarmHeatmap is a snapshot of all node heartbeat statuses for the Observer UI heatmap.
type SwarmHeatmap struct {
	Timestamp time.Time             `json:"timestamp"`
	Nodes     []NodeHeartbeatStatus `json:"nodes"`
	Online    int                   `json:"online"`
	Degraded  int                   `json:"degraded"`
	Dead      int                   `json:"dead"`
}

type TelemetryMessage struct {
	Type    string      `json:"type"`
	Payload interface{} `json:"payload"`
}
