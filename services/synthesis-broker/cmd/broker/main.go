package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"github.com/gorilla/mux"
	"github.com/tpt-crucible/synthesis-broker/internal/cache"
)

func main() {
	cacheClient := cache.NewCacheClient("community_cache_index.json")
	r := mux.NewRouter()

	r.HandleFunc("/api/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
	}).Methods("GET")

	r.HandleFunc("/api/cache/lookup", func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			ModelSHA string `json:"model_sha256"`
			Board    string `json:"board"`
			FlagsHash string `json:"flags_hash"`
		}
		json.NewDecoder(r.Body).Decode(&req)
		entry := cacheClient.Lookup(req.ModelSHA, req.Board, req.FlagsHash)
		w.Header().Set("Content-Type", "application/json")
		if entry != nil {
			json.NewEncoder(w).Encode(entry)
		} else {
			json.NewEncoder(w).Encode(map[string]string{"status": "miss"})
		}
	}).Methods("POST")

	r.HandleFunc("/api/cache/publish", func(w http.ResponseWriter, r *http.Request) {
		var entry cache.CacheEntry
		json.NewDecoder(r.Body).Decode(&entry)
		cacheClient.Publish(entry)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "published"})
	}).Methods("POST")

	fmt.Println("Synthesis Broker starting on :8083")
	log.Fatal(http.ListenAndServe(":8083", r))
}
