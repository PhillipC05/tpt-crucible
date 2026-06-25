"""CLI entrypoint: python -m tpt_validator validate model.tptpkg --reference pytorch"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(prog="tpt-validator",
                                     description="TPT Compliance Validator")
    sub = parser.add_subparsers(dest="command")

    val = sub.add_parser("validate", help="Validate a compiled .tptpkg")
    val.add_argument("package", type=Path, help="Path to .tptpkg file")
    val.add_argument("--reference", choices=["pytorch", "spark"], default="pytorch",
                     help="Reference backend (default: pytorch)")
    val.add_argument("--prompt-suite", type=Path, default=None,
                     help="Custom prompt suite JSON (default: bundled suite)")
    val.add_argument("--output", type=Path, default=None,
                     help="Write report JSON to file (default: stdout)")
    val.add_argument("--no-sign", action="store_true",
                     help="Skip signing the report")

    args = parser.parse_args()

    if args.command == "validate":
        from .validator import run_validation
        print(f"[tpt-validator] validating {args.package} (reference: {args.reference})")
        report = run_validation(
            tptpkg_path=args.package,
            reference_backend=args.reference,
            prompt_suite_path=args.prompt_suite,
            sign=not args.no_sign,
        )
        result = report.to_dict()
        out = json.dumps(result, indent=2)

        if args.output:
            args.output.write_text(out)
            print(f"[tpt-validator] report written to {args.output}")
        else:
            print(out)

        print(f"\n[tpt-validator] overall: {report.overall.upper()} "
              f"(token match: {report.token_match_rate:.1%}, "
              f"perplexity delta: {report.perplexity_delta:.3f})")
        return 0 if report.overall == "pass" else 1
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
