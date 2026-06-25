"""Community Compilation Cache — share and reuse FPGA synthesis results."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import hashlib
import json
import time
from pathlib import Path


@dataclass
class CacheEntry:
    model_sha256: str
    board: str
    flags_hash: str
    download_url: str
    verified_at: float = 0.0
    accuracy_delta: float = 0.0
    synthesis_time_s: float = 0.0
    artifact_size_mb: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_sha256": self.model_sha256,
            "board": self.board,
            "flags_hash": self.flags_hash,
            "download_url": self.download_url,
            "verified_at": self.verified_at,
            "accuracy_delta": self.accuracy_delta,
            "synthesis_time_s": self.synthesis_time_s,
            "artifact_size_mb": self.artifact_size_mb,
        }


class CommunityCacheClient:
    """Client for community compilation cache."""

    def __init__(self, cache_dir: Path | None = None, ttl_seconds: int = 3600):
        self.cache_dir = cache_dir or Path.home() / ".tpt-crucible" / "community-cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self.index: list[CacheEntry] = []
        self._load_index()

    def _load_index(self) -> None:
        index_file = self.cache_dir / "community_cache_index.json"
        if index_file.exists():
            try:
                data = json.loads(index_file.read_text())
                self.index = [CacheEntry(**e) for e in data]
            except (json.JSONDecodeError, KeyError):
                self.index = []

    def _save_index(self) -> None:
        index_file = self.cache_dir / "community_cache_index.json"
        index_file.write_text(json.dumps([e.to_dict() for e in self.index], indent=2))

    def lookup(self, model_sha256: str, board: str, flags: dict[str, Any] | None = None) -> CacheEntry | None:
        flags_hash = self._hash_flags(flags or {})
        for entry in self.index:
            if entry.model_sha256 == model_sha256 and entry.board == board and entry.flags_hash == flags_hash:
                if time.time() - entry.verified_at < self.ttl_seconds:
                    return entry
        return None

    def publish(
        self,
        model_sha256: str,
        board: str,
        download_url: str,
        accuracy_delta: float = 0.0,
        synthesis_time_s: float = 0.0,
        artifact_size_mb: float = 0.0,
        flags: dict[str, Any] | None = None,
    ) -> CacheEntry:
        flags_hash = self._hash_flags(flags or {})
        entry = CacheEntry(
            model_sha256=model_sha256,
            board=board,
            flags_hash=flags_hash,
            download_url=download_url,
            verified_at=time.time(),
            accuracy_delta=accuracy_delta,
            synthesis_time_s=synthesis_time_s,
            artifact_size_mb=artifact_size_mb,
        )
        self.index.append(entry)
        self._save_index()
        return entry

    def search(self, model_sha256: str | None = None, board: str | None = None) -> list[CacheEntry]:
        results = self.index
        if model_sha256:
            results = [e for e in results if e.model_sha256 == model_sha256]
        if board:
            results = [e for e in results if e.board == board]
        return results

    def clear_expired(self) -> int:
        now = time.time()
        before = len(self.index)
        self.index = [e for e in self.index if now - e.verified_at < self.ttl_seconds]
        self._save_index()
        return before - len(self.index)

    def _hash_flags(self, flags: dict[str, Any]) -> str:
        data = json.dumps(flags, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]
