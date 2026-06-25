"""Tests for HBM auto-router and LiteX bridge."""

from pathlib import Path

from tpt_fusion.board import get_board
from tpt_fusion.hbm_router import HbmAutoRouter, HbmPinMapping, TimingConstraint
from tpt_fusion.litex_bridge import LiteXBridge, LiteXConfig


class TestHbmAutoRouter:
    def test_pin_mapping_count(self):
        board = get_board("xilinx_alveo_u280")
        router = HbmAutoRouter(board, mac_rows=4, mac_cols=4)
        result = router.route()
        assert len(result.pin_mappings) == 16

    def test_timing_constraints_generated(self):
        board = get_board("xilinx_alveo_u280")
        router = HbmAutoRouter(board, mac_rows=2, mac_cols=2)
        result = router.route()
        assert len(result.timing_constraints) >= 2

    def test_verilog_assignments(self):
        board = get_board("xilinx_alveo_u280")
        router = HbmAutoRouter(board, mac_rows=2, mac_cols=2)
        result = router.route()
        assert "assign hbm_ch" in result.verilog_assignments

    def test_constraints_xdc(self):
        board = get_board("xilinx_alveo_u280")
        router = HbmAutoRouter(board, mac_rows=2, mac_cols=2)
        result = router.route()
        assert "set_max_delay" in result.constraints_xdc

    def test_no_hbm_board_raises(self):
        board = get_board("lattice_ice40")
        try:
            HbmAutoRouter(board, mac_rows=2, mac_cols=2)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


class TestLiteXBridge:
    def test_generate_soc(self, tmp_path):
        bridge = LiteXBridge(LiteXConfig(cpu_type="vexriscv"))
        soc_path = bridge.generate_soC(tmp_path)
        assert soc_path.exists()
        content = soc_path.read_text()
        assert "TptSoC" in content
        assert "vexriscv" in content

    def test_generate_build_script(self, tmp_path):
        bridge = LiteXBridge()
        script_path = bridge.generate_build_script(tmp_path)
        assert script_path.exists()
        content = script_path.read_text()
        assert "set -euo pipefail" in content
