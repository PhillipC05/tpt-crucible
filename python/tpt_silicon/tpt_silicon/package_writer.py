"""Write CIM artifacts into .tptpkg structure."""

from __future__ import annotations
import json
from pathlib import Path

from .weight_packer import CimWeightPacker, PackedArray
from .array_layout import CimArrayLayout, LayoutConfig
from .bitline import BitlineOpGenerator


def write_silicon_artifacts(
    layout: CimArrayLayout,
    weight_data: PackedArray | None = None,
    pkg_dir: Path | None = None,
) -> dict[str, str]:
    """Write CIM target artifacts into the package.

    Produces:
        targets/silicon/weight_arrays.bin  — packed weight binary
        targets/silicon/layout.json        — array layout + tile mapping
        targets/silicon/config.json        — CIM configuration
    """
    artifacts = {}
    silicon_dir = (pkg_dir / "targets" / "silicon") if pkg_dir else Path("targets/silicon")
    silicon_dir.mkdir(parents=True, exist_ok=True)

    if weight_data is not None:
        packer = CimWeightPacker(
            array_rows=layout.config.array_rows,
            array_cols=layout.config.array_cols,
            bit_precision=layout.config.bit_precision,
        )
        raw = packer.serialize_array(weight_data)
        weight_path = silicon_dir / "weight_arrays.bin"
        weight_path.write_bytes(raw)
        artifacts["silicon/weight_arrays.bin"] = str(weight_path)

    layout_path = silicon_dir / "layout.json"
    layout_path.write_text(json.dumps(layout.to_dict(), indent=2))
    artifacts["silicon/layout.json"] = str(layout_path)

    generator = BitlineOpGenerator()
    bitline_ops = []
    for layer_name in layout.layer_map:
        tile_count = layout.layer_map[layer_name]
        for tile_id in range(tile_count):
            generator.matmul_sequence(tile_id, layout.config.array_rows, layout.config.array_cols)
    bitline_ops = generator.to_dict()

    config = {
        "board": "default",
        "precision": layout.config.bit_precision,
        "array_rows": layout.config.array_rows,
        "array_cols": layout.config.array_cols,
        "num_arrays": layout.config.num_arrays,
        "total_tiles": layout.get_total_tiles(),
        "total_mac_units": layout.config.total_mac_units,
        "bitline_ops": bitline_ops,
    }
    config_path = silicon_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2))
    artifacts["silicon/config.json"] = str(config_path)

    return artifacts
