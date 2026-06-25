package broker

import (
	"time"
)

type JobStatus string

const (
	StatusQueued    JobStatus = "queued"
	StatusRunning   JobStatus = "running"
	StatusCompleted JobStatus = "completed"
	StatusFailed    JobStatus = "failed"
)

type Job struct {
	ID           string
	Target       string
	Driver       string
	Priority     int
	Status       JobStatus
	Stage        string
	ProgressPct  int
	Error        string
	ProviderID   string
	PackageData  []byte
	ResultData   []byte
	CreatedAt    time.Time
	StartedAt    *time.Time
	CompletedAt  *time.Time
	ElapsedSecs  float64
}

type Provider struct {
	ID              string
	URL             string
	Targets         []string
	YosysVersion    string
	NextpnrVersion  string
	MaxConcurrent   int
	CurrentLoad     int
	LastHealthCheck time.Time
	Healthy         bool
}

type Capabilities struct {
	ProviderID         string   `json:"provider_id"`
	Targets            []string `json:"targets"`
	YosysVersion       string   `json:"yosys_version"`
	NextpnrVersion     string   `json:"nextpnr_version"`
	MaxConcurrentJobs  int      `json:"max_concurrent_jobs"`
	CurrentLoad        int      `json:"current_load"`
}
