"""Write Fusion artifacts into .tptpkg structure."""

from __future__ import annotations
from pathlib import Path
from .board import BoardConfig
from .mac_array import MacConfig
from .rtl import RtlGenerator


def write_fusion_artifacts(
    board: BoardConfig,
    mac_config: MacConfig,
    pkg_dir: Path,
) -> dict[str, str]:
    """Write RTL, constraints, and board config into the package."""
    artifacts = {}
    fusion_dir = pkg_dir / "targets" / "fusion"
    fusion_dir.mkdir(parents=True, exist_ok=True)

    gen = RtlGenerator(board, mac_config)
    files = gen.generate(fusion_dir)

    for name, path in files.items():
        artifacts[f"fusion/{path.name}"] = str(path)

    import json
    board_info = {
        "name": board.name,
        "fpga_part": board.fpga_part,
        "hbm": {"capacity_gb": board.hbm.capacity_gb, "channels": board.hbm.channels} if board.hbm else None,
        "mac_config": {
            "rows": mac_config.rows,
            "cols": mac_config.cols,
            "data_width": mac_config.data_width,
        },
    }
    board_path = fusion_dir / "board.json"
    board_path.write_text(json.dumps(board_info, indent=2))
    artifacts["fusion/board.json"] = str(board_path)

    return artifacts
