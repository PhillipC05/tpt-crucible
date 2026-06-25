"""Tests for community cache, RISC-V ISA, photon, and intermittent computing."""

import numpy as np

from tpt_catalyst.community_cache import CommunityCacheClient, CacheEntry
from tpt_alloy.riscv_isa import RiscVCustomOp, RiscVExtensionGenerator
from tpt_photon.mzi_mesh import MziMeshGenerator, MziConfig, MziPhaseAngles
from tpt_catalyst.intermittent import (
    CheckpointPlanner, CheckpointConfig, CheckpointGranularity,
    CheckpointOp, EnergyEstimate,
)
from tpt_catalyst.ir import TptIr, OpNode, ComputationalGraph, ModelMetadata


class TestCommunityCache:
    def test_lookup_miss(self, tmp_path):
        client = CommunityCacheClient(cache_dir=tmp_path)
        result = client.lookup("abc123", "alveo")
        assert result is None

    def test_publish_and_lookup(self, tmp_path):
        client = CommunityCacheClient(cache_dir=tmp_path)
        entry = client.publish("abc123", "alveo", "https://example.com/pkg.tptpkg")
        result = client.lookup("abc123", "alveo")
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


class TestRiscVIsa:
    def test_custom_op_to_chisel(self):
        op = RiscVCustomOp(mnemonic="vmmul", opcode_space=0x0B, funct3=0, funct7=1, latency_cycles=4)
        chisel = op.to_chisel()
        assert "vmmul" in chisel
        assert "class VMMUL" in chisel
        assert "CustomInstruction" in chisel

    def test_custom_op_to_gas(self):
        op = RiscVCustomOp(mnemonic="vmmul", opcode_space=0x0B, funct3=0, funct7=1)
        gas = op.to_gas_asm()
        assert "vmmul" in gas
        assert ".insn" in gas

    def test_extension_generator(self):
        gen = RiscVExtensionGenerator()
        ops = gen.generate_extensions(["matmul", "fused_matmul_relu", "softmax"], top_n=3)
        assert len(ops) == 3
        assert ops[0].mnemonic == "vmmul"

    def test_generate_chisel(self):
        gen = RiscVExtensionGenerator()
        ops = gen.generate_extensions(["matmul", "softmax"])
        chisel = gen.generate_chisel(ops)
        assert "vmmul" in chisel
        assert "vsoftmax" in chisel

    def test_estimate_speedup(self):
        gen = RiscVExtensionGenerator()
        ops = [RiscVCustomOp("vmmul", 0x0B, 0, 1, 4)]
        speedup = gen.estimate_speedup(ops, {"matmul": 100})
        assert speedup > 1.0


class TestPhotonic:
    def test_svd_decompose(self):
        gen = MziMeshGenerator()
        weights = np.random.rand(4, 4)
        U, S, Vt = gen.svd_decompose(weights)
        assert U.shape == (4, 4)
        assert S.shape == (4,)

    def test_phase_encode(self):
        gen = MziMeshGenerator()
        weights = np.random.rand(4, 4)
        angles = gen.phase_encode(weights, layer_id=0)
        assert angles.layer_id == 0
        assert angles.phases.shape[0] == 4

    def test_generate_mesh_config(self):
        gen = MziMeshGenerator(MziConfig(mesh_size=4))
        angles = [gen.phase_encode(np.random.rand(4, 4), layer_id=i) for i in range(2)]
        config = gen.generate_mesh_config(angles)
        assert config["total_mzis"] > 0

    def test_estimate_accuracy(self):
        gen = MziMeshGenerator()
        original = np.array([[1.0, 2.0], [3.0, 4.0]])
        accuracy = gen.estimate_accuracy(original, original)
        assert accuracy == 1.0


class TestIntermittent:
    def test_insert_checkpoints(self):
        config = CheckpointConfig(granularity=CheckpointGranularity.LAYER)
        planner = CheckpointPlanner(config)
        ir = TptIr(
            version="1.0.0",
            metadata=ModelMetadata(name="test", source_format="pytorch"),
            graph=ComputationalGraph(
                nodes=[OpNode(id=i, op_type="matmul", name=f"layer{i}") for i in range(4)],
            ),
        )
        checkpoints = planner.insert_checkpoints(ir)
        assert len(checkpoints) == 4

    def test_validate_budget(self):
        config = CheckpointConfig(energy_budget_mj=10.0)
        planner = CheckpointPlanner(config)
        planner.energy_estimates = [EnergyEstimate("l0", 2.0), EnergyEstimate("l1", 3.0)]
        result = planner.validate_budget()
        assert result["budget_ok"] is True

    def test_validate_budget_exceeded(self):
        config = CheckpointConfig(energy_budget_mj=1.0)
        planner = CheckpointPlanner(config)
        planner.energy_estimates = [EnergyEstimate("l0", 5.0)]
        result = planner.validate_budget()
        assert result["budget_ok"] is False
