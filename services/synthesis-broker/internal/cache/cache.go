package cache

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"sync"
	"time"
)

type CacheEntry struct {
	ModelSHA256    string  `json:"model_sha256"`
	Board          string  `json:"board"`
	FlagsHash      string  `json:"flags_hash"`
	DownloadURL    string  `json:"download_url"`
	VerifiedAt     float64 `json:"verified_at"`
	AccuracyDelta  float64 `json:"accuracy_delta"`
}

type CacheClient struct {
	entries []CacheEntry
	mu      sync.RWMutex
	localPath string
}

func NewCacheClient(localPath string) *CacheClient {
	c := &CacheClient{
		entries:  make([]CacheEntry, 0),
		localPath: localPath,
	}
	c.loadIndex()
	return c
}

func (c *CacheClient) Lookup(modelSHA, board, flagsHash string) *CacheEntry {
	c.mu.RLock()
	defer c.mu.RUnlock()

	for _, entry := range c.entries {
		if entry.ModelSHA256 == modelSHA && entry.Board == board && entry.FlagsHash == flagsHash {
			return &entry
		}
	}
	return nil
}

func (c *CacheClient) Publish(entry CacheEntry) {
	c.mu.Lock()
	defer c.mu.Unlock()
	entry.VerifiedAt = float64(time.Now().Unix())
	c.entries = append(c.entries, entry)
	c.saveIndex()
}

func (c *CacheClient) loadIndex() {
	data, err := os.ReadFile(c.localPath)
	if err != nil {
		return
	}
	json.Unmarshal(data, &c.entries)
}

func (c *CacheClient) saveIndex() {
	data, _ := json.MarshalIndent(c.entries, "", "  ")
	os.WriteFile(c.localPath, data, 0644)
}

func (c *CacheClient) LookupByModel(modelSHA string) []CacheEntry {
	c.mu.RLock()
	defer c.mu.RUnlock()
	var results []CacheEntry
	for _, entry := range c.entries {
		if entry.ModelSHA256 == modelSHA {
			results = append(results, entry)
		}
	}
	return results
}

func ComputeFlagsHash(flags map[string]interface{}) string {
	data, _ := json.Marshal(flags)
	hash := sha256.Sum256(data)
	return hex.EncodeToString(hash[:])[:16]
}
