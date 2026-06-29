package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"strconv"
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

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	log.Printf("TPT Observer starting on :%s", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
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
	simTPS := 120.5
	if v := os.Getenv("TPT_SIM_TPS"); v != "" {
		if f, err := strconv.ParseFloat(v, 64); err == nil {
			simTPS = f
		}
	}
	ticker := time.NewTicker(time.Second)
	for range ticker.C {
		tps := telemetry.TokensPerSecond{
			Timestamp: time.Now(),
			TPS:       simTPS,
		}
		ws.Store.RecordTPS(tps)
	}
}
