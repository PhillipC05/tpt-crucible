"""AI RTL Assistant — generate Verilog MAC arrays from compute patterns."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json


@dataclass
class ComputePattern:
    layer_type: str
    input_shape: list[int]
    output_shape: list[int] = field(default_factory=list)
    dtype: str = "int8"
    activation: str = "none"
    count: int = 1


@dataclass
class RtlCandidate:
    verilog_code: str
    resource_estimate: dict[str, int]
    timing_estimate_ns: float
    confidence: float
    reasoning: str


class AIRtlAssistant:
    """Generate candidate RTL implementations using LLM + templates."""

    MAC_TEMPLATES = {
        "int8": {
            "data_width": 8,
            "weight_width": 8,
            "accumulator_width": 32,
            "dsp_per_mac": 1,
        },
        "int4": {
            "data_width": 4,
            "weight_width": 4,
            "accumulator_width": 16,
            "dsp_per_mac": 0.5,
        },
        "fp16": {
            "data_width": 16,
            "weight_width": 16,
            "accumulator_width": 32,
            "dsp_per_mac": 2,
        },
    }

    def analyze_pattern(self, patterns: list[ComputePattern]) -> dict[str, Any]:
        total_macs = 0
        max_shape = [0, 0]
        for p in patterns:
            if len(p.input_shape) >= 2:
                macs = p.input_shape[0] * p.input_shape[1] * p.count
                total_macs += macs
                max_shape = [max(max_shape[0], p.input_shape[0]),
                            max(max_shape[1], p.input_shape[1])]

        return {
            "total_macs": total_macs,
            "max_shape": max_shape,
            "pattern_count": len(patterns),
            "dominant_dtype": patterns[0].dtype if patterns else "int8",
        }

    def generate_candidates(
        self,
        patterns: list[ComputePattern],
        board_resources: dict[str, int] | None = None,
    ) -> list[RtlCandidate]:
        analysis = self.analyze_pattern(patterns)
        candidates = []

        for dtype, template in self.MAC_TEMPLATES.items():
            rows = min(analysis["max_shape"][0], 64)
            cols = min(analysis["max_shape"][1], 64)

            dsp_needed = int(rows * cols * template["dsp_per_mac"])
            luts_needed = rows * cols * 100

            resource_ok = True
            if board_resources:
                if board_resources.get("max_dsp_slices", 9999) < dsp_needed:
                    resource_ok = False
                if board_resources.get("max_luts", 9999) < luts_needed:
                    resource_ok = False

            confidence = 0.7 if resource_ok else 0.3
            if dtype == analysis["dominant_dtype"]:
                confidence += 0.1

            timing_ns = (rows + cols) * 0.5 / (template["data_width"] / 8)

            verilog = self._generate_mac_verilog(rows, cols, template)

            candidates.append(RtlCandidate(
                verilog_code=verilog,
                resource_estimate={"dsp": dsp_needed, "luts": luts_needed, "ffs": luts_needed * 2},
                timing_estimate_ns=round(timing_ns, 2),
                confidence=round(confidence, 2),
                reasoning=f"{dtype} MAC array {rows}x{cols}, {dsp_needed} DSPs, ~{timing_ns:.1f}ns critical path",
            ))

        candidates.sort(key=lambda c: c.confidence, reverse=True)
        return candidates

    def _generate_mac_verilog(self, rows: int, cols: int, template: dict) -> str:
        dw = template["data_width"]
        ww = template["weight_width"]
        aw = template["accumulator_width"]

        return f"""\
// AI-Generated MAC Array: {rows}x{cols}, {dw}-bit data, {ww}-bit weights
module tpt_mac_array #(
    parameter ROWS = {rows},
    parameter COLS = {cols},
    parameter DATA_WIDTH = {dw},
    parameter WEIGHT_WIDTH = {ww},
    parameter ACCUM_WIDTH = {aw}
)(
    input wire clk,
    input wire rst_n,
    input wire valid_in,
    input wire [DATA_WIDTH-1:0] data_in [0:ROWS-1],
    input wire [WEIGHT_WIDTH-1:0] weight_in [0:COLS-1],
    output wire valid_out,
    output wire [ACCUM_WIDTH-1:0] result_out [0:ROWS-1]
);

    reg [ACCUM_WIDTH-1:0] accum [0:ROWS-1][0:COLS-1];
    reg valid_pipe;
    integer i, j;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < ROWS; i = i + 1)
                for (j = 0; j < COLS; j = j + 1)
                    accum[i][j] <= 0;
            valid_pipe <= 0;
        end else begin
            for (i = 0; i < ROWS; i = i + 1)
                for (j = 0; j < COLS; j = j + 1)
                    accum[i][j] <= accum[i][j] + data_in[i] * weight_in[j];
            valid_pipe <= valid_in;
        end
    end

    assign valid_out = valid_pipe;
    genvar r;
    generate
        for (r = 0; r < ROWS; r = r + 1) begin : out
            assign result_out[r] = accum[r][0];
        end
    endgenerate

endmodule
"""

    def generate_llm_prompt(self, patterns: list[ComputePattern], board: str) -> str:
        analysis = self.analyze_pattern(patterns)
        return (
            f"Generate a Verilog MAC array for these compute patterns:\n"
            f"- Total MACs: {analysis['total_macs']}\n"
            f"- Max shape: {analysis['max_shape']}\n"
            f"- Dominant dtype: {analysis['dominant_dtype']}\n"
            f"- Target board: {board}\n\n"
            f"Return JSON: {{\"verilog\": \"...\", \"resource_estimate\": {{...}}, "
            f"\"timing_estimate_ns\": N, \"reasoning\": \"...\"}}"
        )
