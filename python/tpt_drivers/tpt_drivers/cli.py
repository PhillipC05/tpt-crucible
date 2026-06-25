"""CLI entry point for tpt-drivers."""

import argparse
import json
import sys
from pathlib import Path
from .driver import DriverManifest
from .registry import DriverRegistry


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tpt-drivers",
        description="TPT Drivers — Hardware driver SDK and community registry",
    )
    sub = parser.add_subparsers(dest="command")

    list_cmd = sub.add_parser("list", help="List installed drivers")

    search_cmd = sub.add_parser("search", help="Search for drivers")
    search_cmd.add_argument("query", help="Search query")

    install_cmd = sub.add_parser("install", help="Install a driver from manifest file")
    install_cmd.add_argument("manifest", type=Path, help="Path to driver.toml")

    info_cmd = sub.add_parser("info", help="Show driver details")
    info_cmd.add_argument("name", help="Driver name")

    args = parser.parse_args()
    registry = DriverRegistry()

    if args.command == "list":
        drivers = registry.list_drivers()
        if not drivers:
            print("No drivers installed.")
        for d in drivers:
            print(f"  {d.name} v{d.version} ({d.hardware_type}) — {d.description}")

    elif args.command == "search":
        results = registry.search(args.query)
        if not results:
            print(f"No drivers found for '{args.query}'")
        for d in results:
            print(f"  {d.name} v{d.version} ({d.hardware_type}) — {d.description}")

    elif args.command == "install":
        manifest = DriverManifest.from_dict(json.loads(args.manifest.read_text()))
        path = registry.install_driver(manifest)
        print(f"Installed {manifest.name} v{manifest.version} to {path}")

    elif args.command == "info":
        manifest = registry.get_driver(args.name)
        if manifest:
            print(json.dumps(manifest.to_dict(), indent=2))
        else:
            print(f"Driver '{args.name}' not found")
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
