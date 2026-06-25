"""CLI entry point for tpt-mosaic."""

import argparse
import json
import sys
from pathlib import Path
from .partition import PartitionPlan, auto_assign_layers, HardwareTarget
from .orchestrator import MosaicOrchestrator


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tpt-mosaic",
        description="TPT Mosaic — Hybrid cross-hardware deployment orchestrator",
    )
    sub = parser.add_subparsers(dest="command")

    plan_cmd = sub.add_parser("plan", help="Generate a partition plan")
    plan_cmd.add_argument("--layers", type=int, default=12, help="Number of layers")
    plan_cmd.add_argument("-o", "--output", type=Path, help="Save plan to file")

    compile_cmd = sub.add_parser("compile", help="Compile across multiple hardware targets")
    compile_cmd.add_argument("plan", type=Path, help="Path to partition plan JSON")
    compile_cmd.add_argument("-o", "--output", type=Path, default=Path("build"), help="Output directory")

    args = parser.parse_args()

    if args.command == "plan":
        plan = auto_assign_layers(args.layers)
        if args.output:
            plan.save(args.output)
            print(f"Partition plan saved to {args.output}")
        print(json.dumps(plan.to_dict(), indent=2))

    elif args.command == "compile":
        plan_data = json.loads(args.plan.read_text())
        plan = PartitionPlan.from_dict(plan_data)
        orchestrator = MosaicOrchestrator(args.output)
        result = orchestrator.compile(plan)
        if result.success:
            print(f"Compilation successful. Targets: {', '.join(result.targets_compiled)}")
            for bf in result.bridge_files:
                print(f"  Bridge: {bf}")
        else:
            print("Compilation failed:")
            for err in result.errors:
                print(f"  {err}")
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
