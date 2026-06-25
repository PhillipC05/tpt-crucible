"""CLI entry point for tpt-train."""

import argparse
import json
import sys
from pathlib import Path
from .profile import TptProfile


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tpt-train",
        description="TPT Train — Training hooks for quantization-aware profiles",
    )
    sub = parser.add_subparsers(dest="command")

    inspect_cmd = sub.add_parser("inspect", help="Inspect a .tptprofile file")
    inspect_cmd.add_argument("profile", type=Path, help="Path to .tptprofile file")

    args = parser.parse_args()

    if args.command == "inspect":
        profile = TptProfile.from_file(args.profile)
        print(f"Model: {profile.model_name}")
        print(f"Epoch: {profile.epoch}")
        print(f"Layers: {len(profile.layers)}")
        for layer in profile.layers:
            bits = layer.recommended_bits
            print(f"  {layer.name} ({layer.layer_type}): {bits}-bit recommended, "
                  f"input=[{layer.input_min:.4f}, {layer.input_max:.4f}]")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
