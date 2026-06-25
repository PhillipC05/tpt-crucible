"""Tests for TPT Mosaic module."""

import json
from pathlib import Path

from tpt_mosaic.partition import (
    LayerAssignment,
    PartitionPlan,
    HardwareTarget,
    auto_assign_layers,
)
from tpt_mosaic.bridge import InterHardwareBridge, BridgeConfig
from tpt_mosaic.orchestrator import MosaicOrchestrator


class TestLayerAssignment:
    def test_to_dict_roundtrip(self):
        a = LayerAssignment(layer_id=0, target=HardwareTarget.FPGA, reason="compute")
        d = a.to_dict()
        restored = LayerAssignment.from_dict(d)
        assert restored.layer_id == 0
        assert restored.target == HardwareTarget.FPGA

    def test_with_node_id(self):
        a = LayerAssignment(layer_id=5, target=HardwareTarget.SWARM, node_id=3)
        assert a.node_id == 3


class TestPartitionPlan:
    def test_auto_assign_layers(self):
        plan = auto_assign_layers(12)
        assert plan.layer_count == 12
        assert len(plan.targets_used) >= 2

    def test_layers_for_target(self):
        plan = auto_assign_layers(9)
        fpga = plan.layers_for_target(HardwareTarget.FPGA)
        assert len(fpga) >= 1

    def test_to_dict_roundtrip(self):
        plan = auto_assign_layers(6)
        d = plan.to_dict()
        restored = PartitionPlan.from_dict(d)
        assert restored.layer_count == 6

    def test_save_and_load(self, tmp_path):
        plan = auto_assign_layers(6)
        out = tmp_path / "plan.json"
        plan.save(out)
        assert out.exists()
        loaded = PartitionPlan.from_dict(json.loads(out.read_text()))
        assert loaded.layer_count == 6


class TestBridge:
    def test_usb_bridge(self):
        bridge = InterHardwareBridge()
        code = bridge.generate_bridge_code(HardwareTarget.FPGA, HardwareTarget.SWARM, "x")
        assert "USB" in code or "usb" in code.lower()

    def test_uart_bridge(self):
        bridge = InterHardwareBridge()
        code = bridge.generate_bridge_code(HardwareTarget.SWARM, HardwareTarget.ANALOG, "x")
        assert "UART" in code or "uart" in code.lower()

    def test_ethernet_bridge(self):
        config = BridgeConfig(fpga_to_analog_protocol="ethernet")
        bridge = InterHardwareBridge(config)
        code = bridge.generate_bridge_code(HardwareTarget.FPGA, HardwareTarget.ANALOG, "x")
        assert "Ethernet" in code or "ethernet" in code.lower()


class TestOrchestrator:
    def test_compile_full_plan(self, tmp_path):
        plan = auto_assign_layers(6)
        orch = MosaicOrchestrator(tmp_path)
        result = orch.compile(plan)
        assert result.success
        assert len(result.targets_compiled) >= 2

    def test_bridges_generated(self, tmp_path):
        plan = auto_assign_layers(9)
        orch = MosaicOrchestrator(tmp_path)
        result = orch.compile(plan)
        assert len(result.bridge_files) >= 1
