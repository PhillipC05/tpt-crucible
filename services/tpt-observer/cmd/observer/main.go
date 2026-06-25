package main

import (
	"encoding/json"
	"log"
	"net/http"
	"time"

	"github.com/tpt-crucible/tpt-observer/internal/telemetry"
	"github.com/tpt-crucible/tpt-observer/internal/ws"
)

func main() {
	hub := ws.NewHub()
	go hub.Run()

	http.HandleFunc("/ws", hub.HandleWebSocket)
	http.HandleFunc("/api/health", healthHandler)
	http.HandleFunc("/api/telemetry", telemetryHandler)
	http.HandleFunc("/api/telemetry/tps", tpsHandler)

	log.Println("TPT Observer starting on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status": "healthy",
		"service": "tpt-observer",
		"version": "0.1.0",
	})
}

func telemetryHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	store := ws.Store
	json.NewEncoder(w).Encode(map[string]interface{}{
		"tps": store.GetLatestTPS(),
	})
}

func tpsHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	store := ws.Store
	tpsData := store.GetLatestTPS()
	if tpsData == nil {
		tpsData = []telemetry.TokensPerSecond{}
	}
	json.NewEncoder(w).Encode(tpsData)
}

func init() {
	go simulateTelemetry()
}

func simulateTelemetry() {
	ticker := time.NewTicker(time.Second)
	for range ticker.C {
		tps := telemetry.TokensPerSecond{
			Timestamp: time.Now(),
			TPS:       120.5,
		}
		ws.Store.RecordTPS(tps)
	}
}
