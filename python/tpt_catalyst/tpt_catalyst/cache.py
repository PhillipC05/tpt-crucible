"""Content-addressed compilation cache — skip unchanged operators."""

from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .ir import TptIr, OpNode


@dataclass
class CacheEntry:
    op_hash: str
    op_type: str
    node_id: int
    cached: bool = False
    output_hash: str = ""


@dataclass
class CacheStats:
    total_ops: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def hit_rate(self) -> float:
        return self.cache_hits / max(self.total_ops, 1)


class CompilationCache:
    """Content-addressed cache for compiled operators.

    Hashes each operator's type + attributes + input shapes.
    If the hash matches a cached entry, skip recompilation.
    """

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.cache_dir / "cache_index.json"
        self.index: dict[str, dict[str, Any]] = self._load_index()
        self.stats = CacheStats()

    def _load_index(self) -> dict[str, dict[str, Any]]:
        if self.index_path.exists():
            try:
                return json.loads(self.index_path.read_text())
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_index(self) -> None:
        self.index_path.write_text(json.dumps(self.index, indent=2))

    def compute_op_hash(self, node: OpNode) -> str:
        """Compute a hash for an operator node."""
        payload = json.dumps({
            "op_type": node.op_type,
            "name": node.name,
            "attributes": {k: str(v) for k, v in node.attributes.items()},
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def check(self, node: OpNode) -> bool:
        """Check if an operator is cached. Returns True if cache hit."""
        self.stats.total_ops += 1
        op_hash = self.compute_op_hash(node)
        if op_hash in self.index:
            self.stats.cache_hits += 1
            return True
        self.stats.cache_misses += 1
        return False

    def store(self, node: OpNode, output_data: bytes | None = None) -> str:
        """Store an operator in the cache."""
        op_hash = self.compute_op_hash(node)
        output_hash = ""
        if output_data:
            output_hash = hashlib.sha256(output_data).hexdigest()[:16]

        self.index[op_hash] = {
            "op_type": node.op_type,
            "node_id": node.id,
            "output_hash": output_hash,
        }
        self._save_index()
        return op_hash

    def invalidate(self, node: OpNode) -> None:
        """Remove an operator from the cache."""
        op_hash = self.compute_op_hash(node)
        self.index.pop(op_hash, None)
        self._save_index()

    def clear(self) -> None:
        """Clear the entire cache."""
        self.index.clear()
        self._save_index()

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_ops": self.stats.total_ops,
            "cache_hits": self.stats.cache_hits,
            "cache_misses": self.stats.cache_misses,
            "hit_rate": round(self.stats.hit_rate, 4),
            "cached_entries": len(self.index),
        }

    def filter_uncached(self, ir: TptIr) -> list[OpNode]:
        """Return only nodes that are NOT in the cache."""
        return [n for n in ir.graph.nodes if not self.check(n)]
