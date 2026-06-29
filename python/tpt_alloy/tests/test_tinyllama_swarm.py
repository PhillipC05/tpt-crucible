"""Integration tests: TinyLlama on 16× ESP32 swarm — partition, firmware, KV cache no-OOM."""

import json
import pytest
from tpt_alloy.topology import Topology
from tpt_alloy.partition import PartitionConfig, partition_model
from tpt_alloy.firmware import FirmwareTarget, FirmwareRtos, generate_firmware
from tpt_alloy.kv_cache import KvCachePlanner

# TinyLlama 1.1B architecture constants
TINYLLAMA_LAYERS = 22
TINYLLAMA_KV_HEADS = 4       # grouped-query attention
TINYLLAMA_HIDDEN = 2048
NODE_COUNT = 16
TOPOLOGY = Topology.grid2d(4, 4)

# ESP32 with 4 MB PSRAM (standard WROVER module)
ESP32_PSRAM_BYTES = 4 * 1024 * 1024
GENERATION_TOKENS = 128


# ---------------------------------------------------------------------------
# Partition tests
# ---------------------------------------------------------------------------

class TestTinyLlamaPartition:
    def setup_method(self):
        config = PartitionConfig(topology=TOPOLOGY)
        self.partitions = partition_model(TINYLLAMA_LAYERS, config)

    def test_all_layers_assigned(self):
        assigned = [l for p in self.partitions for l in p.assigned_layers]
        assert len(assigned) == TINYLLAMA_LAYERS

    def test_correct_node_count(self):
        assert len(self.partitions) == NODE_COUNT

    def test_no_duplicate_layer_assignments(self):
        assigned = [l for p in self.partitions for l in p.assigned_layers]
        assert len(assigned) == len(set(assigned)), "Layers assigned to more than one node"

    def test_balanced_distribution(self):
        # With 22 layers across 16 nodes, max per node is ceil(22/16) = 2,
        # but the round-robin stride used by partition_model is 2, so at most
        # ceil(22/16) + 1 = 3 in the worst case (tolerance for non-METIS path).
        max_layers = max(len(p.assigned_layers) for p in self.partitions)
        assert max_layers <= 3, f"Imbalanced: one node has {max_layers} layers"

    def test_node_ids_are_unique(self):
        ids = [p.node_id for p in self.partitions]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Firmware generation tests
# ---------------------------------------------------------------------------

class TestTinyLlamaFirmware:
    def setup_method(self):
        config = PartitionConfig(topology=TOPOLOGY)
        self.partitions = partition_model(TINYLLAMA_LAYERS, config)

    def test_firmware_generated_for_all_nodes(self):
        for p in self.partitions:
            bundle = generate_firmware(p, FirmwareTarget.ESP32)
            assert bundle.node_id == p.node_id
            assert len(bundle.source_code) > 0

    def test_firmware_config_json_valid(self):
        bundle = generate_firmware(self.partitions[0], FirmwareTarget.ESP32)
        cfg = json.loads(bundle.config_json)
        assert "node_id" in cfg
        assert "layers" in cfg

    def test_firmware_references_node_id(self):
        for p in self.partitions:
            bundle = generate_firmware(p, FirmwareTarget.ESP32)
            assert str(p.node_id) in bundle.source_code

    def test_zephyr_firmware_for_riscv(self):
        bundle = generate_firmware(
            self.partitions[0],
            FirmwareTarget.RISCV,
            rtos=FirmwareRtos.ZEPHYR,
        )
        assert "zephyr" in bundle.source_code.lower()
        assert "k_sleep" in bundle.source_code

    def test_riscv_bare_metal_firmware(self):
        bundle = generate_firmware(self.partitions[0], FirmwareTarget.RISCV)
        assert "stdio.h" in bundle.source_code
        assert "zephyr" not in bundle.source_code.lower()


# ---------------------------------------------------------------------------
# KV cache no-OOM tests — 128-token generation on 4 MB PSRAM nodes
# ---------------------------------------------------------------------------

class TestTinyLlamaKvCacheNoOOM:
    """Verify no out-of-memory risk on TinyLlama 16× ESP32 across 128-token generation."""

    def _make_plan(self, **kwargs):
        planner = KvCachePlanner(bytes_per_head=2048, tokens_per_layer=GENERATION_TOKENS)
        return planner, planner.plan(
            total_layers=TINYLLAMA_LAYERS,
            kv_heads=TINYLLAMA_KV_HEADS,
            node_count=NODE_COUNT,
            memory_per_node_bytes=ESP32_PSRAM_BYTES,
            **kwargs,
        )

    def test_no_oom_warnings(self):
        planner, plan = self._make_plan()
        warnings = planner.validate_no_oom(plan, memory_per_node_bytes=ESP32_PSRAM_BYTES)
        assert warnings == [], f"OOM risk detected on nodes: {[w['node_id'] for w in warnings]}"

    def test_active_nodes_support_128_tokens(self):
        _, plan = self._make_plan()
        active = [a for a in plan.allocations if a.layer_ids]
        assert active, "No nodes have layers assigned"
        for alloc in active:
            assert alloc.max_tokens >= GENERATION_TOKENS, (
                f"Node {alloc.node_id} supports only {alloc.max_tokens} tokens"
            )

    def test_per_node_memory_within_psram(self):
        _, plan = self._make_plan()
        for alloc in plan.allocations:
            assert alloc.memory_bytes <= ESP32_PSRAM_BYTES, (
                f"Node {alloc.node_id} needs {alloc.memory_bytes} bytes, "
                f"exceeds {ESP32_PSRAM_BYTES}"
            )

    def test_all_layers_covered_by_kv_plan(self):
        _, plan = self._make_plan()
        assigned = {l for a in plan.allocations for l in a.layer_ids}
        assert assigned == set(range(TINYLLAMA_LAYERS))

    def test_plan_serialises(self):
        _, plan = self._make_plan()
        d = plan.to_dict()
        assert d["max_generation_tokens"] >= 0
        assert d["node_count"] == NODE_COUNT
        assert len(d["allocations"]) == NODE_COUNT
