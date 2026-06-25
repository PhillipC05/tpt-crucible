"""Tests for .tptpkg module integration."""

from pathlib import Path
import numpy as np

from tpt_alloy.package_writer import write_alloy_artifacts
from tpt_alloy.partition import Partition
from tpt_alloy.firmware import FirmwareTarget
from tpt_fusion.package_writer import write_fusion_artifacts
from tpt_fusion.board import get_board
from tpt_fusion.mac_array import MacConfig
from tpt_element.package_writer import write_element_artifacts


class TestAlloyPackageWriter:
    def test_write_artifacts(self, tmp_path):
        partitions = [
            Partition(node_id=0, assigned_layers=[0, 1]),
            Partition(node_id=1, assigned_layers=[2, 3]),
        ]
        artifacts = write_alloy_artifacts(partitions, FirmwareTarget.ESP32, tmp_path)
        assert len(artifacts) >= 3
        assert any("node_0.c" in v for v in artifacts.values())

    def test_topology_written(self, tmp_path):
        partitions = [Partition(node_id=0, assigned_layers=[0])]
        write_alloy_artifacts(partitions, FirmwareTarget.ESP32, tmp_path)
        topo = tmp_path / "targets" / "alloy" / "topology.json"
        assert topo.exists()


class TestFusionPackageWriter:
    def test_write_artifacts(self, tmp_path):
        board = get_board("xilinx_alveo_u280")
        artifacts = write_fusion_artifacts(board, MacConfig(rows=2, cols=2), tmp_path)
        assert len(artifacts) >= 4
        assert any("tpt_mac_array.v" in v for v in artifacts.values())

    def test_board_json(self, tmp_path):
        board = get_board("xilinx_alveo_u280")
        write_fusion_artifacts(board, MacConfig(rows=2, cols=2), tmp_path)
        board_json = tmp_path / "targets" / "fusion" / "board.json"
        assert board_json.exists()


class TestElementPackageWriter:
    def test_write_artifacts(self, tmp_path):
        weights = np.random.randn(4, 4) * 0.1
        artifacts = write_element_artifacts(weights, tmp_path)
        assert len(artifacts) >= 2
        assert any("netlist.spice" in v for v in artifacts.values())

    def test_confidence_json(self, tmp_path):
        weights = np.random.randn(2, 2) * 0.1
        write_element_artifacts(weights, tmp_path)
        conf = tmp_path / "targets" / "element" / "confidence.json"
        assert conf.exists()
