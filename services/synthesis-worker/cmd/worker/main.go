package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"github.com/gorilla/mux"
	"github.com/tpt-crucible/synthesis-worker/internal/job"
)

func main() {
	manager := job.NewManager()
	r := mux.NewRouter()

	r.HandleFunc("/api/jobs", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(manager.ListJobs())
	}).Methods("GET")

	r.HandleFunc("/api/jobs", func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			ModelName string `json:"model_name"`
			Target    string `json:"target"`
		}
		json.NewDecoder(r.Body).Decode(&req)

		j := manager.SubmitJob(req.ModelName, req.Target)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(j)
	}).Methods("POST")

	r.HandleFunc("/api/jobs/{id}", func(w http.ResponseWriter, r *http.Request) {
		vars := mux.Vars(r)
		j := manager.GetJob(vars["id"])
		if j == nil {
			http.Error(w, "job not found", http.StatusNotFound)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(j)
	}).Methods("GET")

	r.HandleFunc("/api/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
	}).Methods("GET")

	fmt.Println("Synthesis Worker starting on :8081")
	log.Fatal(http.ListenAndServe(":8081", r))
}
