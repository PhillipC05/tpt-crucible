package ws

import (
	"encoding/json"
	"log"
	"net/http"
	"sync"

	"github.com/gorilla/websocket"
	"github.com/tpt-crucible/tpt-observer/internal/telemetry"
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		return true
	},
}

type Hub struct {
	clients    map[*Client]bool
	broadcast  chan []byte
	register   chan *Client
	unregister chan *Client
	mu         sync.RWMutex
}

type Client struct {
	hub  *Hub
	conn *websocket.Conn
	send chan []byte
}

type TelemetryStore struct {
	mu         sync.RWMutex
	tps        []telemetry.TokensPerSecond
	bandwidth  []telemetry.MemoryBandwidth
	thermal    []telemetry.ThermalDrift
	latency    []telemetry.NodeLatency
}

var Store = &TelemetryStore{}

func NewHub() *Hub {
	return &Hub{
		clients:    make(map[*Client]bool),
		broadcast:  make(chan []byte, 256),
		register:   make(chan *Client),
		unregister: make(chan *Client),
	}
}

func (h *Hub) Run() {
	for {
		select {
		case client := <-h.register:
			h.mu.Lock()
			h.clients[client] = true
			h.mu.Unlock()
			log.Printf("Client connected. Total: %d", len(h.clients))

		case client := <-h.unregister:
			h.mu.Lock()
			if _, ok := h.clients[client]; ok {
				delete(h.clients, client)
				close(client.send)
			}
			h.mu.Unlock()

		case message := <-h.broadcast:
			h.mu.RLock()
			for client := range h.clients {
				select {
				case client.send <- message:
				default:
					close(client.send)
					delete(h.clients, client)
				}
			}
			h.mu.RUnlock()
		}
	}
}

func (h *Hub) HandleWebSocket(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("WebSocket upgrade error: %v", err)
		return
	}

	client := &Client{hub: h, conn: conn, send: make(chan []byte, 256)}
	h.register <- client

	go client.writePump()
	go client.readPump()
}

func (c *Client) readPump() {
	defer func() {
		c.hub.unregister <- c
		c.conn.Close()
	}()

	for {
		_, _, err := c.conn.ReadMessage()
		if err != nil {
			break
		}
	}
}

func (c *Client) writePump() {
	defer c.conn.Close()

	for message := range c.send {
		if err := c.conn.WriteMessage(websocket.TextMessage, message); err != nil {
			break
		}
	}
}

func BroadcastTelemetry(msg telemetry.TelemetryMessage) {
	data, err := json.Marshal(msg)
	if err != nil {
		log.Printf("Marshal error: %v", err)
		return
	}
	// In production, this would use the hub's broadcast channel
	_ = data
}

// StreamingPreFlight sends pre-flight results as a stream
func (h *Hub) StreamPreFlight(results []map[string]interface{}) {
	for _, result := range results {
		msg := map[string]interface{}{
			"type":    "preflight",
			"payload": result,
		}
		data, _ := json.Marshal(msg)
		h.broadcast <- data
	}
}

func (s *TelemetryStore) RecordTPS(tps telemetry.TokensPerSecond) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.tps = append(s.tps, tps)
	if len(s.tps) > 1000 {
		s.tps = s.tps[1:]
	}
}

func (s *TelemetryStore) GetLatestTPS() []telemetry.TokensPerSecond {
	s.mu.RLock()
	defer s.mu.RUnlock()
	result := make([]telemetry.TokensPerSecond, len(s.tps))
	copy(result, s.tps)
	return result
}
