package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"mime/multipart"
	"net/http"
	"os"
	"os/exec"
	"strconv"
	"strings"

	"github.com/tpt-crucible/synthesis-worker/internal/worker"
)

func main() {
	port := env("PORT", "9090")
	providerID := env("PROVIDER_ID", mustHostname())
	brokerURL := os.Getenv("BROKER_URL")
	maxJobs, _ := strconv.Atoi(env("MAX_CONCURRENT_JOBS", "4"))
	workDir := env("WORK_DIR", "")

	w := worker.New(providerID, maxJobs, workDir)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /capabilities", capabilitiesHandler(w))
	mux.HandleFunc("POST /jobs", submitJobHandler(w))
	mux.HandleFunc("GET /jobs/{id}", getJobHandler(w))
	mux.HandleFunc("GET /jobs/{id}/result", getJobResultHandler(w))
	mux.HandleFunc("GET /health", healthHandler)

	if brokerURL != "" {
		if err := registerWithBroker(brokerURL, port, w); err != nil {
			log.Printf("warning: could not register with broker at %s: %v", brokerURL, err)
		} else {
			log.Printf("registered with broker at %s", brokerURL)
		}
	}

	log.Printf("TPT Synthesis Worker %s listening on :%s", providerID, port)
	log.Fatal(http.ListenAndServe(":"+port, mux))
}

func capabilitiesHandler(w *worker.Worker) http.HandlerFunc {
	return func(rw http.ResponseWriter, r *http.Request) {
		yosys := toolVersion("yosys", "--version")
		nextpnr := toolVersion("nextpnr-ecp5", "--version")

		targets := []string{"fusion"}
		if toolExists("python3", "-c", "import tpt_alloy") {
			targets = append(targets, "alloy")
		}

		writeJSON(rw, http.StatusOK, map[string]interface{}{
			"provider_id":         w.ProviderID(),
			"targets":             targets,
			"yosys_version":       yosys,
			"nextpnr_version":     nextpnr,
			"max_concurrent_jobs": w.MaxConcurrent(),
			"current_load":        w.CurrentLoad(),
		})
	}
}

func submitJobHandler(w *worker.Worker) http.HandlerFunc {
	return func(rw http.ResponseWriter, r *http.Request) {
		if err := r.ParseMultipartForm(512 << 20); err != nil {
			writeError(rw, http.StatusBadRequest, "cannot parse multipart form")
			return
		}

		target := r.FormValue("target")
		if target == "" {
			writeError(rw, http.StatusBadRequest, "target is required")
			return
		}

		file, _, err := r.FormFile("package")
		if err != nil {
			writeError(rw, http.StatusBadRequest, "package file is required")
			return
		}
		defer file.Close()

		data, err := io.ReadAll(file)
		if err != nil {
			writeError(rw, http.StatusInternalServerError, "failed to read package")
			return
		}

		job, err := w.AcceptJob(data, target, r.FormValue("driver"))
		if err != nil {
			writeError(rw, http.StatusServiceUnavailable, err.Error())
			return
		}

		writeJSON(rw, http.StatusAccepted, map[string]interface{}{
			"job_id": job.ID,
			"status": "queued",
		})
	}
}

func getJobHandler(w *worker.Worker) http.HandlerFunc {
	return func(rw http.ResponseWriter, r *http.Request) {
		job, ok := w.GetJob(r.PathValue("id"))
		if !ok {
			writeError(rw, http.StatusNotFound, "job not found")
			return
		}
		resp := map[string]interface{}{
			"job_id":          job.ID,
			"status":          job.Status,
			"stage":           job.Stage,
			"progress_pct":    job.ProgressPct,
			"elapsed_seconds": job.ElapsedSecs,
		}
		if job.Error != "" {
			resp["error"] = job.Error
		}
		if job.Status == worker.StatusCompleted && job.ResultData != nil {
			resp["result_size_bytes"] = len(job.ResultData)
		}
		writeJSON(rw, http.StatusOK, resp)
	}
}

func getJobResultHandler(w *worker.Worker) http.HandlerFunc {
	return func(rw http.ResponseWriter, r *http.Request) {
		job, ok := w.GetJob(r.PathValue("id"))
		if !ok || job.Status != worker.StatusCompleted || job.ResultData == nil {
			writeError(rw, http.StatusNotFound, "result not available")
			return
		}
		rw.Header().Set("Content-Type", "application/zip")
		rw.Header().Set("Content-Disposition", fmt.Sprintf(`attachment; filename="%s.tptpkg"`, job.ID))
		rw.Write(job.ResultData)
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "healthy", "service": "tpt-synthesis-worker"})
}

func registerWithBroker(brokerURL, port string, w *worker.Worker) error {
	selfURL := fmt.Sprintf("http://%s:%s", mustHostname(), port)
	if extURL := os.Getenv("EXTERNAL_URL"); extURL != "" {
		selfURL = extURL
	}

	targets := []string{"fusion"}
	if toolExists("python3", "-c", "import tpt_alloy") {
		targets = append(targets, "alloy")
	}

	body := map[string]interface{}{
		"url": selfURL,
		"capabilities": map[string]interface{}{
			"provider_id":         w.ProviderID(),
			"targets":             targets,
			"yosys_version":       toolVersion("yosys", "--version"),
			"nextpnr_version":     toolVersion("nextpnr-ecp5", "--version"),
			"max_concurrent_jobs": w.MaxConcurrent(),
			"current_load":        0,
		},
	}
	data, _ := json.Marshal(body)
	resp, err := http.Post(brokerURL+"/providers", "application/json", bytes.NewReader(data))
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		b, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("broker returned %d: %s", resp.StatusCode, b)
	}
	return nil
}

func toolVersion(name string, args ...string) string {
	out, err := exec.Command(name, args...).Output()
	if err != nil {
		return "not installed"
	}
	line := strings.SplitN(strings.TrimSpace(string(out)), "\n", 2)[0]
	return line
}

func toolExists(name string, args ...string) bool {
	return exec.Command(name, args...).Run() == nil
}

func uploadMultipart(url string, packageData []byte, jobID string) (*http.Response, error) {
	var body bytes.Buffer
	w := multipart.NewWriter(&body)
	part, _ := w.CreateFormFile("package", jobID+".tptpkg")
	part.Write(packageData)
	w.Close()
	return http.Post(url, w.FormDataContentType(), &body)
}

func mustHostname() string {
	h, err := os.Hostname()
	if err != nil {
		return "localhost"
	}
	return h
}

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func writeJSON(w http.ResponseWriter, code int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, code int, msg string) {
	writeJSON(w, code, map[string]string{"error": msg})
}

// uploadMultipart is available for future CLI tooling
var _ = uploadMultipart
