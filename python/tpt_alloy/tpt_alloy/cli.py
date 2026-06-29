"""CLI entry point for tpt-alloy."""

import argparse
import json
import sys
from pathlib import Path


def _layer_count_from_ir(tptir_path: Path) -> int:
    """Read the number of graph nodes from a .tptir JSON file."""
    try:
        data = json.loads(tptir_path.read_text())
        count = len(data.get("graph", {}).get("nodes", []))
        return count if count > 0 else 100
    except Exception:
        return 100
from .topology import Topology
from .partition import PartitionConfig, partition_model
from .firmware import FirmwareTarget, FirmwareRtos, generate_firmware
from .platformio import generate_flash_script
from .fault_tolerance import HeartbeatConfig
from .ai_topology import AITopologyAdvisor, TopologyConstraints


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tpt-alloy",
        description="TPT Alloy — Swarm partitioning and firmware generation",
    )
    sub = parser.add_subparsers(dest="command")

    part_cmd = sub.add_parser("partition", help="Partition a model for swarm deployment")
    part_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")
    part_cmd.add_argument("--topology", default="grid2d", choices=["grid2d", "star", "ring"])
    part_cmd.add_argument("--nodes", type=int, default=16, help="Number of swarm nodes")
    part_cmd.add_argument(
        "--partition-strategy",
        default="layer",
        choices=["layer", "head-parallel", "hybrid"],
        help="Partitioning strategy: layer (round-robin), head-parallel (distribute attention heads), "
             "hybrid (head-parallel for attention, layer-serial for FFN)",
    )
    part_cmd.add_argument(
        "--num-heads",
        type=int,
        default=32,
        help="Number of attention heads in the model (used for head-parallel / hybrid)",
    )
    part_cmd.add_argument(
        "--head-dim",
        type=int,
        default=64,
        help="Dimension of each attention head",
    )
    part_cmd.add_argument(
        "--fault-tolerance",
        choices=["enabled", "disabled"],
        default="disabled",
        help="Enable fault-tolerant execution with heartbeat monitoring",
    )
    part_cmd.add_argument(
        "--heartbeat-interval-ms",
        type=int,
        default=1000,
        help="Heartbeat interval in milliseconds (requires --fault-tolerance enabled)",
    )
    part_cmd.add_argument(
        "--heartbeat-timeout-ms",
        type=int,
        default=3000,
        help="Node timeout in milliseconds before declaring dead",
    )

    advise_cmd = sub.add_parser("advise", help="Get topology and strategy recommendation")
    advise_cmd.add_argument("--layers", type=int, required=True, help="Number of layers in the model")
    advise_cmd.add_argument("--nodes", type=int, default=16, help="Number of swarm nodes")
    advise_cmd.add_argument("--latency-budget-ms", type=float, default=10.0, help="Latency budget in ms")
    advise_cmd.add_argument("--power-budget-mw", type=float, default=5000.0, help="Power budget in mW")
    advise_cmd.add_argument("--num-heads", type=int, default=0, help="Number of attention heads (0 = unknown)")
    advise_cmd.add_argument(
        "--op-types",
        nargs="*",
        default=None,
        help="Operation types for each layer (e.g. self_attention linear gelu)",
    )

    flash_cmd = sub.add_parser("flash", help="Generate firmware for all nodes")
    flash_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")
    flash_cmd.add_argument("--target", default="esp32", choices=["esp32", "rp2040", "riscv"])
    flash_cmd.add_argument(
        "--rtos",
        default="none",
        choices=["none", "zephyr"],
        help="RTOS to target (zephyr requires --target riscv)",
    )
    flash_cmd.add_argument("--nodes", type=int, default=16)
    flash_cmd.add_argument("--partition-strategy", default="layer", choices=["layer", "head-parallel", "hybrid"])
    flash_cmd.add_argument("--num-heads", type=int, default=32)
    flash_cmd.add_argument("--head-dim", type=int, default=64)
    flash_cmd.add_argument("-o", "--output", type=Path, default=Path("firmware"), help="Output directory")
    flash_cmd.add_argument("--flash-script", action="store_true", help="Generate master flash script")

    discover_cmd = sub.add_parser("discover", help="Auto-discover swarm topology via RTT probing")
    discover_cmd.add_argument("--nodes", type=int, default=16, help="Number of nodes to discover")
    discover_cmd.add_argument("--timeout", type=str, default="30s", help="Discovery timeout (e.g. 30s)")
    discover_cmd.add_argument("-o", "--output", type=Path, default=Path("topology.json"), help="Output topology file")

    tune_cmd = sub.add_parser("tune", help="Auto-tune communication parameters via SiL sweep")
    tune_cmd.add_argument("tptpkg", type=Path, help="Path to .tptpkg directory")
    tune_cmd.add_argument("--topology", type=Path, default=Path("topology.json"), help="Topology file")
    tune_cmd.add_argument("-o", "--output", type=Path, default=Path("tuned_params.json"), help="Output tuned parameters")

    pipeline_cmd = sub.add_parser("pipeline", help="Configure pipeline parallelism for swarm")
    pipeline_cmd.add_argument("--depth", type=int, default=4, help="Pipeline depth (in-flight tokens)")
    pipeline_cmd.add_argument("--nodes", type=int, default=16, help="Number of swarm nodes")
    pipeline_cmd.add_argument("--kv-bytes-per-token", type=int, default=128, help="KV cache bytes per token")
    pipeline_cmd.add_argument("-o", "--output", type=Path, help="Output pipeline config")

    args = parser.parse_args()

    if args.command == "partition":
        rows = cols = int(args.nodes**0.5) or 1
        config = PartitionConfig(
            topology=Topology.grid2d(rows, cols),
            strategy=args.partition_strategy,
            num_heads=args.num_heads,
            head_dim=args.head_dim,
        )
        partitions = partition_model(_layer_count_from_ir(args.tptir), config)

        ft_enabled = args.fault_tolerance == "enabled"
        ft_config = None
        if ft_enabled:
            ft_config = HeartbeatConfig(
                interval_ms=args.heartbeat_interval_ms,
                timeout_ms=args.heartbeat_timeout_ms,
            ).to_dict()

        output = []
        for p in partitions:
            entry: dict = {
                "node_id": p.node_id,
                "layers": p.assigned_layers,
                "assigned_heads": p.assigned_heads,
                "is_aggregator": p.is_aggregator,
                "cross_edges": [
                    {
                        "from_node": e.from_node,
                        "to_node": e.to_node,
                        "tensor_name": e.tensor_name,
                        "protocol": e.protocol,
                    }
                    for e in p.cross_node_edges
                ],
            }
            if ft_config is not None:
                entry["fault_tolerance"] = ft_config
            output.append(entry)

        print(json.dumps(output, indent=2))

    elif args.command == "advise":
        advisor = AITopologyAdvisor()
        constraints = TopologyConstraints(
            node_count=args.nodes,
            latency_budget_ms=args.latency_budget_ms,
            power_budget_mw=args.power_budget_mw,
        )
        recommendations = advisor.recommend(
            layer_count=args.layers,
            tensor_shapes=[],
            constraints=constraints,
            op_types=args.op_types,
            num_heads=args.num_heads,
        )
        print(json.dumps(
            [
                {
                    "topology_type": r.topology_type,
                    "node_count": r.node_count,
                    "predicted_latency_ms": r.predicted_latency_ms,
                    "predicted_power_mw": r.predicted_power_mw,
                    "confidence": r.confidence,
                    "score": r.score,
                    "partition_strategy": r.partition_strategy,
                    "reasoning": r.reasoning,
                }
                for r in recommendations
            ],
            indent=2,
        ))

    elif args.command == "flash":
        rows = cols = int(args.nodes**0.5) or 1
        config = PartitionConfig(
            topology=Topology.grid2d(rows, cols),
            strategy=args.partition_strategy,
            num_heads=args.num_heads,
            head_dim=args.head_dim,
        )
        partitions = partition_model(_layer_count_from_ir(args.tptir), config)
        target = FirmwareTarget(args.target)
        rtos = FirmwareRtos(args.rtos)

        if rtos == FirmwareRtos.ZEPHYR and target != FirmwareTarget.RISCV:
            print("Warning: --rtos zephyr is only supported with --target riscv", file=sys.stderr)

        args.output.mkdir(parents=True, exist_ok=True)

        bundles = []
        for p in partitions:
            bundle = generate_firmware(p, target, rtos=rtos)
            bundles.append(bundle)
            fw_path = args.output / f"node_{bundle.node_id}.c"
            fw_path.write_text(bundle.source_code)
            cfg_path = args.output / f"node_{bundle.node_id}.json"
            cfg_path.write_text(bundle.config_json)
            print(f"Generated firmware: {fw_path}")

        if args.flash_script:
            script_path = args.output / "flash_all.sh"
            generate_flash_script(bundles, script_path)
            print(f"Generated flash script: {script_path}")

    elif args.command == "discover":
        from .auto_discovery import TopologyDiscovery, DiscoveryConfig, save_topology
        timeout = float(args.timeout.rstrip("s"))
        disc_config = DiscoveryConfig(node_count=args.nodes, timeout_s=timeout)
        discovery = TopologyDiscovery(disc_config)
        result = discovery.discover()

        if result.success and result.inferred_topology:
            save_topology(result.inferred_topology, args.output)
            print(f"Discovered topology: {result.inferred_topology.type.value}")
            print(f"Nodes: {result.inferred_topology.node_count()}")
            print(f"Measurements: {len(result.measurements)}")
            print(f"Topology saved to {args.output}")
        else:
            print(f"Discovery failed: {result.error}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "tune":
        from .sil_tuner import SiLTuner
        import json as _json
        tuner = SiLTuner()
        params = tuner.tune(args.tptpkg, args.topology)
        args.output.write_text(_json.dumps(params, indent=2))
        print(f"Tuned parameters written to {args.output}")

    elif args.command == "pipeline":
        from .pipeline import build_pipeline_schedule, save_pipeline_config, PipelineConfig, estimate_psram_usage
        rows = cols = int(args.nodes**0.5) or 1
        pconfig = PartitionConfig(topology=Topology.grid2d(rows, cols))
        partitions = partition_model(args.nodes * pconfig.max_layers_per_node, pconfig)

        pipe_config = PipelineConfig(pipeline_depth=args.depth)
        schedule = build_pipeline_schedule(partitions, pipe_config, kv_bytes_per_token=args.kv_bytes_per_token)
        psram = estimate_psram_usage(schedule)

        print(f"Pipeline depth: {schedule.depth}")
        print(f"Stages: {len(schedule.stages)}")
        print(f"Utilization: {schedule.utilization:.1%}")
        print(f"Pipeline bubble: {schedule.pipeline_bubble_pct:.1f}%")
        print(f"Total KV buffer: {psram['total_kv_bytes'] / 1024:.0f} KB")

        if args.output:
            save_pipeline_config(schedule, args.output)
            print(f"Pipeline config saved to {args.output}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
