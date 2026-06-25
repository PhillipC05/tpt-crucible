"""CLI entry point for tpt-catalyst."""

import argparse
import json
import sys
from pathlib import Path
from .ingest import ingest_model
from .optimizer import optimize_graph
from .compat import check_compatibility, HardwareTarget
from .quantize import recommend_quantization, apply_quantization, QUANT_PROFILES, QuantTarget


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tpt-catalyst",
        description="TPT Catalyst — Core IR compiler for AI model ingestion",
    )
    sub = parser.add_subparsers(dest="command")

    ingest_cmd = sub.add_parser("ingest", help="Ingest a model into TPT-IR")
    ingest_cmd.add_argument("model", type=Path, help="Path to model file (.pt/.onnx/.pb/.gguf)")
    ingest_cmd.add_argument("-o", "--output", type=Path, help="Output .tptir file path")
    ingest_cmd.add_argument("--quantize", choices=["auto", "int8", "int4", "float"], help="Apply quantization")
    ingest_cmd.add_argument("--target", choices=["fusion", "alloy", "element"], help="Target hardware for quantization")

    check_cmd = sub.add_parser("check", help="Check model compatibility with hardware target")
    check_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")
    check_cmd.add_argument("--target", required=True, choices=["fusion", "alloy", "element"], help="Target hardware")
    check_cmd.add_argument("-o", "--output", type=Path, help="Save report to JSON file")

    optimize_cmd = sub.add_parser("optimize", help="Apply optimization passes to TPT-IR")
    optimize_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")
    optimize_cmd.add_argument("-o", "--output", type=Path, help="Output .tptir file path")

    args = parser.parse_args()

    if args.command == "ingest":
        ir = ingest_model(args.model)

        if args.quantize:
            target = args.target or "fusion"
            rec = recommend_quantization(ir, target)
            if args.quantize == "auto":
                profile = rec.recommended_profile
            elif args.quantize == "int8":
                profile = QUANT_PROFILES[QuantTarget.FUSION_INT8]
            elif args.quantize == "int4":
                profile = QUANT_PROFILES[QuantTarget.FUSION_INT4]
            else:
                profile = QUANT_PROFILES[QuantTarget.ELEMENT_FLOAT]

            ir = apply_quantization(ir, profile)
            print(f"Applied quantization: {profile.name}")

        out = args.output or args.model.with_suffix(".tptir")
        ir.save(out)
        print(f"TPT-IR written to {out}")

    elif args.command == "check":
        from .ir import TptIr
        ir = TptIr.from_file(args.tptir)
        target_map = {"fusion": HardwareTarget.FUSION, "alloy": HardwareTarget.ALLOY, "element": HardwareTarget.ELEMENT}
        report = check_compatibility(ir, target_map[args.target])
        print(f"Compatibility score: {report.score:.0%}")
        print(f"Passes: {len(report.results) - len(report.warnings) - len(report.failures)}")
        print(f"Warnings: {len(report.warnings)}")
        print(f"Failures: {len(report.failures)}")
        if report.failures:
            print("\nFailed operators:")
            for f in report.failures:
                print(f"  {f.op_type}: {f.message}")
                if f.suggestion:
                    print(f"    Suggestion: {f.suggestion}")
        if args.output:
            args.output.write_text(json.dumps(report.to_dict(), indent=2))
            print(f"\nReport saved to {args.output}")

    elif args.command == "optimize":
        from .ir import TptIr
        ir = TptIr.from_file(args.tptir)
        optimized = optimize_graph(ir)
        out = args.output or args.tptir
        optimized.save(out)
        print(f"Optimized TPT-IR written to {out}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
