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
    ingest_cmd.add_argument("model", nargs="?", type=Path, help="Path to model file (.pt/.onnx/.pb/.gguf)")
    ingest_cmd.add_argument("-o", "--output", type=Path, help="Output .tptir file path")
    ingest_cmd.add_argument("--quantize", choices=["auto", "int8", "int4", "float"], help="Apply quantization")
    ingest_cmd.add_argument("--target", choices=["fusion", "alloy", "element"], help="Target hardware for quantization")
    ingest_cmd.add_argument("--spark-model", type=str, help="Spark model ID to ingest")
    ingest_cmd.add_argument("--profile", type=Path, help="Path to .tptprofile for quantization clamps")

    pack_cmd = sub.add_parser("pack", help="Pack TPT-IR into .tptpkg")
    pack_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")
    pack_cmd.add_argument("--targets", type=str, default="alloy", help="Comma-separated target list")
    pack_cmd.add_argument("-o", "--output", type=Path, help="Output .tptpkg path")
    pack_cmd.add_argument("--incremental", action="store_true", help="Skip operators already in cache")

    check_cmd = sub.add_parser("check", help="Check model compatibility with hardware target")
    check_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")
    check_cmd.add_argument("--target", required=True, choices=["fusion", "alloy", "element"], help="Target hardware")
    check_cmd.add_argument("-o", "--output", type=Path, help="Save report to JSON file")

    optimize_cmd = sub.add_parser("optimize", help="Apply optimization passes to TPT-IR")
    optimize_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")
    optimize_cmd.add_argument("-o", "--output", type=Path, help="Output .tptir file path")

    doctor_cmd = sub.add_parser("doctor", help="Check toolchain readiness")
    doctor_cmd.add_argument("--target", choices=["fusion", "alloy", "element", "observer"], help="Check specific target")

    info_cmd = sub.add_parser("info", help="Show TPT-IR file information")
    info_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")

    args = parser.parse_args()

    if args.command == "ingest":
        if args.spark_model:
            from .spark_integration import SparkDetector
            detector = SparkDetector()
            spark_model = detector.get_model(args.spark_model)
            if spark_model:
                model_path = spark_model.path
                print(f"Found Spark model: {spark_model.name} at {model_path}")
            else:
                print(f"Spark model '{args.spark_model}' not found")
                sys.exit(1)
        elif args.model:
            model_path = args.model
        else:
            print("Error: specify a model path or --spark-model")
            sys.exit(1)

        ir = ingest_model(model_path)

        if args.profile and args.profile.exists():
            from .tpt_profile import TptProfile
            tpt_profile = TptProfile.from_file(args.profile)
            print(f"Loaded profile: {tpt_profile.model_name} ({len(tpt_profile.layers)} layers)")
            for layer in tpt_profile.layers:
                for node in ir.graph.nodes:
                    if node.name == layer.name:
                        node.attributes["profile_bits"] = layer.recommended_bits

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

        out = args.output or model_path.with_suffix(".tptir")
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

    elif args.command == "pack":
        from .ir import TptIr
        from .cache import CompilationCache
        from .package_reports import write_preflight_report, write_quant_profile
        from .compat import check_compatibility, HardwareTarget
        from .quantize import QUANT_PROFILES, QuantTarget
        from pathlib import Path as P
        import hashlib, json

        ir = TptIr.from_file(args.tptir)
        targets = [t.strip() for t in args.targets.split(",")]
        out = args.output or P(f"{ir.metadata.name}.tptpkg")
        out.mkdir(parents=True, exist_ok=True)

        if args.incremental:
            cache = CompilationCache(out / ".tpt-cache")
            uncached = cache.filter_uncached(ir)
            print(f"Cache: {len(ir.graph.nodes) - len(uncached)} hit, {len(uncached)} miss")
        else:
            cache = CompilationCache(out / ".tpt-cache")
            for node in ir.graph.nodes:
                cache.store(node)

        source_hash = hashlib.sha256(json.dumps(ir.to_json()).encode()).hexdigest()[:16]
        manifest = {
            "format_version": "1.0.0",
            "model_name": ir.metadata.name,
            "source_sha256": source_hash,
            "targets": targets,
        }
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
        (out / "ir").mkdir(exist_ok=True)
        ir.save(out / "ir" / "model.tptir")

        for target in targets:
            hw_target = {"alloy": HardwareTarget.ALLOY, "fusion": HardwareTarget.FUSION, "element": HardwareTarget.ELEMENT}.get(target)
            if hw_target:
                report = check_compatibility(ir, hw_target)
                write_preflight_report(report, out)
                rec = recommend_quantization(ir, target)
                write_quant_profile(rec.recommended_profile, out)

        print(f"Package written to {out}")
        print(f"  Targets: {', '.join(targets)}")
        print(f"  Source SHA-256: {source_hash}")

    elif args.command == "doctor":
        from .doctor import run_doctor, print_report
        report = run_doctor(target=args.target)
        print_report(report)

    elif args.command == "info":
        from .ir import TptIr
        ir = TptIr.from_file(args.tptir)
        print(f"Model: {ir.metadata.name}")
        print(f"Source: {ir.metadata.source_format}")
        print(f"Parameters: {ir.metadata.parameter_count:,}")
        print(f"Operators: {len(ir.graph.nodes)}")
        print(f"Edges: {len(ir.graph.edges)}")
        op_types = {}
        for node in ir.graph.nodes:
            op_types[node.op_type] = op_types.get(node.op_type, 0) + 1
        print("\nOperator breakdown:")
        for op, count in sorted(op_types.items(), key=lambda x: -x[1]):
            print(f"  {op}: {count}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
