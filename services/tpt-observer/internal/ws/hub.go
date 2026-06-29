package ws

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"
	"sync/atomic"

	"github.com/gorilla/websocket"
	"github.com/tpt-crucible/tpt-observer/internal/telemetry"
)

const maxConnsPerIP = 5

// ipCounter tracks open WS connections per source IP.
var ipCounter sync.Map // map[string]*int32

func allowedOrigin(r *http.Request) bool {
	origin := r.Header.Get("Origin")
	if origin == "" {
		// Same-origin or non-browser client; allow.
		return true
	}
	// In development, allow any localhost/127.0.0.1 origin.
	if strings.HasPrefix(origin, "http://localhost") ||
		strings.HasPrefix(origin, "http://127.0.0.1") ||
		strings.HasPrefix(origin, "https://localhost") {
		return true
	}
	// In production, require ALLOWED_ORIGIN env var to match.
	allowed := os.Getenv("ALLOWED_ORIGIN")
	if allowed != "" && origin == allowed {
		return true
	}
	log.Printf("WebSocket: rejected origin %q", origin)
	return false
}

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin:    allowedOrigin,
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
	ip   string
}

type TelemetryStore struct {
	mu        sync.RWMutex
	tps       []telemetry.TokensPerSecond
	bandwidth []telemetry.MemoryBandwidth
	thermal   []telemetry.ThermalDrift
	latency   []telemetry.NodeLatency
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
				decrementIP(client.ip)
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

func clientIP(r *http.Request) string {
	if forwarded := r.Header.Get("X-Forwarded-For"); forwarded != "" {
		return strings.SplitN(forwarded, ",", 2)[0]
	}
	ip := r.RemoteAddr
	if idx := strings.LastIndex(ip, ":"); idx != -1 {
		ip = ip[:idx]
	}
	return ip
}

func incrementIP(ip string) (int32, bool) {
	val, _ := ipCounter.LoadOrStore(ip, new(int32))
	counter := val.(*int32)
	n := atomic.AddInt32(counter, 1)
	return n, n <= maxConnsPerIP
}

func decrementIP(ip string) {
	if val, ok := ipCounter.Load(ip); ok {
		atomic.AddInt32(val.(*int32), -1)
	}
}

func (h *Hub) HandleWebSocket(w http.ResponseWriter, r *http.Request) {
	ip := clientIP(r)
	n, ok := incrementIP(ip)
	if !ok {
		decrementIP(ip)
		http.Error(w, fmt.Sprintf("too many connections from %s (%d)", ip, n), http.StatusTooManyRequests)
		return
	}

	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		decrementIP(ip)
		log.Printf("WebSocket upgrade error: %v", err)
		return
	}

	client := &Client{hub: h, conn: conn, send: make(chan []byte, 256), ip: ip}
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

// StreamPreFlight sends pre-flight results as a stream
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
