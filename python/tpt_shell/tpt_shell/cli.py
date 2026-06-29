"""tpt-shell CLI entry point."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from .session import ShellSession
from .repl import run_repl


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tpt-shell",
        description="TPT Shell — Interactive hardware REPL for TPT Crucible deployments",
    )
    parser.add_argument("tptpkg", type=Path, help="Path to .tptpkg directory")
    parser.add_argument(
        "--hardware",
        choices=["alloy", "fusion", "element", "sil"],
        default="sil",
        help="Hardware backend to connect to (default: sil)",
    )
    parser.add_argument(
        "--node",
        type=str,
        default=None,
        help="Node IP or hostname for direct hardware connection (optional)",
    )
    parser.add_argument(
        "--ws-url",
        type=str,
        default=None,
        help="Override WebSocket URL (default: derived from --hardware and --node)",
    )
    parser.add_argument(
        "--layer",
        type=str,
        default=None,
        help="Pre-select a layer ID (non-interactive single-layer mode)",
    )
    args = parser.parse_args()

    if not args.tptpkg.exists():
        print(f"Error: {args.tptpkg} does not exist", file=sys.stderr)
        sys.exit(1)

    if args.ws_url:
        ws_url = args.ws_url
    elif args.node:
        ws_url = f"ws://{args.node}:8080/ws/shell"
    else:
        ws_url = "ws://localhost:8080/ws/shell"

    print(f"Connecting to {ws_url} ({args.hardware})...")

    async def _main() -> None:
        session = ShellSession(ws_url, args.tptpkg)
        try:
            await session.connect()
        except Exception as e:
            print(f"Warning: could not connect to hardware ({e}). Running in offline mode.")

        if args.layer:
            try:
                tensor = await session.run_layer(args.layer)
                print(tensor.pretty())
            except Exception as e:
                print(f"Error running layer {args.layer}: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            await run_repl(session)
        await session.disconnect()

    asyncio.run(_main())


if __name__ == "__main__":
    main()
