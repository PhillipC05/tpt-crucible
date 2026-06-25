package job

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
	"time"
)

type Status string

const (
	StatusPending  Status = "pending"
	StatusRunning  Status = "running"
	StatusComplete Status = "complete"
	StatusFailed   Status = "failed"
)

type Job struct {
	ID        string    `json:"id"`
	ModelName string    `json:"model_name"`
	Target    string    `json:"target"`
	Status    Status    `json:"status"`
	CreatedAt time.Time `json:"created_at"`
	StartedAt *time.Time `json:"started_at,omitempty"`
	CompletedAt *time.Time `json:"completed_at,omitempty"`
	Error     string    `json:"error,omitempty"`
	Result    string    `json:"result,omitempty"`
}

type JobResult struct {
	JobID       string `json:"job_id"`
	ArtifactURL string `json:"artifact_url"`
	Duration    string `json:"duration"`
	ToolUsed    string `json:"tool_used"`
}

type Manager struct {
	jobs  map[string]*Job
	mu    sync.RWMutex
	queue chan string
}

func NewManager() *Manager {
	m := &Manager{
		jobs:  make(map[string]*Job),
		queue: make(chan string, 100),
	}
	go m.worker()
	return m
}

func (m *Manager) SubmitJob(modelName, target string) *Job {
	m.mu.Lock()
	defer m.mu.Unlock()

	id := fmt.Sprintf("job_%d", time.Now().UnixNano())
	job := &Job{
		ID:        id,
		ModelName: modelName,
		Target:    target,
		Status:    StatusPending,
		CreatedAt: time.Now(),
	}
	m.jobs[id] = job

	select {
	case m.queue <- id:
	default:
		job.Status = StatusFailed
		job.Error = "queue full"
	}

	return job
}

func (m *Manager) GetJob(id string) *Job {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.jobs[id]
}

func (m *Manager) ListJobs() []*Job {
	m.mu.RLock()
	defer m.mu.RUnlock()
	jobs := make([]*Job, 0, len(m.jobs))
	for _, j := range m.jobs {
		jobs = append(jobs, j)
	}
	return jobs
}

func (m *Manager) worker() {
	for id := range m.queue {
		m.processJob(id)
	}
}

func (m *Manager) processJob(id string) {
	m.mu.Lock()
	job := m.jobs[id]
	now := time.Now()
	job.Status = StatusRunning
	job.StartedAt = &now
	m.mu.Unlock()

	defer func() {
		m.mu.Lock()
		now := time.Now()
		job.CompletedAt = &now
		m.mu.Unlock()
	}()

	workDir := filepath.Join("work", id)
	os.MkdirAll(workDir, 0755)

	switch job.Target {
	case "fusion":
		m.runFusion(job, workDir)
	case "alloy":
		m.runAlloy(job, workDir)
	default:
		m.mu.Lock()
		job.Status = StatusFailed
		job.Error = fmt.Sprintf("unsupported target: %s", job.Target)
		m.mu.Unlock()
	}
}

func (m *Manager) runFusion(job *Job, workDir string) {
	cmd := exec.Command("yosys", "-p", "read_verilog input.v; synth_xilinx -blif output.blif")
	cmd.Dir = workDir
	output, err := cmd.CombinedOutput()

	m.mu.Lock()
	if err != nil {
		job.Status = StatusFailed
		job.Error = string(output)
	} else {
		job.Status = StatusComplete
		hash := sha256.Sum256(output)
		job.Result = hex.EncodeToString(hash[:])
	}
	m.mu.Unlock()
}

func (m *Manager) runAlloy(job *Job, workDir string) {
	cmd := exec.Command("echo", fmt.Sprintf("Firmware compiled for %s", job.ModelName))
	cmd.Dir = workDir
	output, _ := cmd.CombinedOutput()

	m.mu.Lock()
	job.Status = StatusComplete
	hash := sha256.Sum256(output)
	job.Result = hex.EncodeToString(hash[:])
	m.mu.Unlock()
}

func (m *Manager) ToJSON() []byte {
	data, _ := json.Marshal(m.ListJobs())
	return data
}
