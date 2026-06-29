"""Tests for SafeTensors/HF ingestion, KV cache, and fault tolerance."""

from pathlib import Path
import json

from tpt_catalyst.safetensors_ingest import SafeTensorsIngester, HuggingFaceIngester
from tpt_alloy.kv_cache import KvCachePlanner, KvCachePlan, KvAllocation
from tpt_alloy.fault_tolerance import (
    FaultToleranceManager, HeartbeatConfig, NodeStatus, FaultToleranceReport,
)


class TestSafeTensorsIngester:
    def test_ingest_stub(self, tmp_path):
        f = tmp_path / "model.safetensors"
        f.write_bytes(b"")
        ingester = SafeTensorsIngester()
        ir = ingester.ingest(f)
        assert ir.metadata.source_format == "safetensors"

    def test_available_flag(self):
        ingester = SafeTensorsIngester()
        assert isinstance(ingester._available, bool)


class TestHuggingFaceIngester:
    def test_ingest_with_config(self, tmp_path):
        model_dir = tmp_path / "model"
        model_dir.mkdir()
        config = {
            "model_type": "llama",
            "architectures": ["LlamaForCausalLM"],
            "hidden_size": 2048,
            "num_hidden_layers": 22,
            "num_attention_heads": 32,
        }
        (model_dir / "config.json").write_text(json.dumps(config))
        ingester = HuggingFaceIngester()
        ir = ingester.ingest(model_dir)
        assert len(ir.graph.nodes) == 66
        assert "llama" in ir.metadata.source_format

    def test_ingest_from_weights(self, tmp_path):
        model_dir = tmp_path / "model"
        model_dir.mkdir()
        (model_dir / "model.safetensors").write_bytes(b"")
        (model_dir / "model.bin").write_bytes(b"")
        ingester = HuggingFaceIngester()
        ir = ingester.ingest(model_dir)
        assert len(ir.graph.nodes) == 2

    def test_pull_model(self, tmp_path):
        ingester = HuggingFaceIngester(cache_dir=tmp_path)
        path = ingester.pull_model("test/model")
        assert "test" in str(path)


class TestKvCachePlanner:
    def test_plan(self):
        planner = KvCachePlanner()
        plan = planner.plan(total_layers=22, kv_heads=32, node_count=16)
        assert plan.total_layers == 22
        assert len(plan.allocations) == 16
        assert plan.total_memory_bytes > 0

    def test_validate_no_oom(self):
        planner = KvCachePlanner()
        plan = planner.plan(total_layers=22, kv_heads=32, node_count=16)
        warnings = planner.validate_no_oom(plan, memory_per_node_bytes=1024*1024)
        assert isinstance(warnings, list)

    def test_plan_to_dict(self):
        planner = KvCachePlanner()
        plan = planner.plan(total_layers=8, kv_heads=8, node_count=4)
        d = plan.to_dict()
        assert "allocations" in d
        assert d["node_count"] == 4


class TestFaultTolerance:
    def test_register_and_heartbeat(self):
        ft = FaultToleranceManager(HeartbeatConfig(timeout_ms=100))
        ft.register_node(0)
        ft.receive_heartbeat(0)
        assert ft.nodes[0].is_alive

    def test_timeout_detection(self):
        ft = FaultToleranceManager(HeartbeatConfig(timeout_ms=0, max_missed=1))
        ft.register_node(0)
        ft.nodes[0].last_heartbeat = 0.0
        dead = ft.check_timeouts()
        assert 0 in dead

    def test_reroute_layers(self):
        ft = FaultToleranceManager()
        ft.register_node(0)
        ft.register_node(1)
        ft.nodes[0].assigned_layers = [0, 1, 2]
        ft.nodes[1].assigned_layers = [3, 4]
        reassignments = ft.reroute_layers(0, [1])
        assert len(reassignments) == 3
        assert ft.nodes[0].assigned_layers == []

    def test_recovery(self):
        ft = FaultToleranceManager()
        ft.register_node(0)
        ft.nodes[0].status = "dead"
        ft.recover_node(0)
        assert ft.nodes[0].is_alive

    def test_report(self):
        ft = FaultToleranceManager()
        ft.register_node(0)
        ft.register_node(1)
        report = ft.get_report()
        assert report.total_nodes == 2
        assert report.health_score == 1.0
