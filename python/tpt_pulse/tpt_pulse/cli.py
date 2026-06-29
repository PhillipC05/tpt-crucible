"""CLI entry point for tpt-pulse."""

import argparse
import json
import sys
from pathlib import Path

from .lif_node import SnnGraph
from .converter import SnnConverter
from .sim_export import LifSimulator


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tpt-pulse",
        description="TPT Pulse — Neuromorphic / ANN→SNN compiler",
    )
    sub = parser.add_subparsers(dest="command")

    convert_cmd = sub.add_parser("convert", help="Convert ANN to SNN")
    convert_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")
    convert_cmd.add_argument("--target", default="sim", choices=["loihi", "brainscales", "sim"])
    convert_cmd.add_argument("--layers", type=int, default=4)
    convert_cmd.add_argument("--neurons", type=int, default=32)
    convert_cmd.add_argument("-o", "--output", type=Path, default=Path("pulse_output"))

    sim_cmd = sub.add_parser("simulate", help="Run SNN simulation")
    sim_cmd.add_argument("--layers", type=int, default=4)
    sim_cmd.add_argument("--neurons", type=int, default=32)
    sim_cmd.add_argument("--timesteps", type=int, default=100)

    args = parser.parse_args()

    if args.command == "convert":
        converter = SnnConverter()
        graph = converter.convert(args.layers, args.neurons)

        output_dir = args.output
        output_dir.mkdir(parents=True, exist_ok=True)

        graph.save(output_dir / "snn_graph.json")

        config = {
            "target": args.target,
            "neuron_count": len(graph.neurons),
            "edge_count": len(graph.edges),
        }
        (output_dir / "config.json").write_text(json.dumps(config, indent=2))

        print(f"SNN conversion written to {output_dir}")
        print(f"  Neurons: {len(graph.neurons)}")
        print(f"  Edges: {len(graph.edges)}")
        print(f"  Target: {args.target}")

    elif args.command == "simulate":
        converter = SnnConverter()
        graph = converter.convert(args.layers, args.neurons)
        simulator = LifSimulator()
        result = simulator.simulate(graph, input_spikes=[0, 1, 2], timesteps=args.timesteps)
        print(json.dumps(result.to_dict(), indent=2))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
