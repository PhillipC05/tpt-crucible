"""Tests for TPT Fusion module."""

from pathlib import Path

from tpt_fusion.mac_array import MacArray, MacConfig
from tpt_fusion.board import get_board, list_boards, BoardConfig, BOARD_LIBRARY
from tpt_fusion.rtl import RtlGenerator
from tpt_fusion.toolchain import YosysRunner, NextpnrRunner


class TestMacArray:
    def test_verilog_generation(self):
        mac = MacArray(MacConfig(rows=4, cols=4))
        verilog = mac.generate_verilog()
        assert "module tpt_mac_array" in verilog
        assert "ROWS = 4" in verilog
        assert "COLS = 4" in verilog

    def test_resource_estimate(self):
        mac = MacArray(MacConfig(rows=8, cols=8, use_dsp=True))
        est = mac.get_resource_estimate()
        assert est["dsp_slices"] == 64
        assert est["lut_count"] > 0

    def test_no_dsp_estimate(self):
        mac = MacArray(MacConfig(rows=4, cols=4, use_dsp=False))
        est = mac.get_resource_estimate()
        assert est["dsp_slices"] == 0


class TestBoard:
    def test_list_boards(self):
        boards = list_boards()
        assert "xilinx_alveo_u280" in boards
        assert len(boards) >= 3

    def test_get_board(self):
        board = get_board("xilinx_alveo_u280")
        assert board.name == "Xilinx Alveo U280"
        assert board.hbm is not None
        assert board.hbm.capacity_gb == 4

    def test_unknown_board_raises(self):
        try:
            get_board("nonexistent_board")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


class TestRtlGenerator:
    def test_generate_all_files(self, tmp_path):
        board = get_board("xilinx_alveo_u280")
        gen = RtlGenerator(board, MacConfig(rows=4, cols=4))
        files = gen.generate(tmp_path)
        assert "mac_array" in files
        assert "top" in files
        assert "constraints" in files
        assert files["mac_array"].exists()
        assert files["top"].exists()

    def test_verilog_content(self, tmp_path):
        board = get_board("xilinx_alveo_u280")
        gen = RtlGenerator(board, MacConfig(rows=2, cols=2))
        files = gen.generate(tmp_path)
        content = files["top"].read_text()
        assert "tpt_top" in content
        assert "tpt_mac_array" in content


class TestToolchain:
    def test_yosys_not_available(self):
        runner = YosysRunner("nonexistent_yosys")
        assert runner.check_available() is False

    def test_nextpnr_not_available(self):
        runner = NextpnrRunner("nonexistent_nextpnr")
        assert runner.check_available() is False
