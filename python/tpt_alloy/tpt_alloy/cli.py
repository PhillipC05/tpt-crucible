"""CLI entry point for tpt-alloy."""

import argparse
import json
import sys
from pathlib import Path
from .topology import Topology
from .partition import PartitionConfig, partition_model
from .firmware import FirmwareTarget, generate_firmware
from .platformio import generate_flash_script


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tpt-alloy",
        description="TPT Alloy — Swarm partitioning and firmware generation",
    )
    sub = parser.add_subparsers(dest="command")

    part_cmd = sub.add_parser("partition", help="Partition a model for swarm deployment")
    part_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")
    part_cmd.add_argument("--topology", default="grid2d", choices=["grid2d", "star", "ring"])
    part_cmd.add_argument("--nodes", type=int, default=16, help="Number of swarm nodes")

    flash_cmd = sub.add_parser("flash", help="Generate firmware for all nodes")
    flash_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")
    flash_cmd.add_argument("--target", default="esp32", choices=["esp32", "rp2040", "riscv"])
    flash_cmd.add_argument("--nodes", type=int, default=16)
    flash_cmd.add_argument("-o", "--output", type=Path, default=Path("firmware"), help="Output directory")
    flash_cmd.add_argument("--flash-script", action="store_true", help="Generate master flash script")

    args = parser.parse_args()

    if args.command == "partition":
        rows = cols = int(args.nodes**0.5) or 1
        config = PartitionConfig(topology=Topology.grid2d(rows, cols))
        partitions = partition_model(100, config)
        print(json.dumps([{"node_id": p.node_id, "layers": p.assigned_layers} for p in partitions], indent=2))
    elif args.command == "flash":
        rows = cols = int(args.nodes**0.5) or 1
        config = PartitionConfig(topology=Topology.grid2d(rows, cols))
        partitions = partition_model(100, config)
        target = FirmwareTarget(args.target)
        args.output.mkdir(parents=True, exist_ok=True)

        bundles = []
        for p in partitions:
            bundle = generate_firmware(p, target)
            bundles.append(bundle)
            fw_path = args.output / f"node_{bundle.node_id}.c"
            fw_path.write_text(bundle.source_code)
            cfg_path = args.output / f"node_{bundle.node_id}.json"
            cfg_path.write_text(bundle.config_json)
            print(f"Generated firmware: {fw_path}")

        if args.flash_script:
            script_path = args.output / "flash_all.sh"
            generate_flash_script(bundles, script_path)
            print(f"Generated flash script: {script_path}")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
