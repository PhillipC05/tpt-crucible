"""CLI entry point for tpt-emulate."""

import argparse
import json
import sys
from pathlib import Path
from .alloy_sil import AlloySil
from .fusion_sil import FusionSil
from .element_sil import ElementSil


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tpt-emulate",
        description="TPT Emulator — Software-in-the-Loop simulation",
    )
    parser.add_argument("model", type=Path, help="Path to compiled model or TPT-IR")
    parser.add_argument("--hardware", required=True, choices=["alloy", "fusion", "element"])
    parser.add_argument("--nodes", type=int, default=16, help="Swarm node count (alloy only)")
    parser.add_argument("--clock-mhz", type=int, default=200, help="FPGA clock (fusion only)")
    parser.add_argument("-o", "--output", type=Path, help="Save telemetry to file")

    args = parser.parse_args()

    if args.hardware == "alloy":
        emu = AlloySil(node_count=args.nodes)
    elif args.hardware == "fusion":
        emu = FusionSil(clock_mhz=args.clock_mhz)
    else:
        emu = ElementSil()

    if emu.load_model(str(args.model)):
        result = emu.run_inference(None)
        print(json.dumps(result.to_dict(), indent=2))
        if args.output:
            args.output.write_text(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"Failed to load model: {args.model}")
        sys.exit(1)


if __name__ == "__main__":
    main()
