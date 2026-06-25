"""CLI entry point for tpt-element."""

import argparse
import sys
import numpy as np
from pathlib import Path
from .weight_map import WeightMapper
from .spice import SpiceNetlistGenerator


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tpt-element",
        description="TPT Element — Analog compute weight mapping and drift simulation",
    )
    sub = parser.add_subparsers(dest="command")

    sim_cmd = sub.add_parser("simulate", help="Map weights and generate SPICE netlist")
    sim_cmd.add_argument("--weights", type=Path, help="Path to weights .npy file")
    sim_cmd.add_argument("--tolerance", type=float, default=0.05)
    sim_cmd.add_argument("-o", "--output", type=Path, default=Path("circuit.spice"))

    args = parser.parse_args()

    if args.command == "simulate":
        if args.weights and args.weights.exists():
            weights = np.load(args.weights)
        else:
            weights = np.random.randn(4, 4) * 0.1

        mapper = WeightMapper(tolerance=args.tolerance)
        components = mapper.map_weights(weights)
        confidence = mapper.compute_confidence_score(components)

        gen = SpiceNetlistGenerator()
        for c in components:
            gen.add_component(c)
        gen.save_netlist(args.output)

        print(f"Generated {len(components)} components")
        print(f"Confidence score: {confidence:.2%}")
        print(f"Netlist written to {args.output}")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
