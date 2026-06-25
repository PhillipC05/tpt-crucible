"""Recipe system — pre-configured deployment bundles."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json
from pathlib import Path

from .driver import DriverManifest, PowerProfile, SynthesisConstraints, BomEntry
from .registry import DriverRegistry


@dataclass
class RecipeStep:
    name: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Recipe:
    name: str
    description: str
    model_id: str
    hardware_type: str
    node_count: int
    topology: str
    steps: list[RecipeStep]
    drivers: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "model_id": self.model_id,
            "hardware_type": self.hardware_type,
            "node_count": self.node_count,
            "topology": self.topology,
            "drivers": self.drivers,
            "steps": [{"name": s.name, "action": s.action, "params": s.params} for s in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Recipe:
        steps = [RecipeStep(name=s["name"], action=s["action"], params=s.get("params", {})) for s in data.get("steps", [])]
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            model_id=data.get("model_id", ""),
            hardware_type=data.get("hardware_type", ""),
            node_count=data.get("node_count", 16),
            topology=data.get("topology", "grid2d"),
            steps=steps,
            drivers=data.get("drivers", []),
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> Recipe:
        return cls.from_dict(json.loads(path.read_text()))


BUILTIN_RECIPES: list[Recipe] = [
    Recipe(
        name="tinyllama-esp32-16node",
        description="TinyLlama 1.1B on 16x ESP32 swarm (4x4 grid)",
        model_id="TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF",
        hardware_type="swarm",
        node_count=16,
        topology="grid2d",
        drivers=["esp32-devkit"],
        steps=[
            RecipeStep(name="ingest", action="tpt-catalyst ingest --spark-model tinyllama"),
            RecipeStep(name="optimize", action="tpt-catalyst optimize model.tptir"),
            RecipeStep(name="check", action="tpt-catalyst check model.tptir --target alloy"),
            RecipeStep(name="quantize", action="tpt-catalyst ingest model.gguf --quantize int8 --target alloy"),
            RecipeStep(name="partition", action="tpt-alloy partition model.tptir --topology grid2d --nodes 16"),
            RecipeStep(name="compile", action="tpt-alloy compile model.tptir --target esp32"),
        ],
    ),
    Recipe(
        name="llama2-7b-alveo",
        description="Llama 2 7B on Xilinx Alveo U280 FPGA",
        model_id="TheBloke/Llama-2-7B-Chat-GGUF",
        hardware_type="fpga",
        node_count=1,
        topology="single",
        drivers=["xilinx_alveo_u280"],
        steps=[
            RecipeStep(name="ingest", action="tpt-catalyst ingest model.gguf"),
            RecipeStep(name="optimize", action="tpt-catalyst optimize model.tptir"),
            RecipeStep(name="quantize", action="tpt-catalyst ingest model.gguf --quantize int8 --target fusion"),
            RecipeStep(name="check", action="tpt-catalyst check model.tptir --target fusion"),
            RecipeStep(name="compile", action="tpt-fusion compile model.tptir --board xilinx_alveo_u280"),
        ],
    ),
    Recipe(
        name="analog-3layer",
        description="3-layer analog neural network design",
        model_id="custom",
        hardware_type="analog",
        node_count=1,
        topology="single",
        steps=[
            RecipeStep(name="ingest", action="tpt-catalyst ingest model.pt"),
            RecipeStep(name="check", action="tpt-catalyst check model.tptir --target element"),
            RecipeStep(name="simulate", action="tpt-element simulate --weights weights.npy"),
            RecipeStep(name="export", action="tpt-element export --output circuit.kicad_pcb"),
        ],
    ),
]


class RecipeManager:
    """Manage deployment recipes."""

    def __init__(self, recipes_dir: Path | None = None):
        self.recipes_dir = recipes_dir or Path.home() / ".tpt-crucible" / "recipes"
        self.recipes_dir.mkdir(parents=True, exist_ok=True)
        self._load_custom_recipes()

    def _load_custom_recipes(self) -> None:
        self.recipes = list(BUILTIN_RECIPES)
        for f in self.recipes_dir.glob("*.json"):
            try:
                self.recipes.append(Recipe.load(f))
            except Exception:
                pass

    def list_recipes(self) -> list[Recipe]:
        return self.recipes

    def get_recipe(self, name: str) -> Recipe | None:
        return next((r for r in self.recipes if r.name == name), None)

    def search(self, query: str) -> list[Recipe]:
        q = query.lower()
        return [r for r in self.recipes if q in r.name.lower() or q in r.description.lower()]

    def save_recipe(self, recipe: Recipe) -> Path:
        path = self.recipes_dir / f"{recipe.name}.json"
        recipe.save(path)
        self.recipes.append(recipe)
        return path

    def delete_recipe(self, name: str) -> bool:
        path = self.recipes_dir / f"{name}.json"
        if path.exists():
            path.unlink()
            self.recipes = [r for r in self.recipes if r.name != name]
            return True
        return False
