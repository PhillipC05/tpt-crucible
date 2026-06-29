"""Tests for community cache Go integration and CLI integrations."""

from pathlib import Path
import json

from tpt_catalyst.community_cache import CommunityCacheClient, CacheEntry


class TestCommunityCacheClient:
    def test_lookup_miss(self, tmp_path):
        client = CommunityCacheClient(cache_dir=tmp_path)
        result = client.lookup("abc123", "alveo", {})
        assert result is None

    def test_publish_and_lookup(self, tmp_path):
        client = CommunityCacheClient(cache_dir=tmp_path)
        entry = client.publish("abc123", "alveo", "https://example.com/pkg.tptpkg")
        result = client.lookup("abc123", "alveo", {})
        assert result is not None
        assert result.download_url == "https://example.com/pkg.tptpkg"

    def test_search(self, tmp_path):
        client = CommunityCacheClient(cache_dir=tmp_path)
        client.publish("abc123", "alveo", "url1")
        client.publish("abc123", "esp32", "url2")
        results = client.search(board="alveo")
        assert len(results) == 1

    def test_clear_expired(self, tmp_path):
        client = CommunityCacheClient(cache_dir=tmp_path, ttl_seconds=0)
        client.publish("abc123", "alveo", "url1")
        cleared = client.clear_expired()
        assert cleared == 1

    def test_publish_with_flags(self, tmp_path):
        client = CommunityCacheClient(cache_dir=tmp_path)
        entry = client.publish("abc123", "alveo", "url1", flags={"opt": "speed"})
        result = client.lookup("abc123", "alveo", {"opt": "speed"})
        assert result is not None
        assert result.flags_hash == client._hash_flags({"opt": "speed"})
