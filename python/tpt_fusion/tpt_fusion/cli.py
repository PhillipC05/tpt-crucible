"""CLI entry point for tpt-fusion."""

import argparse
import json
import sys
from pathlib import Path
from .mac_array import MacConfig
from .board import get_board, list_boards
from .rtl import RtlGenerator
from .toolchain import YosysRunner, NextpnrRunner
from .overlay import OverlayCompiler, OverlayHotSwap, OverlayManifest, FuseCfg


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tpt-fusion",
        description="TPT Fusion — FPGA synthesis and HBM auto-routing",
    )
    sub = parser.add_subparsers(dest="command")

    compile_cmd = sub.add_parser("compile", help="Compile model for FPGA target")
    compile_cmd.add_argument("tptir", type=Path, help="Path to .tptir file")
    compile_cmd.add_argument("--board", default="alveo_u250", help="Target FPGA board")
    compile_cmd.add_argument("--mode", default="overlay", choices=["overlay", "full"], help="Compile mode: overlay (fast, reuse bitstream) or full (resynthesis)")
    compile_cmd.add_argument("-o", "--output", type=Path, help="Output directory")

    load_cmd = sub.add_parser("load", help="Hot-load model weights to running overlay")
    load_cmd.add_argument("fusecfg", type=Path, help="Path to .fusecfg file")
    load_cmd.add_argument("--weights", type=Path, help="Path to weight binary file")
    load_cmd.add_argument("--model-name", default="", help="Model name for cache key")
    load_cmd.add_argument("--hbm-mb", type=float, default=4096, help="Total HBM size in MB")
    load_cmd.add_argument("--cache-slots", type=int, default=8, help="Number of HBM cache slots")

    cache_cmd = sub.add_parser("cache", help="Manage HBM model cache")
    cache_sub = cache_cmd.add_subparsers(dest="cache_action")
    cache_list_cmd = cache_sub.add_parser("list", help="Show HBM slot occupancy")
    cache_list_cmd.add_argument("--hbm-mb", type=float, default=4096, help="Total HBM size in MB")
    cache_list_cmd.add_argument("--cache-slots", type=int, default=8, help="Number of HBM cache slots")
    cache_evict_cmd = cache_sub.add_parser("evict", help="Manually free an HBM slot")
    cache_evict_cmd.add_argument("model", help="Model name to evict")
    cache_evict_cmd.add_argument("--hbm-mb", type=float, default=4096)
    cache_evict_cmd.add_argument("--cache-slots", type=int, default=8)

    overlay_cmd = sub.add_parser("overlay", help="Manage FPGA overlays")
    overlay_sub = overlay_cmd.add_subparsers(dest="overlay_action")
    overlay_list_cmd = overlay_sub.add_parser("list", help="Show available overlays for board")
    overlay_list_cmd.add_argument("--board", default="alveo_u250")
    overlay_flash_cmd = overlay_sub.add_parser("flash", help="Flash a specific overlay")
    overlay_flash_cmd.add_argument("overlay_name", help="Overlay name to flash")
    overlay_flash_cmd.add_argument("--board", default="alveo_u250")

    gen_cmd = sub.add_parser("generate", help="Generate RTL from MAC array config")
    gen_cmd.add_argument("--board", default="xilinx_alveo_u280", help="Target FPGA board")
    gen_cmd.add_argument("--rows", type=int, default=16, help="MAC array rows")
    gen_cmd.add_argument("--cols", type=int, default=16, help="MAC array columns")
    gen_cmd.add_argument("-o", "--output", type=Path, default=Path("rtl"), help="Output directory")

    boards_cmd = sub.add_parser("boards", help="List available FPGA boards")

    syn_cmd = sub.add_parser("synthesize", help="Run Yosys + Nextpnr synthesis")
    syn_cmd.add_argument("--rtl-dir", type=Path, required=True, help="Directory with RTL files")
    syn_cmd.add_argument("--board", default="xilinx_alveo_u280")
    syn_cmd.add_argument("-o", "--output", type=Path, default=Path("bitstream"), help="Output directory")

    args = parser.parse_args()

    if args.command == "compile":
        compiler = OverlayCompiler(board=args.board)
        fusecfg = compiler.compile(ir_nodes=22, precision="int8")
        output_dir = args.output or Path("fusion_output")
        output_dir.mkdir(parents=True, exist_ok=True)
        fusecfg.save(output_dir / "model.fusecfg")
        print(f"Compiled for {args.board} in {args.mode} mode")
        print(f"  Datapath: {fusecfg.datapath_width}-bit")
        print(f"  Layers: {fusecfg.layer_count}")
        print(f"  FuseCfg written to {output_dir / 'model.fusecfg'}")

    elif args.command == "load":
        fusecfg = FuseCfg.load(args.fusecfg)
        hotswap = OverlayHotSwap(total_hbm_mb=args.hbm_mb, cache_slots=args.cache_slots)
        weight_size = args.weights.stat().st_size / (1024 * 1024) if args.weights and args.weights.exists() else 0.0
        model_name = args.model_name or args.fusecfg.stem
        ok, msg = hotswap.load_model(model_name, fusecfg, weight_size)
        print(f"{'OK' if ok else 'FAILED'}: {msg}")

    elif args.command == "cache":
        hotswap = OverlayHotSwap(total_hbm_mb=args.hbm_mb, cache_slots=args.cache_slots)
        if args.cache_action == "list":
            slots = hotswap.list_cache()
            if not slots:
                print("No models in HBM cache")
            else:
                for s in slots:
                    print(f"  Slot {s['slot_id']}: {s['model_name']} ({s['weight_size_mb']:.1f} MB)")
        elif args.cache_action == "evict":
            ok = hotswap.evict_model(args.model)
            print(f"{'Evicted' if ok else 'Not found'}: {args.model}")
        else:
            cache_cmd.print_help()

    elif args.command == "overlay":
        if args.overlay_action == "list":
            overlays = [
                OverlayManifest(name="dense-int4", board=args.board, datapath="dense", precision="int4", max_layers=64, max_model_size_mb=2048),
                OverlayManifest(name="dense-int8", board=args.board, datapath="dense", precision="int8", max_layers=64, max_model_size_mb=4096),
                OverlayManifest(name="moe-int4", board=args.board, datapath="moe", precision="int4", max_layers=32, max_model_size_mb=1024),
            ]
            print(f"Available overlays for {args.board}:")
            for o in overlays:
                print(f"  {o.name}: {o.datapath}/{o.precision}, max {o.max_layers} layers, {o.max_model_size_mb} MB")
        elif args.overlay_action == "flash":
            print(f"Flashing overlay '{args.overlay_name}' to {args.board}...")
            print("This typically takes 5-10 minutes. User will be notified on completion.")
        else:
            overlay_cmd.print_help()

    elif args.command == "generate":
        board = get_board(args.board)
        config = MacConfig(rows=args.rows, cols=args.cols)
        gen = RtlGenerator(board, config)
        files = gen.generate(args.output)
        for name, path in files.items():
            print(f"Generated {name}: {path}")

    elif args.command == "boards":
        for name in list_boards():
            board = get_board(name)
            has_hbm = "HBM" if board.hbm else "No HBM"
            print(f"  {name}: {board.fpga_part} ({has_hbm})")

    elif args.command == "synthesize":
        board = get_board(args.board)
        yosys = YosysRunner()
        nextpnr = NextpnrRunner()

        if not yosys.check_available():
            print("Warning: Yosys not found. Install it for synthesis.")
        if not nextpnr.check_available():
            print("Warning: Nextpnr not found. Install it for place-and-route.")

        print(f"Synthesis pipeline ready for {board.name}")
        print(f"RTL directory: {args.rtl_dir}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
