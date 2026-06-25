"""MAC (Multiply-Accumulate) array hardware generation."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class MacConfig:
    """Configuration for a MAC array block."""
    rows: int = 16
    cols: int = 16
    data_width: int = 16
    weight_width: int = 8
    accumulator_width: int = 32
    pipeline_stages: int = 3
    use_dsp: bool = True


class MacArray:
    """Generates Amaranth HDL for a MAC array.

    The MAC array is the core compute unit for FPGA-based inference.
    It performs matrix multiplication using systolic array architecture.
    """

    def __init__(self, config: MacConfig | None = None):
        self.config = config or MacConfig()

    def generate_verilog(self) -> str:
        """Generate synthesizable Verilog for the MAC array."""
        cfg = self.config
        return f"""\
// Auto-generated TPT Fusion MAC Array
// Configuration: {cfg.rows}x{cfg.cols}, {cfg.data_width}-bit data, {cfg.weight_width}-bit weights
// Pipeline stages: {cfg.pipeline_stages}

module tpt_mac_array #(
    parameter ROWS = {cfg.rows},
    parameter COLS = {cfg.cols},
    parameter DATA_WIDTH = {cfg.data_width},
    parameter WEIGHT_WIDTH = {cfg.weight_width},
    parameter ACCUM_WIDTH = {cfg.accumulator_width}
)(
    input wire clk,
    input wire rst_n,
    input wire valid_in,
    input wire [DATA_WIDTH-1:0] data_in [0:ROWS-1],
    input wire [WEIGHT_WIDTH-1:0] weight_in [0:COLS-1],
    output wire valid_out,
    output wire [ACCUM_WIDTH-1:0] result_out [0:ROWS-1]
);

    // Pipeline registers
    reg [ACCUM_WIDTH-1:0] accum [0:ROWS-1][0:COLS-1];
    reg valid_pipe [0:{cfg.pipeline_stages - 1}];

    integer i, j;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < ROWS; i = i + 1)
                for (j = 0; j < COLS; j = j + 1)
                    accum[i][j] <= 0;
            for (i = 0; i < {cfg.pipeline_stages}; i = i + 1)
                valid_pipe[i] <= 0;
        end else begin
            for (i = 0; i < ROWS; i = i + 1)
                for (j = 0; j < COLS; j = j + 1)
                    accum[i][j] <= accum[i][j] + data_in[i] * weight_in[j];
            valid_pipe[0] <= valid_in;
            for (i = 1; i < {cfg.pipeline_stages}; i = i + 1)
                valid_pipe[i] <= valid_pipe[i-1];
        end
    end

    assign valid_out = valid_pipe[{cfg.pipeline_stages - 1}];
    genvar r;
    generate
        for (r = 0; r < ROWS; r = r + 1) begin : output_mux
            assign result_out[r] = accum[r][0];
        end
    endgenerate

endmodule
"""

    def get_resource_estimate(self) -> dict[str, Any]:
        """Estimate FPGA resource usage."""
        cfg = self.config
        dsp_count = cfg.rows * cfg.cols if cfg.use_dsp else 0
        lut_count = cfg.rows * cfg.cols * 4
        ff_count = cfg.rows * cfg.cols * cfg.accumulator_width

        return {
            "dsp_slices": dsp_count,
            "lut_count": lut_count,
            "ff_count": ff_count,
            "bram_kbits": (cfg.rows * cfg.cols * cfg.data_width) // 1024,
            "clock_mhz": 200 if cfg.use_dsp else 100,
        }
