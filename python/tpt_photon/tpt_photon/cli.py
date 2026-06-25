"""CLI entry point for tpt-photon."""

import argparse
import json
import sys
from pathlib import Path

from .mzi_mesh import MziMeshGenerator, MziConfig


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tpt-photon",
        description="TPT Photon — Photonic compute backend (EXPERIMENTAL)",
    )

    print("=" * 60)
    print("  WARNING: TPT Photon is EXPERIMENTAL")
    print("  Silicon photonic inference is not yet production-ready")
    print("=" * 60)

    sub = parser.add_subparsers(dest="command")

    compile_cmd = sub.add_parser("compile", help="Compile model for photonic target")
    compile_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")
    compile_cmd.add_argument("--mesh-size", type=int, default=8, help="MZI mesh size")
    compile_cmd.add_argument("--wavelength", type=int, default=1550, help="Wavelength in nm")
    compile_cmd.add_argument("-o", "--output", type=Path, default=Path("photon_output"), help="Output directory")

    args = parser.parse_args()

    if args.command == "compile":
        config = MziConfig(mesh_size=args.mesh_size, wavelength_nm=args.wavelength)
        generator = MziMeshGenerator(config)

        output_dir = args.output
        output_dir.mkdir(parents=True, exist_ok=True)

        phase_config = {
            "config": config.to_dict(),
            "status": "EXPERIMENTAL",
            "message": "Photonic inference requires physical MZI mesh hardware",
        }
        (output_dir / "phase_config.json").write_text(json.dumps(phase_config, indent=2))
        print(f"Photonic compilation stub written to {output_dir}")
        print(f"  Mesh size: {args.mesh_size}x{args.mesh_size}")
        print(f"  Wavelength: {args.wavelength}nm")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
