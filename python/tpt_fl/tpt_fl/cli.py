"""tpt-fl CLI entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import FederatedConfig, AggregationStrategy, GradientCompression
from .orchestrator import FLOrchestrator


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tpt-fl",
        description="TPT FL — Federated learning orchestration for custom AI hardware",
    )
    sub = parser.add_subparsers(dest="command")

    train_cmd = sub.add_parser("train", help="Run federated learning training")
    train_cmd.add_argument("tptpkg", type=Path, help="Path to .tptpkg directory")
    train_cmd.add_argument(
        "--data-sources", required=True, type=str,
        help="Comma-separated node IPs or hostnames"
    )
    train_cmd.add_argument("--rounds", type=int, default=10, help="Number of FL rounds (default: 10)")
    train_cmd.add_argument(
        "--strategy", choices=["fedavg", "fedprox"], default="fedavg",
        help="Aggregation strategy (default: fedavg)"
    )
    train_cmd.add_argument(
        "--compression", choices=["none", "topk", "quantized"], default="topk",
        help="Gradient compression (default: topk)"
    )
    train_cmd.add_argument("--min-participants", type=int, default=2, help="Minimum responding nodes per round")
    train_cmd.add_argument("--local-epochs", type=int, default=1, help="Local training epochs per round")
    train_cmd.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    train_cmd.add_argument("--batch-size", type=int, default=32, help="Batch size per node")
    train_cmd.add_argument("--recompile-every", type=int, default=5, help="Recompile + OTA every N rounds")
    train_cmd.add_argument("-o", "--output", type=Path, help="Save session report to JSON")

    args = parser.parse_args()

    if args.command == "train":
        sources = [s.strip() for s in args.data_sources.split(",") if s.strip()]
        if not sources:
            print("Error: --data-sources must be a non-empty comma-separated list", file=sys.stderr)
            sys.exit(1)

        config = FederatedConfig(
            tptpkg_path=str(args.tptpkg),
            data_sources=sources,
            strategy=AggregationStrategy(args.strategy),
            rounds=args.rounds,
            min_participants=args.min_participants,
            gradient_compression=GradientCompression(args.compression),
            local_epochs=args.local_epochs,
            learning_rate=args.lr,
            batch_size=args.batch_size,
            recompile_after_rounds=args.recompile_every,
        )

        print(f"Starting federated training:")
        print(f"  Package:    {args.tptpkg}")
        print(f"  Nodes:      {', '.join(sources)}")
        print(f"  Rounds:     {args.rounds}")
        print(f"  Strategy:   {args.strategy}")
        print(f"  Compression:{args.compression}")
        print()

        orchestrator = FLOrchestrator(config)
        session = orchestrator.run()

        print(f"\nFederated training complete:")
        print(f"  Rounds completed: {session.rounds_completed}/{args.rounds}")
        print(f"  Status: {session.status}")

        if args.output:
            args.output.write_text(json.dumps(session.to_dict(), indent=2))
            print(f"  Report saved to {args.output}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
