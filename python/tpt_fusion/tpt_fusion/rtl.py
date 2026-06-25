"""RTL generation from TPT-IR."""

from __future__ import annotations
from pathlib import Path
from tpt_fusion.mac_array import MacArray, MacConfig
from tpt_fusion.board import BoardConfig


class RtlGenerator:
    """Generates synthesizable RTL from TPT-IR."""

    def __init__(self, board: BoardConfig, mac_config: MacConfig | None = None):
        self.board = board
        self.mac_config = mac_config or MacConfig()
        self.mac_array = MacArray(self.mac_config)

    def generate(self, output_dir: Path) -> dict[str, Path]:
        """Generate all RTL files for the board."""
        output_dir.mkdir(parents=True, exist_ok=True)

        files = {}

        mac_verilog = self.mac_array.generate_verilog()
        mac_path = output_dir / "tpt_mac_array.v"
        mac_path.write_text(mac_verilog)
        files["mac_array"] = mac_path

        top_verilog = self._generate_top_level()
        top_path = output_dir / "tpt_top.v"
        top_path.write_text(top_verilog)
        files["top"] = top_path

        constraints = self._generate_constraints()
        constr_path = output_dir / "tpt_constraints.xdc"
        constr_path.write_text(constraints)
        files["constraints"] = constr_path

        init_mem = self._generate_memory_init()
        mem_path = output_dir / "tpt_weights.hex"
        mem_path.write_text(init_mem)
        files["memory_init"] = mem_path

        return files

    def _generate_top_level(self) -> str:
        cfg = self.mac_config
        return f"""\
// Auto-generated TPT Fusion top-level module
// Target: {self.board.name} ({self.board.fpga_part})

module tpt_top (
    input wire clk_100mhz,
    input wire rst_n,
    // HBM interface (if available)
    output wire [{self.board.hbm.data_width - 1 if self.board.hbm else 255}:0] hbm_data_out,
    input wire [{self.board.hbm.data_width - 1 if self.board.hbm else 255}:0] hbm_data_in,
    output wire hbm_valid,
    input wire hbm_ready
);

    wire clk = clk_100mhz;
    wire valid_in = 1'b1;

    tpt_mac_array #(
        .ROWS({cfg.rows}),
        .COLS({cfg.cols}),
        .DATA_WIDTH({cfg.data_width}),
        .WEIGHT_WIDTH({cfg.weight_width}),
        .ACCUM_WIDTH({cfg.accumulator_width})
    ) mac_inst (
        .clk(clk),
        .rst_n(rst_n),
        .valid_in(valid_in),
        .data_in({{{cfg.rows}}}{{{{cfg.data_width{{1'b0}}}}}}),
        .weight_in({{{cfg.cols}}}{{{{cfg.weight_width{{1'b0}}}}}}),
        .valid_out(hbm_valid),
        .result_out()
    );

endmodule
"""

    def _generate_constraints(self) -> str:
        lines = [
            f"# Auto-generated TPT Fusion constraints for {self.board.name}",
            f"# FPGA: {self.board.fpga_part}",
            "",
            "set_property PACKAGE_PIN E3 [get_ports clk_100mhz]",
            "set_property IOSTANDARD LVCMOS33 [get_ports clk_100mhz]",
            "create_clock -period 5.0 -name sys_clk [get_ports clk_100mhz]",
            "",
        ]
        if self.board.hbm:
            lines.extend([
                "# HBM timing constraints",
                "set_false_path -from [get_clocks hbm_clk] -to [get_clocks sys_clk]",
                "",
            ])
        return "\n".join(lines)

    def _generate_memory_init(self) -> str:
        return "// Weight initialization placeholder\n// Run tpt-fusion with --weights <file> to populate\n"
