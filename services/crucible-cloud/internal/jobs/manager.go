package jobs

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
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
	ID          string    `json:"id"`
	ModelName   string    `json:"model_name"`
	Target      string    `json:"target"`
	Status      Status    `json:"status"`
	CreatedAt   time.Time `json:"created_at"`
	StartedAt   *time.Time `json:"started_at,omitempty"`
	CompletedAt *time.Time `json:"completed_at,omitempty"`
	Error       string    `json:"error,omitempty"`
	Result      string    `json:"result,omitempty"`
}

type Manager struct {
	jobs map[string]*Job
	mu   sync.RWMutex
}

func NewManager() *Manager {
	return &Manager{
		jobs: make(map[string]*Job),
	}
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

func (m *Manager) UpdateJob(id string, status Status, result string, errMsg string) bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	job, ok := m.jobs[id]
	if !ok {
		return false
	}
	job.Status = status
	job.Result = result
	job.Error = errMsg
	now := time.Now()
	if status == StatusRunning {
		job.StartedAt = &now
	}
	if status == StatusComplete || status == StatusFailed {
		job.CompletedAt = &now
	}
	return true
}

func (m *Manager) SaveManifest(pkgDir string) error {
	manifest := map[string]interface{}{
		"format_version": "1.0.0",
		"model_name":     "",
		"targets":        []string{},
	}
	data, _ := json.MarshalIndent(manifest, "", "  ")
	return os.WriteFile(filepath.Join(pkgDir, "manifest.json"), data, 0644)
}

func ComputeSHA256(data []byte) string {
	hash := sha256.Sum256(data)
	return hex.EncodeToString(hash[:])
}
