package broker

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"mime/multipart"
	"net/http"
	"slices"
	"sync"
	"time"

	"github.com/tpt-crucible/synthesis-broker/internal/id"
)

type Broker struct {
	mu        sync.RWMutex
	providers map[string]*Provider
	jobs      map[string]*Job
	queue     chan *Job
}

func New() *Broker {
	b := &Broker{
		providers: make(map[string]*Provider),
		jobs:      make(map[string]*Job),
		queue:     make(chan *Job, 256),
	}
	go b.dispatch()
	go b.healthLoop()
	return b
}

func (b *Broker) RegisterProvider(caps Capabilities, rawURL string) {
	b.mu.Lock()
	defer b.mu.Unlock()
	now := time.Now()
	b.providers[caps.ProviderID] = &Provider{
		ID:              caps.ProviderID,
		URL:             rawURL,
		Targets:         caps.Targets,
		YosysVersion:    caps.YosysVersion,
		NextpnrVersion:  caps.NextpnrVersion,
		MaxConcurrent:   caps.MaxConcurrentJobs,
		CurrentLoad:     caps.CurrentLoad,
		LastHealthCheck: now,
		Healthy:         true,
	}
	log.Printf("registered provider %s at %s (targets: %v)", caps.ProviderID, rawURL, caps.Targets)
}

func (b *Broker) SubmitJob(packageData []byte, target, driver string, priority int) (*Job, error) {
	job := &Job{
		ID:          id.New(),
		Target:      target,
		Driver:      driver,
		Priority:    priority,
		Status:      StatusQueued,
		PackageData: packageData,
		CreatedAt:   time.Now(),
	}

	b.mu.Lock()
	b.jobs[job.ID] = job
	b.mu.Unlock()

	select {
	case b.queue <- job:
	default:
		return nil, fmt.Errorf("broker queue full")
	}
	return job, nil
}

func (b *Broker) GetJob(jobID string) (*Job, bool) {
	b.mu.RLock()
	defer b.mu.RUnlock()
	j, ok := b.jobs[jobID]
	return j, ok
}

func (b *Broker) dispatch() {
	for job := range b.queue {
		provider := b.pickProvider(job.Target)
		if provider == nil {
			b.mu.Lock()
			job.Status = StatusFailed
			job.Error = "no healthy provider available for target: " + job.Target
			b.mu.Unlock()
			log.Printf("job %s failed: no provider for %s", job.ID, job.Target)
			continue
		}
		go b.forward(job, provider)
	}
}

func (b *Broker) pickProvider(target string) *Provider {
	b.mu.RLock()
	defer b.mu.RUnlock()
	var best *Provider
	for _, p := range b.providers {
		if !p.Healthy {
			continue
		}
		if !slices.Contains(p.Targets, target) {
			continue
		}
		if p.MaxConcurrent > 0 && p.CurrentLoad >= p.MaxConcurrent {
			continue
		}
		if best == nil || p.CurrentLoad < best.CurrentLoad {
			best = p
		}
	}
	return best
}

func (b *Broker) forward(job *Job, provider *Provider) {
	now := time.Now()
	b.mu.Lock()
	job.Status = StatusRunning
	job.ProviderID = provider.ID
	job.StartedAt = &now
	provider.CurrentLoad++
	b.mu.Unlock()

	log.Printf("forwarding job %s to provider %s", job.ID, provider.ID)

	result, err := b.sendToProvider(provider.URL, job)

	b.mu.Lock()
	done := time.Now()
	job.CompletedAt = &done
	job.ElapsedSecs = done.Sub(now).Seconds()
	provider.CurrentLoad--
	if err != nil {
		job.Status = StatusFailed
		job.Error = err.Error()
		log.Printf("job %s failed on provider %s: %v", job.ID, provider.ID, err)
	} else {
		job.Status = StatusCompleted
		job.ResultData = result
		log.Printf("job %s completed in %.1fs", job.ID, job.ElapsedSecs)
	}
	b.mu.Unlock()
}

func (b *Broker) sendToProvider(baseURL string, job *Job) ([]byte, error) {
	var body bytes.Buffer
	w := multipart.NewWriter(&body)

	part, err := w.CreateFormFile("package", job.ID+".tptpkg")
	if err != nil {
		return nil, err
	}
	if _, err := part.Write(job.PackageData); err != nil {
		return nil, err
	}
	_ = w.WriteField("target", job.Target)
	if job.Driver != "" {
		_ = w.WriteField("driver", job.Driver)
	}
	w.Close()

	resp, err := http.Post(baseURL+"/jobs", w.FormDataContentType(), &body)
	if err != nil {
		return nil, fmt.Errorf("submit to provider: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusAccepted {
		b, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("provider returned %d: %s", resp.StatusCode, b)
	}

	var accepted struct {
		JobID string `json:"job_id"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&accepted); err != nil {
		return nil, err
	}

	// Poll until done
	for {
		time.Sleep(2 * time.Second)
		statusResp, err := http.Get(baseURL + "/jobs/" + accepted.JobID)
		if err != nil {
			return nil, fmt.Errorf("polling provider: %w", err)
		}
		var status struct {
			Status string `json:"status"`
			Error  string `json:"error"`
		}
		json.NewDecoder(statusResp.Body).Decode(&status)
		statusResp.Body.Close()

		switch status.Status {
		case "completed":
			res, err := http.Get(baseURL + "/jobs/" + accepted.JobID + "/result")
			if err != nil {
				return nil, err
			}
			defer res.Body.Close()
			return io.ReadAll(res.Body)
		case "failed":
			return nil, fmt.Errorf("provider job failed: %s", status.Error)
		}
	}
}

func (b *Broker) healthLoop() {
	ticker := time.NewTicker(30 * time.Second)
	for range ticker.C {
		b.mu.RLock()
		ids := make([]string, 0, len(b.providers))
		for id := range b.providers {
			ids = append(ids, id)
		}
		b.mu.RUnlock()

		for _, pid := range ids {
			b.mu.RLock()
			p := b.providers[pid]
			b.mu.RUnlock()
			if p == nil {
				continue
			}
			healthy := b.ping(p.URL)
			b.mu.Lock()
			p.Healthy = healthy
			p.LastHealthCheck = time.Now()
			b.mu.Unlock()
			if !healthy {
				log.Printf("provider %s is unhealthy", pid)
			}
		}
	}
}

func (b *Broker) ListProviders() []*Provider {
	b.mu.RLock()
	defer b.mu.RUnlock()
	out := make([]*Provider, 0, len(b.providers))
	for _, p := range b.providers {
		out = append(out, p)
	}
	return out
}

func (b *Broker) ping(baseURL string) bool {
	resp, err := http.Get(baseURL + "/capabilities")
	if err != nil {
		return false
	}
	resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}
