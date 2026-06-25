"""HBM Auto-Router — automatically wire compute arrays to HBM pins."""

from __future__ import annotations
from dataclasses import dataclass, field
from .board import BoardConfig, HbmConfig


@dataclass
class HbmPinMapping:
    """Mapping between MAC array outputs and HBM data pins."""
    mac_row: int
    mac_col: int
    hbm_channel: int
    hbm_byte_lane: int
    signal_name: str


@dataclass
class TimingConstraint:
    """Timing constraint for an HBM connection."""
    source_clock: str
    dest_clock: str
    max_delay_ns: float
    constraint_type: str = "set_max_delay"


@dataclass
class HbmRouteResult:
    """Result of HBM auto-routing."""
    pin_mappings: list[HbmPinMapping]
    timing_constraints: list[TimingConstraint]
    verilog_assignments: str
    constraints_xdc: str


class HbmAutoRouter:
    """Automatically route MAC array I/O to HBM pins.

    Given a board with HBM and a MAC array configuration,
    this router computes optimal pin assignments and timing constraints.
    """

    def __init__(self, board: BoardConfig, mac_rows: int, mac_cols: int):
        self.board = board
        self.mac_rows = mac_rows
        self.mac_cols = mac_cols
        self.hbm = board.hbm
        if not self.hbm:
            raise ValueError(f"Board {board.name} does not have HBM")

    def route(self) -> HbmRouteResult:
        """Perform automatic HBM routing."""
        pin_mappings = self._compute_pin_mappings()
        timing_constraints = self._compute_timing_constraints()
        verilog = self._generate_verilog_assignments(pin_mappings)
        constraints = self._generate_constraints(timing_constraints)

        return HbmRouteResult(
            pin_mappings=pin_mappings,
            timing_constraints=timing_constraints,
            verilog_assignments=verilog,
            constraints_xdc=constraints,
        )

    def _compute_pin_mappings(self) -> list[HbmPinMapping]:
        """Compute pin assignments from MAC array to HBM channels."""
        mappings = []
        channels = self.hbm.channels
        bytes_per_channel = self.hbm.data_width // 8

        for row in range(self.mac_rows):
            for col in range(self.mac_cols):
                channel = (row * self.mac_cols + col) % channels
                byte_lane = ((row * self.mac_cols + col) // channels) % bytes_per_channel
                mappings.append(HbmPinMapping(
                    mac_row=row,
                    mac_col=col,
                    hbm_channel=channel,
                    hbm_byte_lane=byte_lane,
                    signal_name=f"mac_{row}_{col}_to_hbm_ch{channel}",
                ))
        return mappings

    def _compute_timing_constraints(self) -> list[TimingConstraint]:
        """Generate timing constraints for HBM connections."""
        freq_mhz = self.hbm.frequency_mhz
        period_ns = 1000.0 / freq_mhz

        return [
            TimingConstraint(
                source_clock="sys_clk",
                dest_clock="hbm_clk",
                max_delay_ns=period_ns * 0.8,
            ),
            TimingConstraint(
                source_clock="hbm_clk",
                dest_clock="sys_clk",
                max_delay_ns=period_ns * 0.8,
            ),
        ]

    def _generate_verilog_assignments(self, mappings: list[HbmPinMapping]) -> str:
        """Generate Verilog wire assignments for HBM routing."""
        lines = [
            "// Auto-generated HBM pin assignments",
            f"// Board: {self.board.name}",
            f"// MAC array: {self.mac_rows}x{self.mac_cols}",
            "",
        ]
        for m in mappings:
            lines.append(
                f"assign hbm_ch{m.hbm_channel}_byte{m.hbm_byte_lane} = mac_data[{m.mac_row}][{m.mac_col}];"
            )
        return "\n".join(lines)

    def _generate_constraints(self, constraints: list[TimingConstraint]) -> str:
        """Generate XDC timing constraints."""
        lines = [
            "# Auto-generated HBM timing constraints",
            f"# Board: {self.board.name}",
            "",
        ]
        for c in constraints:
            lines.append(
                f"{c.constraint_type} {c.max_delay_ns:.3f} [get_pins -hierarchical -filter {{NAME =~ *hbm*}}]"
            )
        return "\n".join(lines)
