"""CLI entry point for tpt-fusion."""

import argparse
import json
import sys
from pathlib import Path
from .mac_array import MacConfig
from .board import get_board, list_boards
from .rtl import RtlGenerator
from .toolchain import YosysRunner, NextpnrRunner


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tpt-fusion",
        description="TPT Fusion — FPGA synthesis and HBM auto-routing",
    )
    sub = parser.add_subparsers(dest="command")

    gen_cmd = sub.add_parser("generate", help="Generate RTL from MAC array config")
    gen_cmd.add_argument("--board", default="xilinx_alveo_u280", help="Target FPGA board")
    gen_cmd.add_argument("--rows", type=int, default=16, help="MAC array rows")
    gen_cmd.add_argument("--cols", type=int, default=16, help="MAC array columns")
    gen_cmd.add_argument("-o", "--output", type=Path, default=Path("rtl"), help="Output directory")

    boards_cmd = sub.add_parser("boards", help="List available FPGA boards")

    syn_cmd = sub.add_parser("synthesize", help="Run Yosys + Nextpnr synthesis")
    syn_cmd.add_argument("--rtl-dir", type=Path, required=True, help="Directory with RTL files")
    syn_cmd.add_argument("--board", default="xilinx_alveo_u280")
    syn_cmd.add_argument("-o", "--output", type=Path, default=Path("bitstream"), help="Output directory")

    args = parser.parse_args()

    if args.command == "generate":
        board = get_board(args.board)
        config = MacConfig(rows=args.rows, cols=args.cols)
        gen = RtlGenerator(board, config)
        files = gen.generate(args.output)
        for name, path in files.items():
            print(f"Generated {name}: {path}")

    elif args.command == "boards":
        for name in list_boards():
            board = get_board(name)
            has_hbm = "HBM" if board.hbm else "No HBM"
            print(f"  {name}: {board.fpga_part} ({has_hbm})")

    elif args.command == "synthesize":
        board = get_board(args.board)
        yosys = YosysRunner()
        nextpnr = NextpnrRunner()

        if not yosys.check_available():
            print("Warning: Yosys not found. Install it for synthesis.")
        if not nextpnr.check_available():
            print("Warning: Nextpnr not found. Install it for place-and-route.")

        print(f"Synthesis pipeline ready for {board.name}")
        print(f"RTL directory: {args.rtl_dir}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
