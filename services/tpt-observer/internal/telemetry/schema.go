package telemetry

import "time"

type HardwareType string

const (
	HardwareFPGA   HardwareType = "fpga"
	HardwareAnalog HardwareType = "analog"
	HardwareSwarm  HardwareType = "swarm"
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

type TelemetryMessage struct {
	Type    string      `json:"type"`
	Payload interface{} `json:"payload"`
}
