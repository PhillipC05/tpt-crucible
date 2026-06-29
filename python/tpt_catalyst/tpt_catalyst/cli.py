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
    ingest_cmd.add_argument("--quantize", choices=["auto", "int8", "int4", "float", "mixed-precision"], help="Apply quantization")
    ingest_cmd.add_argument("--accuracy-budget", type=float, default=0.05, help="Accuracy loss budget for mixed-precision search (default: 0.05)")
    ingest_cmd.add_argument("--target", choices=["fusion", "alloy", "element"], help="Target hardware for quantization")
    ingest_cmd.add_argument("--spark-model", type=str, help="Spark model ID to ingest")
    ingest_cmd.add_argument("--profile", type=Path, help="Path to .tptprofile for quantization clamps")
    ingest_cmd.add_argument("--optimize-carbon", action="store_true", help="Include carbon cost analysis")
    ingest_cmd.add_argument("--carbon-region", default="global_avg", help="Region for carbon intensity lookup")
    ingest_cmd.add_argument("--sparsity", choices=["auto", "2:4", "4:8", "none"], help="Structured sparsity mode")
    ingest_cmd.add_argument("--intermittent", action="store_true", help="Enable checkpoint ops for energy-harvesting devices")
    ingest_cmd.add_argument("--checkpoint-granularity", choices=["layer", "block", "operator"], default="layer", help="Checkpoint insertion granularity")
    ingest_cmd.add_argument("--energy-budget-mj", type=float, help="Energy budget in mJ for intermittent mode")

    pack_cmd = sub.add_parser("pack", help="Pack TPT-IR into .tptpkg")
    pack_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")
    pack_cmd.add_argument("--targets", type=str, default="alloy", help="Comma-separated target list")
    pack_cmd.add_argument("-o", "--output", type=Path, help="Output .tptpkg path")
    pack_cmd.add_argument("--incremental", action="store_true", help="Skip operators already in cache")
    pack_cmd.add_argument("--lock-to-hardware", type=str, help="Lock package to specific hardware IDs")
    pack_cmd.add_argument("--no-regression-check", action="store_true", help="Skip accuracy regression check (for CI)")
    pack_cmd.add_argument("--community-cache", action="store_true", help="Use community compilation cache")
    pack_cmd.add_argument("--no-community-cache", action="store_true", help="Disable community compilation cache")

    unpack_cmd = sub.add_parser("unpack", help="Inspect/extract .tptpkg contents")
    unpack_cmd.add_argument("tptpkg", type=Path, help="Path to .tptpkg directory")
    unpack_cmd.add_argument("-o", "--output", type=Path, help="Extract contents to directory")
    unpack_cmd.add_argument("--json", action="store_true", help="Output manifest as JSON")

    check_cmd = sub.add_parser("check", help="Check model compatibility with hardware target")
    check_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")
    check_cmd.add_argument("--target", required=True, choices=["fusion", "alloy", "element", "cim", "neuromorphic", "photonic"], help="Target hardware")
    check_cmd.add_argument("-o", "--output", type=Path, help="Save report to JSON file")
    check_cmd.add_argument("--optimize-carbon", action="store_true", help="Include carbon cost analysis")
    check_cmd.add_argument("--carbon-region", default="global_avg", help="Region for carbon intensity lookup")

    validate_cmd = sub.add_parser("validate", help="Validate model accuracy against reference")
    validate_cmd.add_argument("tptpkg", type=Path, help="Path to .tptpkg directory")
    validate_cmd.add_argument("--reference", default="spark", help="Reference backend")
    validate_cmd.add_argument("--hardware", default="alloy", help="Target hardware")
    validate_cmd.add_argument("-o", "--output", type=Path, help="Save results to JSON")

    optimize_cmd = sub.add_parser("optimize", help="Apply optimization passes to TPT-IR")
    optimize_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")
    optimize_cmd.add_argument("-o", "--output", type=Path, help="Output .tptir file path")

    doctor_cmd = sub.add_parser("doctor", help="Check toolchain readiness")
    doctor_cmd.add_argument("--target", choices=["fusion", "alloy", "element", "observer"], help="Check specific target")

    info_cmd = sub.add_parser("info", help="Show TPT-IR file information")
    info_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")

    diagnose_cmd = sub.add_parser("diagnose", help="Run hardware diagnostics")
    diagnose_cmd.add_argument("tptpkg", type=Path, help="Path to .tptpkg directory")
    diagnose_cmd.add_argument("--hardware", default="alloy", choices=["alloy", "fusion", "element"], help="Hardware to diagnose")
    diagnose_cmd.add_argument("-o", "--output", type=Path, help="Save results to JSON")

    provenance_cmd = sub.add_parser("provenance", help="Show compilation lineage for a .tptpkg")
    provenance_cmd.add_argument("tptpkg", type=Path, help="Path to .tptpkg directory")
    provenance_cmd.add_argument("--diff", type=Path, metavar="OTHER_TPTPKG", help="Diff lineage against another package")
    provenance_cmd.add_argument("--json", action="store_true", help="Output as JSON")

    smoke_cmd = sub.add_parser("smoke-test", help="Run end-to-end smoke test")
    smoke_cmd.add_argument("--target", default="all", choices=["alloy", "fusion", "element", "all"], help="Hardware target to test")

    tournament_cmd = sub.add_parser("tournament", help="Sweep optimization space and build Pareto frontier")
    tournament_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")
    tournament_cmd.add_argument("--targets", type=str, default="alloy,fusion,element", help="Comma-separated targets")
    tournament_cmd.add_argument("--max-latency", type=float, metavar="MS", help="Max latency constraint (ms/token)")
    tournament_cmd.add_argument("--max-power", type=float, metavar="W", help="Max power constraint (W)")
    tournament_cmd.add_argument("--max-cost", type=float, metavar="USD", help="Max hardware cost (USD)")
    tournament_cmd.add_argument("--min-accuracy", type=float, metavar="FRAC", help="Min accuracy (e.g. 0.95)")
    tournament_cmd.add_argument("--carbon-region", default="global_avg", help="Carbon grid region")
    tournament_cmd.add_argument("--quant-schemes", type=str, default="int4,int8,float", help="Quantization schemes to sweep")
    tournament_cmd.add_argument("--synth-modes", type=str, default="overlay,full", help="Synthesis modes to sweep")
    tournament_cmd.add_argument("--node-counts", type=str, default="8,16,32", help="Node counts to sweep (Alloy only)")
    tournament_cmd.add_argument("-o", "--output", type=Path, help="Save report to JSON file")

    compare_cmd = sub.add_parser("compare", help="Run cross-hardware benchmark comparison")
    compare_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")
    compare_cmd.add_argument("--targets", type=str, default="all", help="Comma-separated targets or 'all'")
    compare_cmd.add_argument("--max-latency", type=float, metavar="MS", help="Maximum acceptable latency (ms/token)")
    compare_cmd.add_argument("--max-power", type=float, metavar="W", help="Maximum acceptable power (watts)")
    compare_cmd.add_argument("--max-cost", type=float, metavar="USD", help="Maximum hardware cost (USD)")
    compare_cmd.add_argument("--min-accuracy", type=float, metavar="FRAC", help="Minimum accuracy fraction (e.g. 0.95)")
    compare_cmd.add_argument("--carbon-region", default="global_avg", help="Carbon grid region")
    compare_cmd.add_argument("--inferences-per-day", type=int, default=1000, help="Expected daily inference count for cost amortization")
    compare_cmd.add_argument("--no-sil", action="store_true", help="Skip SiL runs; use profile-based estimates only")
    compare_cmd.add_argument("-o", "--output", type=Path, help="Save report to JSON file")

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

        if hasattr(args, 'sparsity') and args.sparsity:
            from .sparsity import SparsityAnalyzer, SparsityMode
            import numpy as np
            analyzer = SparsityAnalyzer()
            mode_map = {"auto": SparsityMode.AUTO, "2:4": SparsityMode.TWO_FOUR, "4:8": SparsityMode.FOUR_EIGHT, "none": SparsityMode.NONE}
            mode = mode_map[args.sparsity]
            print(f"Sparsity mode: {mode.value}")

        if hasattr(args, 'intermittent') and args.intermittent:
            from .intermittent import CheckpointPlanner, CheckpointConfig, CheckpointGranularity
            gran_map = {"layer": CheckpointGranularity.LAYER, "block": CheckpointGranularity.BLOCK, "operator": CheckpointGranularity.OPERATOR}
            config = CheckpointConfig(
                granularity=gran_map[args.checkpoint_granularity],
                energy_budget_mj=args.energy_budget_mj or 100.0,
            )
            planner = CheckpointPlanner(config)
            checkpoints = planner.insert_checkpoints(ir)
            print(f"Inserted {len(checkpoints)} checkpoint ops (granularity: {config.granularity.value})")

        if args.quantize:
            target = args.target or "fusion"
            rec = recommend_quantization(ir, target)
            if args.quantize == "auto":
                profile = rec.recommended_profile
            elif args.quantize == "int8":
                profile = QUANT_PROFILES[QuantTarget.FUSION_INT8]
            elif args.quantize == "int4":
                profile = QUANT_PROFILES[QuantTarget.FUSION_INT4]
            elif args.quantize == "mixed-precision":
                from .quantize import mixed_precision_search, apply_mixed_precision
                budget = getattr(args, 'accuracy_budget', 0.05)
                profile_path_val = str(args.profile) if args.profile else None
                mp_result = mixed_precision_search(ir, target, accuracy_budget=budget, profile_path=profile_path_val)
                ir = apply_mixed_precision(ir, mp_result)
                print(f"Mixed-precision search complete:")
                print(f"  Budget: {mp_result.accuracy_budget:.0%}")
                print(f"  Estimated loss: {mp_result.estimated_accuracy_loss:.4%}")
                print(f"  Avg bits: {mp_result.avg_weight_bits:.1f}")
                print(f"  Compression: {mp_result.compression_ratio:.1f}x")
                promoted = sum(1 for d in mp_result.decisions if d.promoted)
                print(f"  Promoted layers: {promoted}/{len(mp_result.decisions)}")
                profile = None
            else:
                profile = QUANT_PROFILES[QuantTarget.ELEMENT_FLOAT]

            if profile is not None:
                ir = apply_quantization(ir, profile)
                print(f"Applied quantization: {profile.name}")

        out = args.output or model_path.with_suffix(".tptir")
        ir.save(out)
        print(f"TPT-IR written to {out}")

    elif args.command == "check":
        from .ir import TptIr
        ir = TptIr.from_file(args.tptir)
        target_map = {
            "fusion": HardwareTarget.FUSION, "alloy": HardwareTarget.ALLOY,
            "element": HardwareTarget.ELEMENT, "cim": HardwareTarget.CIM,
            "neuromorphic": HardwareTarget.NEUROMORPHIC, "photonic": HardwareTarget.PHOTONIC,
        }
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

        if getattr(args, 'optimize_carbon', False):
            from .carbon import estimate_carbon, select_lowest_carbon_target
            power_map = {"alloy": (200, 200), "fusion": (100, 100), "element": (50, 50)}
            estimates = []
            for t in target_map:
                if t in power_map:
                    idle, active = power_map[t]
                    est = estimate_carbon(t, active, 1.0, args.carbon_region)
                    estimates.append(est)
            if estimates:
                lowest = select_lowest_carbon_target(estimates)
                print(f"\nCarbon analysis ({args.carbon_region}):")
                for est in sorted(estimates, key=lambda e: e.carbon_gco2):
                    marker = " <-- lowest" if est == lowest else ""
                    print(f"  {est.target}: {est.carbon_gco2:.1f} gCO2{marker}")
                print(f"  Recommended: {lowest.target}")

        if args.output:
            args.output.write_text(json.dumps(report.to_dict(), indent=2))
            print(f"\nReport saved to {args.output}")

    elif args.command == "validate":
        from .validate_cli import run_validation
        result = run_validation(args.tptpkg, args.reference, args.hardware, args.output)
        print(f"Validation grade: {result['grade']}")
        print(f"Overall similarity: {result['overall_similarity']:.2%}")
        print(f"Prompts tested: {result['prompts_tested']}")
        if args.output:
            print(f"Results saved to {args.output}")

    elif args.command == "diagnose":
        from .diagnose_cli import run_diagnostics
        result = run_diagnostics(args.tptpkg, args.hardware, args.output)
        print(f"Diagnostics score: {result['score']:.0%}")
        print(f"Status: {result['status']}")
        print(f"Tests run: {len(result['results'])}")
        for r in result['results']:
            icon = "\u2705" if r['status'] == 'pass' else "\u26a0\ufe0f" if r['status'] == 'warn' else "\u274c"
            print(f"  {icon} {r['test_name']}: {r['message']}")

    elif args.command == "smoke-test":
        from .doctor import run_smoke_test
        results = run_smoke_test(args.target)
        print("Smoke test results:")
        for hw, result in results.items():
            status = "\u2705" if result["status"] == "ok" else "\u274c"
            print(f"  {status} {hw}: {result['status']}")
            if result.get("message"):
                print(f"      {result['message']}")

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

        if hasattr(args, 'lock_to_hardware') and args.lock_to_hardware:
            from .ip_lock import create_lock
            hw_ids = [h.strip() for h in args.lock_to_hardware.split(",")]
            lock = create_lock(hw_ids)
            manifest["hardware_lock"] = lock.to_dict()
            print(f"Locked to hardware: {', '.join(hw_ids)}")

        if getattr(args, 'community_cache', False):
            from .community_cache import CommunityCacheClient
            cache_client = CommunityCacheClient()
            cached = cache_client.lookup(source_hash, targets[0] if targets else "alloy")
            if cached:
                print(f"Community cache hit: saved ~{cached.synthesis_time_s / 3600:.1f}h synthesis time")
            else:
                print("No community cache entry found; will compile from scratch")

        (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
        (out / "ir").mkdir(exist_ok=True)
        ir.save(out / "ir" / "model.tptir")

        for target in targets:
            hw_target = {
                "alloy": HardwareTarget.ALLOY, "fusion": HardwareTarget.FUSION,
                "element": HardwareTarget.ELEMENT, "cim": HardwareTarget.CIM,
                "neuromorphic": HardwareTarget.NEUROMORPHIC, "photonic": HardwareTarget.PHOTONIC,
            }.get(target)
            if hw_target:
                report = check_compatibility(ir, hw_target)
                write_preflight_report(report, out)
                rec = recommend_quantization(ir, target)
                write_quant_profile(rec.recommended_profile, out)

        print(f"Package written to {out}")
        print(f"  Targets: {', '.join(targets)}")
        print(f"  Source SHA-256: {source_hash}")

        if not getattr(args, 'no_regression_check', False):
            existing_pkgs = list(out.parent.glob(f"{ir.metadata.name}*.tptpkg"))
            if len(existing_pkgs) > 1:
                print("Regression check: comparing against previous package...")
                print("  (Full regression requires SiL; run tpt-validate for detailed comparison)")
            else:
                print("Regression check: no previous package found (first build)")
        else:
            print("Regression check: skipped (--no-regression-check)")

    elif args.command == "unpack":
        manifest_path = args.tptpkg / "manifest.json"
        if not manifest_path.exists():
            print(f"Error: No manifest.json found in {args.tptpkg}")
            sys.exit(1)
        manifest = json.loads(manifest_path.read_text())
        if args.json:
            print(json.dumps(manifest, indent=2))
        else:
            print(f"Model: {manifest.get('model_name', 'unknown')}")
            print(f"Format: {manifest.get('format_version', 'unknown')}")
            print(f"Source SHA-256: {manifest.get('source_sha256', 'unknown')}")
            print(f"Targets: {', '.join(manifest.get('targets', []))}")
            if args.output:
                import shutil
                shutil.copytree(args.tptpkg, args.output, dirs_exist_ok=True)
                print(f"Extracted to {args.output}")

    elif args.command == "provenance":
        from .provenance import ProvenanceGraph
        lineage_path = args.tptpkg / "provenance" / "lineage.json"
        if not lineage_path.exists():
            print(f"No provenance data found in {args.tptpkg}")
            print("  (provenance tracking is available for packages compiled with tpt-catalyst 0.1.0+)")
            sys.exit(0)
        graph = ProvenanceGraph.from_file(lineage_path)
        if getattr(args, "json", False):
            print(graph.to_json())
        else:
            graph.print_tree()
            print(f"\nTotal accuracy delta: {graph.total_accuracy_delta:+.4%}")
        if hasattr(args, "diff") and args.diff:
            other_path = args.diff / "provenance" / "lineage.json"
            if not other_path.exists():
                print(f"No provenance data in {args.diff}")
            else:
                other = ProvenanceGraph.from_file(other_path)
                diff_steps = graph.diff(other)
                print(f"\nSteps in {args.diff.name} not in {args.tptpkg.name}:")
                for step in diff_steps:
                    print(f"  [{step['step_type']}] {step['step_id'][:8]}… — {step.get('notes', '')}")

    elif args.command == "tournament":
        from .tournament import TournamentRunner, TournamentConfig, TournamentConstraints
        config = TournamentConfig(
            targets=[t.strip() for t in args.targets.split(",")],
            quantization_schemes=[q.strip() for q in args.quant_schemes.split(",")],
            synthesis_modes=[s.strip() for s in args.synth_modes.split(",")],
            node_counts=[int(n.strip()) for n in args.node_counts.split(",")],
        )
        constraints = TournamentConstraints(
            max_latency_ms=args.max_latency,
            max_power_w=args.max_power,
            max_cost_usd=args.max_cost,
            min_accuracy=args.min_accuracy,
            carbon_region=args.carbon_region,
        )
        runner = TournamentRunner(config=config, verbose=True)
        print(f"Running compilation tournament ({runner.config.targets})...")
        report = runner.run(args.tptir, constraints)
        report.print_table()
        if args.output:
            args.output.write_text(report.to_json())
            print(f"\nReport saved to {args.output}")

    elif args.command == "compare":
        from .compare import ComparisonRunner, ComparisonConstraints
        from .compare import _SUPPORTED_TARGETS

        target_list = (
            _SUPPORTED_TARGETS
            if args.targets == "all"
            else [t.strip() for t in args.targets.split(",")]
        )
        constraints = ComparisonConstraints(
            max_latency_ms=args.max_latency,
            max_power_w=args.max_power,
            max_cost_usd=args.max_cost,
            min_accuracy=args.min_accuracy,
            carbon_region=args.carbon_region,
            inferences_per_day=args.inferences_per_day,
        )
        runner = ComparisonRunner(targets=target_list, use_sil=not args.no_sil)
        report = runner.run(args.tptir, constraints)
        report.print_table()
        if args.output:
            args.output.write_text(report.to_json())
            print(f"\nReport saved to {args.output}")

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


def _emit_structured_error(error_type: str, message: str, details: dict | None = None) -> None:
    """Emit a structured JSON error to stderr for CI/CD consumption."""
    import json as _json
    error_obj = {
        "error": error_type,
        "message": message,
        "tool": "tpt-catalyst",
    }
    if details:
        error_obj["details"] = details
    print(_json.dumps(error_obj), file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        _emit_structured_error(type(e).__name__, str(e))
        sys.exit(1)
