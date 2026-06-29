"""CLI entry point for tpt-element."""

import argparse
import sys
import numpy as np
from pathlib import Path
from .weight_map import WeightMapper
from .spice import SpiceNetlistGenerator


def _run_demo(output_dir: Path, tolerance: float, temperature_k: float, hours: float) -> None:
    """Phase 3 milestone demo: 3-layer analog NN → drift simulation → KiCad PCB."""
    from .reality_check import RealityCheckModel, CircuitFeatures, generate_training_data
    from .kicad import KiCadExporter

    # Topology: 4 → 8 → 4 → 2
    layer_shapes = [(4, 8), (8, 4), (4, 2)]
    layer_names = ["input->hidden1", "hidden1->hidden2", "hidden2->output"]

    rng = np.random.default_rng(42)
    layer_weights = [rng.standard_normal(shape) * 0.1 for shape in layer_shapes]

    print("=" * 60)
    print("  TPT Element — Phase 3 Milestone Demo")
    print("  3-Layer Analog Neural Network")
    print("=" * 60)
    print(f"  Topology : 4 -> 8 -> 4 -> 2")
    print(f"  Tolerance: {tolerance*100:.0f}%")
    print(f"  Temp     : {temperature_k:.1f} K ({temperature_k - 273.15:.1f} °C)")
    print(f"  Sim time : {hours:.0f} h")
    print()

    # Step 1: Weight mapping
    print("[ 1/5 ] Mapping weights to physical components ...")
    mapper = WeightMapper(tolerance=tolerance)
    all_components = []
    for weights, name, shape in zip(layer_weights, layer_names, layer_shapes):
        layer_comps = mapper.map_weights(weights)
        layer_conf = mapper.compute_confidence_score(layer_comps)
        all_components.extend(layer_comps)
        print(f"        {name:20s}  {shape[0]}×{shape[1]} = {len(layer_comps):3d} resistors  "
              f"confidence {layer_conf:.2%}")
    print(f"        Total components: {len(all_components)}")

    # Step 2: SPICE netlist + thermal drift simulation
    print()
    print("[ 2/5 ] Building SPICE netlist and simulating thermal drift ...")
    gen = SpiceNetlistGenerator(vdd=3.3)
    for comp in all_components:
        gen.add_component(comp)
    sim_result = gen.full_simulation(temperature_k=temperature_k, hours=hours)
    print(f"        Nodes simulated : {len(gen.nodes)}")
    max_noise = max(r["thermal_noise_uV"] for r in sim_result.thermal_noise)
    max_drift = max(r["drift_pct"] for r in sim_result.voltage_drift)
    print(f"        Peak thermal noise : {max_noise:.2f} µV")
    print(f"        Peak voltage drift : {max_drift:.4f}% over {hours:.0f} h")
    print(f"        Confidence score   : {sim_result.confidence_score:.2%}")

    # Step 3: Reality Check — fast ML drift prediction per layer
    print()
    print("[ 3/5 ] Reality Check — training ML model on synthetic SPICE data ...")
    rc_model = RealityCheckModel()
    rc_features, rc_labels = generate_training_data(n_samples=1000)
    rc_model.train(rc_features, rc_labels)
    print("        Model trained on 1000 synthetic SPICE samples.")
    print()
    print("        Per-layer drift predictions:")
    for weights, name in zip(layer_weights, layer_names):
        comps = mapper.map_weights(weights)
        pred = rc_model.predict(CircuitFeatures(
            resistance_values=[c.value for c in comps],
            tolerance=tolerance,
            temperature_k=temperature_k,
            voltage_v=3.3,
            component_count=len(comps),
        ))
        print(f"        {name:20s}  drift {pred.predicted_drift_pct:+.4f}%  "
              f"failure_prob {pred.failure_probability:.2%}  conf {pred.confidence:.2%}")

    # Step 4: Mitigations
    print()
    print("[ 4/5 ] Generating mitigation recommendations ...")
    mitigations = gen.generate_mitigations(sim_result)
    for m in mitigations:
        print(f"        • {m}")

    # Step 5: KiCad PCB export
    print()
    print("[ 5/5 ] Exporting KiCad PCB files ...")
    output_dir.mkdir(parents=True, exist_ok=True)
    exporter = KiCadExporter(board_width_mm=200.0, board_height_mm=150.0)
    exporter.add_components(all_components)
    saved = exporter.save(output_dir)

    netlist_path = output_dir / "three_layer_nn.spice"
    gen.save_netlist(netlist_path)

    print(f"        PCB layout  : {saved['pcb']}")
    print(f"        Schematic   : {saved['schematic']}")
    print(f"        SPICE netlist: {netlist_path}")
    print()
    print("=" * 60)
    print("  Demo complete. KiCad PCB ready for manufacturing.")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tpt-element",
        description="TPT Element — Analog compute weight mapping and drift simulation",
    )
    sub = parser.add_subparsers(dest="command")

    sim_cmd = sub.add_parser("simulate", help="Map weights and generate SPICE netlist")
    sim_cmd.add_argument("--weights", type=Path, help="Path to weights .npy file")
    sim_cmd.add_argument("--tolerance", type=float, default=0.05)
    sim_cmd.add_argument("-o", "--output", type=Path, default=Path("circuit.spice"))

    demo_cmd = sub.add_parser(
        "demo",
        help="Phase 3 milestone: 3-layer analog NN → thermal drift → KiCad PCB",
    )
    demo_cmd.add_argument(
        "-o", "--output", type=Path, default=Path("three_layer_nn_demo"),
        help="Output directory for KiCad and SPICE files",
    )
    demo_cmd.add_argument("--tolerance", type=float, default=0.01,
                          help="Component tolerance (default: 0.01 = 1%%)")
    demo_cmd.add_argument("--temperature", type=float, default=330.0,
                          help="Operating temperature in Kelvin (default: 330 K / 57 °C)")
    demo_cmd.add_argument("--hours", type=float, default=24.0,
                          help="Simulation duration in hours (default: 24)")

    dataset_cmd = sub.add_parser("generate-dataset", help="Generate SPICE dataset for Reality Check training")
    dataset_cmd.add_argument("--runs", type=int, default=1000, help="Number of SPICE simulation runs")
    dataset_cmd.add_argument("--threshold", type=int, default=5000, help="Auto-train Reality Check when dataset reaches this size")
    dataset_cmd.add_argument("-o", "--output", type=Path, default=Path("spice_dataset"), help="Output directory for dataset")

    args = parser.parse_args()

    if args.command == "simulate":
        if args.weights and args.weights.exists():
            weights = np.load(args.weights)
        else:
            weights = np.random.randn(4, 4) * 0.1

        mapper = WeightMapper(tolerance=args.tolerance)
        components = mapper.map_weights(weights)
        confidence = mapper.compute_confidence_score(components)

        gen = SpiceNetlistGenerator()
        for c in components:
            gen.add_component(c)
        gen.save_netlist(args.output)

        print(f"Generated {len(components)} components")
        print(f"Confidence score: {confidence:.2%}")
        print(f"Netlist written to {args.output}")

    elif args.command == "demo":
        _run_demo(
            output_dir=args.output,
            tolerance=args.tolerance,
            temperature_k=args.temperature,
            hours=args.hours,
        )

    elif args.command == "generate-dataset":
        from .spice_pipeline import SpiceSweepOrchestrator, SweepConfig
        from .reality_check import RealityCheckModel, generate_training_data
        import json

        orchestrator = SpiceSweepOrchestrator()
        results = orchestrator.run(max_runs=args.runs)

        args.output.mkdir(parents=True, exist_ok=True)
        dataset_path = args.output / "sweep_results.json"
        dataset_path.write_text(json.dumps([r.to_dict() for r in results], indent=2))

        print(f"Generated {len(results)} SPICE simulation results")
        print(f"Dataset saved to {dataset_path}")

        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        print(f"  Passed: {passed}, Failed: {failed}")

        if len(results) >= args.threshold:
            print(f"\nDataset threshold reached ({len(results)} >= {args.threshold}).")
            print("Auto-training Reality Check ML model...")
            features, labels = generate_training_data(n_samples=len(results))
            rc_model = RealityCheckModel()
            rc_model.train(features, labels)
            checkpoint_path = args.output / "reality_check_checkpoint.json"
            rc_model.save(str(checkpoint_path))
            print(f"Reality Check model saved to {checkpoint_path}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
