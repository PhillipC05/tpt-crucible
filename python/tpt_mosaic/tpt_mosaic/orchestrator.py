"""Mosaic orchestrator — reads annotations and calls relevant module per partition."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from pathlib import Path

from .partition import PartitionPlan, HardwareTarget, LayerAssignment
from .bridge import InterHardwareBridge, BridgeConfig


@dataclass
class CompilationResult:
    """Result of a Mosaic compilation pass."""
    success: bool
    targets_compiled: list[str]
    artifacts: dict[str, Path]
    bridge_files: list[Path]
    errors: list[str]


class MosaicOrchestrator:
    """Orchestrates compilation across multiple hardware backends.

    Reads layer annotations from PartitionPlan, dispatches to the
    appropriate module (Fusion/Alloy/Element), and generates
    inter-hardware communication glue.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.bridge = InterHardwareBridge()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def compile(
        self,
        plan: PartitionPlan,
        tptir_path: Path | None = None,
    ) -> CompilationResult:
        """Compile a partition plan across multiple hardware targets."""
        targets = plan.targets_used
        artifacts = {}
        errors = []
        bridge_files = []

        for target in targets:
            layers = plan.layers_for_target(target)
            target_dir = self.output_dir / target.value
            target_dir.mkdir(exist_ok=True)

            try:
                if target == HardwareTarget.FPGA:
                    artifacts[target.value] = self._compile_fusion(layers, target_dir)
                elif target == HardwareTarget.SWARM:
                    artifacts[target.value] = self._compile_alloy(layers, target_dir)
                elif target == HardwareTarget.ANALOG:
                    artifacts[target.value] = self._compile_element(layers, target_dir)
                elif target == HardwareTarget.CIM:
                    artifacts[target.value] = self._compile_silicon(layers, target_dir)
                elif target == HardwareTarget.NEUROMORPHIC:
                    artifacts[target.value] = self._compile_pulse(layers, target_dir)
                elif target == HardwareTarget.PHOTONIC:
                    artifacts[target.value] = self._compile_photon(layers, target_dir)
            except Exception as e:
                errors.append(f"{target.value}: {e}")

        bridge_files = self._generate_bridges(plan)

        return CompilationResult(
            success=len(errors) == 0,
            targets_compiled=list(artifacts.keys()),
            artifacts=artifacts,
            bridge_files=bridge_files,
            errors=errors,
        )

    def _compile_fusion(self, layers: list[LayerAssignment], output_dir: Path) -> Path:
        config_json = {
            "target": "fpga",
            "layers": [l.to_dict() for l in layers],
        }
        out = output_dir / "fusion_config.json"
        out.write_text(str(config_json))
        return out

    def _compile_alloy(self, layers: list[LayerAssignment], output_dir: Path) -> Path:
        config_json = {
            "target": "swarm",
            "layers": [l.to_dict() for l in layers],
        }
        out = output_dir / "alloy_config.json"
        out.write_text(str(config_json))
        return out

    def _compile_element(self, layers: list[LayerAssignment], output_dir: Path) -> Path:
        config_json = {
            "target": "analog",
            "layers": [l.to_dict() for l in layers],
        }
        out = output_dir / "element_config.json"
        out.write_text(str(config_json))
        return out

    def _compile_silicon(self, layers: list[LayerAssignment], output_dir: Path) -> Path:
        config_json = {
            "target": "cim",
            "layers": [l.to_dict() for l in layers],
        }
        out = output_dir / "silicon_config.json"
        out.write_text(str(config_json))
        return out

    def _compile_pulse(self, layers: list[LayerAssignment], output_dir: Path) -> Path:
        config_json = {
            "target": "neuromorphic",
            "layers": [l.to_dict() for l in layers],
        }
        out = output_dir / "pulse_config.json"
        out.write_text(str(config_json))
        return out

    def _compile_photon(self, layers: list[LayerAssignment], output_dir: Path) -> Path:
        config_json = {
            "target": "photonic",
            "layers": [l.to_dict() for l in layers],
            "experimental": True,
        }
        out = output_dir / "photon_config.json"
        out.write_text(str(config_json))
        return out

    def _generate_bridges(self, plan: PartitionPlan) -> list[Path]:
        bridge_files = []
        targets = list(plan.targets_used)

        for i, src in enumerate(targets):
            for dst in targets[i + 1:]:
                src_layers = plan.layers_for_target(src)
                if src_layers:
                    code = self.bridge.generate_bridge_code(
                        src, dst,
                        tensor_name=f"{src.value}_to_{dst.value}",
                    )
                    bridge_dir = self.output_dir / "bridges"
                    bridge_dir.mkdir(exist_ok=True)
                    bridge_path = bridge_dir / f"bridge_{src.value}_{dst.value}.c"
                    bridge_path.write_text(code)
                    bridge_files.append(bridge_path)

        return bridge_files
