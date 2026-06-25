"""Tests for compilation cache."""

from tpt_catalyst.ir import TptIr, OpNode, ComputationalGraph, ModelMetadata
from tpt_catalyst.cache import CompilationCache, CacheStats


class TestCompilationCache:
    def test_check_miss(self, tmp_path):
        cache = CompilationCache(tmp_path / "cache")
        node = OpNode(id=0, op_type="matmul", name="layer0")
        assert cache.check(node) is False

    def test_store_and_check_hit(self, tmp_path):
        cache = CompilationCache(tmp_path / "cache")
        node = OpNode(id=0, op_type="matmul", name="layer0")
        cache.store(node)
        assert cache.check(node) is True

    def test_invalidate(self, tmp_path):
        cache = CompilationCache(tmp_path / "cache")
        node = OpNode(id=0, op_type="matmul", name="layer0")
        cache.store(node)
        cache.invalidate(node)
        assert cache.check(node) is False

    def test_stats(self, tmp_path):
        cache = CompilationCache(tmp_path / "cache")
        n1 = OpNode(id=0, op_type="matmul", name="l0")
        n2 = OpNode(id=1, op_type="relu", name="l1")
        cache.store(n1)
        cache.check(n1)
        cache.check(n2)
        stats = cache.get_stats()
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1

    def test_filter_uncached(self, tmp_path):
        cache = CompilationCache(tmp_path / "cache")
        ir = TptIr(
            version="1.0.0",
            metadata=ModelMetadata(name="test", source_format="pytorch"),
            graph=ComputationalGraph(
                nodes=[
                    OpNode(id=0, op_type="matmul", name="l0"),
                    OpNode(id=1, op_type="relu", name="l1"),
                ],
            ),
        )
        cache.store(ir.graph.nodes[0])
        uncached = cache.filter_uncached(ir)
        assert len(uncached) == 1
        assert uncached[0].op_type == "relu"
