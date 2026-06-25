package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"github.com/tpt-crucible/synthesis-broker/internal/broker"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8081"
	}

	b := broker.New()

	mux := http.NewServeMux()
	mux.HandleFunc("POST /providers", registerProvider(b))
	mux.HandleFunc("GET /providers", listProviders(b))
	mux.HandleFunc("POST /jobs", submitJob(b))
	mux.HandleFunc("GET /jobs/{id}", getJob(b))
	mux.HandleFunc("GET /jobs/{id}/result", getJobResult(b))
	mux.HandleFunc("GET /health", healthHandler)

	log.Printf("TPT Synthesis Broker listening on :%s", port)
	log.Fatal(http.ListenAndServe(":"+port, mux))
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{
		"status":  "healthy",
		"service": "tpt-synthesis-broker",
		"version": "1.0.0",
	})
}

func registerProvider(b *broker.Broker) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var body struct {
			URL          string `json:"url"`
			Capabilities broker.Capabilities `json:"capabilities"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
			return
		}
		if body.URL == "" || body.Capabilities.ProviderID == "" {
			writeError(w, http.StatusBadRequest, "url and capabilities.provider_id are required")
			return
		}
		b.RegisterProvider(body.Capabilities, body.URL)
		writeJSON(w, http.StatusOK, map[string]string{"status": "registered"})
	}
}

func listProviders(b *broker.Broker) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, b.ListProviders())
	}
}

func submitJob(b *broker.Broker) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if err := r.ParseMultipartForm(512 << 20); err != nil {
			writeError(w, http.StatusBadRequest, "cannot parse multipart form")
			return
		}

		target := r.FormValue("target")
		if target == "" {
			writeError(w, http.StatusBadRequest, "target is required")
			return
		}

		file, _, err := r.FormFile("package")
		if err != nil {
			writeError(w, http.StatusBadRequest, "package file is required")
			return
		}
		defer file.Close()

		data, err := io.ReadAll(file)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to read package")
			return
		}

		driver := r.FormValue("driver")
		priority := 5

		job, err := b.SubmitJob(data, target, driver, priority)
		if err != nil {
			writeError(w, http.StatusServiceUnavailable, err.Error())
			return
		}

		writeJSON(w, http.StatusAccepted, map[string]interface{}{
			"job_id":            job.ID,
			"status":            "queued",
			"estimated_seconds": 120,
		})
	}
}

func getJob(b *broker.Broker) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		jobID := r.PathValue("id")
		job, ok := b.GetJob(jobID)
		if !ok {
			writeError(w, http.StatusNotFound, "job not found")
			return
		}

		resp := map[string]interface{}{
			"job_id":  job.ID,
			"status":  job.Status,
			"stage":   job.Stage,
			"elapsed_seconds": job.ElapsedSecs,
		}
		if job.Error != "" {
			resp["error"] = job.Error
		}
		if job.Status == broker.StatusCompleted && job.ResultData != nil {
			resp["result_size_bytes"] = len(job.ResultData)
		}
		writeJSON(w, http.StatusOK, resp)
	}
}

func getJobResult(b *broker.Broker) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		jobID := r.PathValue("id")
		job, ok := b.GetJob(jobID)
		if !ok || job.Status != broker.StatusCompleted || job.ResultData == nil {
			writeError(w, http.StatusNotFound, "result not available")
			return
		}
		w.Header().Set("Content-Type", "application/zip")
		w.Header().Set("Content-Disposition", fmt.Sprintf(`attachment; filename="%s.tptpkg"`, jobID))
		w.Header().Set("Content-Length", fmt.Sprintf("%d", len(job.ResultData)))
		w.WriteHeader(http.StatusOK)
		w.Write(job.ResultData)
	}
}

func writeJSON(w http.ResponseWriter, code int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, code int, msg string) {
	writeJSON(w, code, map[string]string{"error": msg})
}

