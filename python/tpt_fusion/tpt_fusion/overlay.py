"""FPGA Overlay Architecture — pre-built bitstream with hot-swappable weights."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json
import time


@dataclass
class FuseCfg:
    datapath_width: int = 8
    layer_count: int = 22
    weight_loading_addresses: dict[int, int] = field(default_factory=dict)
    model_name: str = ""
    precision: str = "int8"

    def to_dict(self) -> dict[str, Any]:
        return {
            "datapath_width": self.datapath_width,
            "layer_count": self.layer_count,
            "weight_loading_addresses": self.weight_loading_addresses,
            "model_name": self.model_name,
            "precision": self.precision,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FuseCfg:
        return cls(
            datapath_width=data.get("datapath_width", 8),
            layer_count=data.get("layer_count", 22),
            weight_loading_addresses=data.get("weight_loading_addresses", {}),
            model_name=data.get("model_name", ""),
            precision=data.get("precision", "int8"),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> FuseCfg:
        return cls.from_dict(json.loads(json_str))

    def save(self, path: Path) -> None:
        path.write_text(self.to_json())

    @classmethod
    def load(cls, path: Path) -> FuseCfg:
        return cls.from_json(path.read_text())


@dataclass
class OverlayManifest:
    name: str
    board: str
    datapath: str
    precision: str
    max_layers: int
    max_model_size_mb: float
    bitstream_url: str = ""
    fusecfg_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "board": self.board,
            "datapath": self.datapath,
            "precision": self.precision,
            "max_layers": self.max_layers,
            "max_model_size_mb": self.max_model_size_mb,
            "bitstream_url": self.bitstream_url,
            "fusecfg_url": self.fusecfg_url,
        }

    def is_compatible(self, fusecfg: FuseCfg) -> bool:
        return (fusecfg.datapath_width <= 8 and
                fusecfg.layer_count <= self.max_layers and
                fusecfg.precision in self.precision)


@dataclass
class HbmSlot:
    slot_id: int
    model_name: str = ""
    fusecfg: FuseCfg | None = None
    weight_size_mb: float = 0.0
    last_used: float = 0.0
    occupied: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "model_name": self.model_name,
            "weight_size_mb": round(self.weight_size_mb, 2),
            "last_used": self.last_used,
            "occupied": self.occupied,
        }


class OverlayCompiler:
    """Compile TPT-IR to .fusecfg + weight binary for overlay loading."""

    def __init__(self, board: str = "alveo_u250"):
        self.board = board

    def compile(self, ir_nodes: int, precision: str = "int8") -> FuseCfg:
        addresses = {}
        addr = 0x1000
        for i in range(ir_nodes):
            addresses[i] = addr
            addr += 0x1000

        return FuseCfg(
            datapath_width=8 if precision == "int8" else 4,
            layer_count=ir_nodes,
            weight_loading_addresses=addresses,
            precision=precision,
        )

    def generate_weight_binary(self, weights: list[float], precision: int = 8) -> bytes:
        import numpy as np
        arr = np.array(weights, dtype=np.float32)
        if precision == 8:
            quantized = ((arr - arr.min()) / (arr.max() - arr.min()) * 255).astype(np.uint8)
        else:
            quantized = ((arr - arr.min()) / (arr.max() - arr.min()) * 15).astype(np.uint8)
        return quantized.tobytes()


class OverlayHotSwap:
    """Manage overlay hot-swapping and HBM cache."""

    def __init__(self, total_hbm_mb: float = 4096, cache_slots: int = 8):
        self.total_hbm_mb = total_hbm_mb
        self.cache_slots = cache_slots
        self.slots: list[HbmSlot] = [HbmSlot(slot_id=i) for i in range(cache_slots)]
        self.current_overlay: str = ""

    def load_model(self, model_name: str, fusecfg: FuseCfg, weight_size_mb: float) -> tuple[bool, str]:
        for slot in self.slots:
            if slot.occupied and slot.model_name == model_name:
                slot.last_used = time.time()
                return True, f"Cache hit: loaded from slot {slot.slot_id}"

        empty_slot = next((s for s in self.slots if not s.occupied), None)
        if empty_slot:
            empty_slot.model_name = model_name
            empty_slot.fusecfg = fusecfg
            empty_slot.weight_size_mb = weight_size_mb
            empty_slot.occupied = True
            empty_slot.last_used = time.time()
            return True, f"Loaded to slot {empty_slot.slot_id}"

        lru_slot = min(self.slots, key=lambda s: s.last_used)
        old_name = lru_slot.model_name
        lru_slot.model_name = model_name
        lru_slot.fusecfg = fusecfg
        lru_slot.weight_size_mb = weight_size_mb
        lru_slot.last_used = time.time()
        return True, f"Evicted {old_name} from slot {lru_slot.slot_id}, loaded {model_name}"

    def evict_model(self, model_name: str) -> bool:
        for slot in self.slots:
            if slot.model_name == model_name:
                slot.model_name = ""
                slot.fusecfg = None
                slot.weight_size_mb = 0.0
                slot.occupied = False
                return True
        return False

    def list_cache(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self.slots if s.occupied]

    def check_compatibility(self, fusecfg: FuseCfg, overlay: OverlayManifest) -> tuple[bool, str]:
        if overlay.is_compatible(fusecfg):
            return True, "Compatible"
        return False, f"Overlay {overlay.name} incompatible: requires {overlay.precision} precision, max {overlay.max_layers} layers"


def verify_overlay_compatibility(fusecfg: FuseCfg, overlay: OverlayManifest) -> tuple[bool, str]:
    """Verify that a .fusecfg is compatible with a given overlay.

    Checks datapath width, layer count, and precision match.
    Returns (is_compatible, error_message).
    """
    errors = []

    if fusecfg.datapath_width != 8 and fusecfg.datapath_width != 4:
        errors.append(f"Unsupported datapath width: {fusecfg.datapath_width} (expected 4 or 8)")

    if fusecfg.layer_count > overlay.max_layers:
        errors.append(f"Layer count {fusecfg.layer_count} exceeds overlay max {overlay.max_layers}")

    if fusecfg.precision not in overlay.precision:
        errors.append(f"Precision '{fusecfg.precision}' not supported by overlay '{overlay.name}' (supports {overlay.precision})")

    if errors:
        return False, "; ".join(errors)
    return True, "Compatible"


class OverlayStateManager:
    """Persist the current overlay type to a local state file."""

    STATE_FILE = "overlay_state.json"

    def __init__(self, state_dir: Path | None = None):
        self.state_dir = state_dir or Path.home() / ".tpt-crucible"
        self.state_path = self.state_dir / self.STATE_FILE

    def save(self, overlay_name: str, board: str) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        import time as _time
        data = {
            "current_overlay": overlay_name,
            "board": board,
            "loaded_at": _time.time(),
        }
        self.state_path.write_text(json.dumps(data, indent=2))

    def load(self) -> dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {"current_overlay": "", "board": "", "loaded_at": 0.0}

    def get_current_overlay(self) -> str:
        return self.load().get("current_overlay", "")

    def clear(self) -> None:
        if self.state_path.exists():
            self.state_path.unlink()
