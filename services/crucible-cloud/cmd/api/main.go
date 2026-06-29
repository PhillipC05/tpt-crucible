package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"github.com/gorilla/mux"
	"github.com/tpt-crucible/crucible-cloud/internal/jobs"
)

func main() {
	manager := jobs.NewManager()
	r := mux.NewRouter()

	r.HandleFunc("/api/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
	}).Methods("GET")

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
		job := manager.SubmitJob(req.ModelName, req.Target)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(job)
	}).Methods("POST")

	r.HandleFunc("/api/jobs/{id}", func(w http.ResponseWriter, r *http.Request) {
		vars := mux.Vars(r)
		job := manager.GetJob(vars["id"])
		if job == nil {
			http.Error(w, "job not found", http.StatusNotFound)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(job)
	}).Methods("GET")

	fmt.Println("TPT Crucible Cloud API starting on :8082")
	log.Fatal(http.ListenAndServe(":8082", r))
}
