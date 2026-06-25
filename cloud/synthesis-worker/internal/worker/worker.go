package worker

import (
	"archive/zip"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
	"sync/atomic"
	"time"

	"github.com/tpt-crucible/synthesis-worker/internal/id"
)

type JobStatus string

const (
	StatusQueued    JobStatus = "queued"
	StatusRunning   JobStatus = "running"
	StatusCompleted JobStatus = "completed"
	StatusFailed    JobStatus = "failed"
)

type Job struct {
	ID          string
	Target      string
	Driver      string
	Status      JobStatus
	Stage       string
	ProgressPct int
	Error       string
	PackageData []byte
	ResultData  []byte
	ElapsedSecs float64
	CreatedAt   time.Time
}

type Worker struct {
	providerID    string
	maxConcurrent int
	currentLoad   atomic.Int64
	mu            sync.RWMutex
	jobs          map[string]*Job
	workDir       string
}

func New(providerID string, maxConcurrent int, workDir string) *Worker {
	if workDir == "" {
		workDir = os.TempDir()
	}
	return &Worker{
		providerID:    providerID,
		maxConcurrent: maxConcurrent,
		jobs:          make(map[string]*Job),
		workDir:       workDir,
	}
}

func (w *Worker) ProviderID() string { return w.providerID }
func (w *Worker) MaxConcurrent() int  { return w.maxConcurrent }
func (w *Worker) CurrentLoad() int    { return int(w.currentLoad.Load()) }

func (w *Worker) AcceptJob(packageData []byte, target, driver string) (*Job, error) {
	if w.maxConcurrent > 0 && w.CurrentLoad() >= w.maxConcurrent {
		return nil, fmt.Errorf("worker at capacity")
	}
	job := &Job{
		ID:          id.New(),
		Target:      target,
		Driver:      driver,
		Status:      StatusQueued,
		PackageData: packageData,
		CreatedAt:   time.Now(),
	}
	w.mu.Lock()
	w.jobs[job.ID] = job
	w.mu.Unlock()

	go w.run(job)
	return job, nil
}

func (w *Worker) GetJob(jobID string) (*Job, bool) {
	w.mu.RLock()
	defer w.mu.RUnlock()
	j, ok := w.jobs[jobID]
	return j, ok
}

func (w *Worker) run(job *Job) {
	w.currentLoad.Add(1)
	defer w.currentLoad.Add(-1)

	start := time.Now()
	w.setStatus(job, StatusRunning, "extracting", 0)

	workDir := filepath.Join(w.workDir, "tpt-synthesis-"+job.ID)
	if err := os.MkdirAll(workDir, 0755); err != nil {
		w.failJob(job, "setup: "+err.Error())
		return
	}
	defer os.RemoveAll(workDir)

	// Extract .tptpkg (ZIP) to work dir
	if err := extractZip(job.PackageData, workDir); err != nil {
		w.failJob(job, "extract: "+err.Error())
		return
	}

	irPath := filepath.Join(workDir, "ir", "model.tptir")
	if _, err := os.Stat(irPath); err != nil {
		w.failJob(job, "ir/model.tptir not found in package")
		return
	}

	outDir := filepath.Join(workDir, "targets", job.Target)
	if err := os.MkdirAll(outDir, 0755); err != nil {
		w.failJob(job, "mkdir targets: "+err.Error())
		return
	}

	switch job.Target {
	case "fusion":
		if err := w.runFusion(job, workDir, irPath, outDir); err != nil {
			w.failJob(job, err.Error())
			return
		}
	case "alloy":
		if err := w.runAlloy(job, workDir, irPath, outDir); err != nil {
			w.failJob(job, err.Error())
			return
		}
	default:
		w.failJob(job, "unsupported target: "+job.Target)
		return
	}

	// Repack to .tptpkg
	w.setStatus(job, StatusRunning, "packaging", 90)
	result, err := packZip(workDir)
	if err != nil {
		w.failJob(job, "repack: "+err.Error())
		return
	}

	w.mu.Lock()
	job.Status = StatusCompleted
	job.Stage = ""
	job.ProgressPct = 100
	job.ResultData = result
	job.ElapsedSecs = time.Since(start).Seconds()
	w.mu.Unlock()

	log.Printf("job %s completed in %.1fs", job.ID, job.ElapsedSecs)
}

func (w *Worker) runFusion(job *Job, workDir, irPath, outDir string) error {
	// Convert TPT-IR to Verilog via tpt-catalyst (Python)
	w.setStatus(job, StatusRunning, "yosys:synth", 20)
	rtlPath := filepath.Join(outDir, "top.v")

	if err := w.runCmd(workDir, "python3", "-m", "tpt_fusion.rtl_gen",
		"--ir", irPath, "--out", rtlPath); err != nil {
		// Fall back to a synthesis-only pass if RTL is already present
		if _, statErr := os.Stat(rtlPath); statErr != nil {
			return fmt.Errorf("RTL generation: %w", err)
		}
		log.Printf("RTL gen failed (%v) but RTL exists — continuing with Yosys", err)
	}

	// Yosys synthesis
	w.setStatus(job, StatusRunning, "yosys:synth", 40)
	synthJson := filepath.Join(outDir, "synth.json")
	yosysScript := fmt.Sprintf("read_verilog %s; synth -top top; write_json %s", rtlPath, synthJson)
	if err := w.runCmd(workDir, "yosys", "-p", yosysScript); err != nil {
		return fmt.Errorf("yosys: %w", err)
	}

	// Nextpnr place-and-route (ECP5 as default FPGA family)
	w.setStatus(job, StatusRunning, "nextpnr:place", 65)
	bitstreamPath := filepath.Join(outDir, "bitstream.bit")
	if err := w.runCmd(workDir, "nextpnr-ecp5",
		"--json", synthJson,
		"--lpf-allow-unconstrained",
		"--textcfg", bitstreamPath+".config",
	); err != nil {
		return fmt.Errorf("nextpnr: %w", err)
	}

	// Pack bitstream config
	w.setStatus(job, StatusRunning, "nextpnr:pack", 80)
	if err := w.runCmd(workDir, "ecppack", "--input", bitstreamPath+".config", "--bit", bitstreamPath); err != nil {
		log.Printf("ecppack warning: %v (config retained)", err)
	}

	return nil
}

func (w *Worker) runAlloy(job *Job, workDir, irPath, outDir string) error {
	// Alloy firmware generation via tpt-alloy (Python)
	w.setStatus(job, StatusRunning, "alloy:partition", 30)
	if err := w.runCmd(workDir, "python3", "-m", "tpt_alloy.firmware_gen",
		"--ir", irPath, "--out", outDir, "--target", "esp32"); err != nil {
		return fmt.Errorf("alloy firmware gen: %w", err)
	}
	w.setStatus(job, StatusRunning, "alloy:compile", 70)
	return nil
}

func (w *Worker) runCmd(dir string, name string, args ...string) error {
	cmd := exec.Command(name, args...)
	cmd.Dir = dir
	out, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("%s: %w\n%s", name, err, out)
	}
	return nil
}

func (w *Worker) setStatus(job *Job, status JobStatus, stage string, pct int) {
	w.mu.Lock()
	job.Status = status
	job.Stage = stage
	job.ProgressPct = pct
	w.mu.Unlock()
}

func (w *Worker) failJob(job *Job, reason string) {
	w.mu.Lock()
	job.Status = StatusFailed
	job.Error = reason
	w.mu.Unlock()
	log.Printf("job %s failed: %s", job.ID, reason)
}

func extractZip(data []byte, dest string) error {
	r, err := zip.NewReader(bytes.NewReader(data), int64(len(data)))
	if err != nil {
		return err
	}
	for _, f := range r.File {
		path := filepath.Join(dest, filepath.Clean(f.Name))
		if f.FileInfo().IsDir() {
			os.MkdirAll(path, 0755)
			continue
		}
		os.MkdirAll(filepath.Dir(path), 0755)
		rc, err := f.Open()
		if err != nil {
			return err
		}
		out, err := os.Create(path)
		if err != nil {
			rc.Close()
			return err
		}
		_, err = io.Copy(out, rc)
		rc.Close()
		out.Close()
		if err != nil {
			return err
		}
	}
	return nil
}

func packZip(dir string) ([]byte, error) {
	var buf bytes.Buffer
	w := zip.NewWriter(&buf)

	err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() {
			return err
		}
		rel, err := filepath.Rel(dir, path)
		if err != nil {
			return err
		}
		f, err := w.Create(filepath.ToSlash(rel))
		if err != nil {
			return err
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		_, err = f.Write(data)
		return err
	})
	if err != nil {
		return nil, err
	}
	if err := w.Close(); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

// SynthesisConstraints mirrors the driver manifest fields relevant to synthesis.
type SynthesisConstraints struct {
	MaxClockMHz    float64
	MaxLUTs        int
	MaxDSPSlices   int
	MaxBRAMKbits   int
	TimingMarginNS float64
}

func LoadConstraintsFromManifest(manifestJSON []byte) (*SynthesisConstraints, error) {
	var m struct {
		Synthesis struct {
			MaxClockMHz    float64 `json:"max_clock_mhz"`
			MaxLUTs        int     `json:"max_luts"`
			MaxDSPSlices   int     `json:"max_dsp_slices"`
			MaxBRAMKbits   int     `json:"max_bram_kbits"`
			TimingMarginNS float64 `json:"timing_margin_ns"`
		} `json:"synthesis"`
	}
	if err := json.Unmarshal(manifestJSON, &m); err != nil {
		return nil, err
	}
	return &SynthesisConstraints{
		MaxClockMHz:    m.Synthesis.MaxClockMHz,
		MaxLUTs:        m.Synthesis.MaxLUTs,
		MaxDSPSlices:   m.Synthesis.MaxDSPSlices,
		MaxBRAMKbits:   m.Synthesis.MaxBRAMKbits,
		TimingMarginNS: m.Synthesis.TimingMarginNS,
	}, nil
}
