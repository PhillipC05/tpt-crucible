"""CLI entry point for tpt-silicon."""

import argparse
import json
import sys
from pathlib import Path
import numpy as np

from .weight_packer import CimWeightPacker
from .array_layout import CimArrayLayout, LayoutConfig
from .bitline import BitlineOpGenerator


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tpt-silicon",
        description="TPT Silicon — Compute-in-Memory backend",
    )
    sub = parser.add_subparsers(dest="command")

    compile_cmd = sub.add_parser("compile", help="Compile model for CIM target")
    compile_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")
    compile_cmd.add_argument("--board", default="default", help="CIM board name")
    compile_cmd.add_argument("--precision", type=int, default=8, choices=[4, 8], help="Bit precision")
    compile_cmd.add_argument("-o", "--output", type=Path, default=Path("silicon_output"), help="Output directory")

    info_cmd = sub.add_parser("info", help="Show CIM array info")
    info_cmd.add_argument("--rows", type=int, default=1024)
    info_cmd.add_argument("--cols", type=int, default=1024)
    info_cmd.add_argument("--precision", type=int, default=8)

    args = parser.parse_args()

    if args.command == "compile":
        output_dir = args.output
        output_dir.mkdir(parents=True, exist_ok=True)

        packer = CimWeightPacker(
            array_rows=1024,
            array_cols=1024,
            bit_precision=args.precision,
        )

        layout = CimArrayLayout.from_config(LayoutConfig(
            array_rows=1024,
            array_cols=1024,
            bit_precision=args.precision,
        ))

        generator = BitlineOpGenerator()

        config_data = {
            "board": args.board,
            "precision": args.precision,
            "layout": layout.to_dict(),
        }
        (output_dir / "config.json").write_text(json.dumps(config_data, indent=2))
        print(f"CIM compilation stub written to {output_dir}")
        print(f"  Board: {args.board}")
        print(f"  Precision: {args.precision}-bit")

    elif args.command == "info":
        config = LayoutConfig(
            array_rows=args.rows,
            array_cols=args.cols,
            bit_precision=args.precision,
        )
        print(f"CIM Array: {config.array_rows}x{config.array_cols}")
        print(f"Bit precision: {config.bit_precision}")
        print(f"MAC units: {config.total_mac_units:,}")
        print(f"Memory: {config.memory_bits / 8 / 1024:.1f} KB")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
