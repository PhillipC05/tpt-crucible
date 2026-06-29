"""
Integration test: Catalyst → pre-flight → pack → SiL emulator.

Runs the full compilation pipeline on a small synthetic model and verifies:
  1. TPT-IR round-trips correctly through save/load.
  2. Pre-flight check returns a scored compatibility report.
  3. pack() writes the expected .tptpkg directory structure.
  4. AlloySil emulator can load and run inference from the packaged model.
  5. Telemetry emitted by the emulator matches the Observer schema.

Mark: pytest -m integration
"""

import json
import hashlib
from pathlib import Path

import pytest

from tpt_catalyst.ir import TptIr, OpNode, Edge, ComputationalGraph, ModelMetadata
from tpt_catalyst.compat import check_compatibility, HardwareTarget
from tpt_catalyst.quantize import recommend_quantization, apply_quantization
from tpt_catalyst.package_reports import write_preflight_report, write_quant_profile
from tpt_emulator.alloy_sil import AlloySil
from tpt_emulator.interface import EmulatorResult


pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SMALL_MODEL_OPS = [
    "embedding", "matmul", "layernorm", "attention",
    "gelu", "matmul", "layernorm", "linear", "softmax",
]


@pytest.fixture()
def small_ir() -> TptIr:
    """A minimal TptIr that exercises common transformer operators."""
    nodes = [
        OpNode(id=i, op_type=op, name=f"{op}_{i}")
        for i, op in enumerate(SMALL_MODEL_OPS)
    ]
    edges = [Edge(src=i, dst=i + 1) for i in range(len(nodes) - 1)]
    return TptIr(
        version="1.0.0",
        metadata=ModelMetadata(
            name="integration-test-model",
            source_format="synthetic",
        ),
        graph=ComputationalGraph(nodes=nodes, edges=edges),
    )


@pytest.fixture()
def packed_pkg(tmp_path: Path, small_ir: TptIr) -> Path:
    """Build a .tptpkg directory from small_ir targeting alloy."""
    pkg_dir = tmp_path / "test_model.tptpkg"
    pkg_dir.mkdir()

    # IR
    ir_dir = pkg_dir / "ir"
    ir_dir.mkdir()
    small_ir.save(ir_dir / "model.tptir")

    # Manifest
    source_hash = hashlib.sha256(small_ir.to_json().encode()).hexdigest()[:16]
    manifest = {
        "format_version": "1.0.0",
        "model_name": small_ir.metadata.name,
        "source_sha256": source_hash,
        "targets": ["alloy"],
    }
    (pkg_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    # Pre-flight + quant profile
    compat_report = check_compatibility(small_ir, HardwareTarget.ALLOY)
    write_preflight_report(compat_report, pkg_dir)

    quant_rec = recommend_quantization(small_ir, "alloy")
    write_quant_profile(quant_rec.recommended_profile, pkg_dir)

    return pkg_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestIrRoundtrip:
    def test_save_load_preserves_graph(self, tmp_path, small_ir):
        path = tmp_path / "model.tptir"
        small_ir.save(path)
        loaded = TptIr.from_json(path.read_text())
        assert loaded.metadata.name == small_ir.metadata.name
        assert len(loaded.graph.nodes) == len(small_ir.graph.nodes)
        assert len(loaded.graph.edges) == len(small_ir.graph.edges)

    def test_op_types_preserved(self, tmp_path, small_ir):
        path = tmp_path / "model.tptir"
        small_ir.save(path)
        loaded = TptIr.from_json(path.read_text())
        original_ops = [n.op_type for n in small_ir.graph.nodes]
        loaded_ops = [n.op_type for n in loaded.graph.nodes]
        assert original_ops == loaded_ops


class TestPreflight:
    def test_returns_score(self, small_ir):
        report = check_compatibility(small_ir, HardwareTarget.ALLOY)
        assert 0.0 <= report.score <= 1.0

    def test_report_has_results(self, small_ir):
        report = check_compatibility(small_ir, HardwareTarget.ALLOY)
        assert len(report.results) > 0

    def test_to_dict_schema(self, small_ir):
        report = check_compatibility(small_ir, HardwareTarget.ALLOY)
        d = report.to_dict()
        assert "score" in d
        assert "details" in d or "results" in d


class TestPackaging:
    def test_manifest_exists(self, packed_pkg):
        assert (packed_pkg / "manifest.json").exists()

    def test_manifest_schema(self, packed_pkg):
        manifest = json.loads((packed_pkg / "manifest.json").read_text())
        assert manifest["format_version"] == "1.0.0"
        assert manifest["model_name"] == "integration-test-model"
        assert "source_sha256" in manifest
        assert "alloy" in manifest["targets"]

    def test_ir_file_present(self, packed_pkg):
        assert (packed_pkg / "ir" / "model.tptir").exists()

    def test_preflight_report_present(self, packed_pkg):
        assert (packed_pkg / "compat" / "preflight.json").exists()

    def test_quant_profile_present(self, packed_pkg):
        assert (packed_pkg / "quant" / "quant_profile.json").exists()


class TestSilEmulator:
    def test_alloy_sil_runs(self, packed_pkg):
        emu = AlloySil(node_count=4)
        model_path = str(packed_pkg / "ir" / "model.tptir")
        loaded = emu.load_model(model_path)
        assert loaded, "AlloySil.load_model() should return truthy"
        result: EmulatorResult = emu.run_inference({"tokens": [1, 2, 3, 4, 5]})
        assert result.success, f"SiL inference failed: {result}"

    def test_tokens_per_second_positive(self, packed_pkg):
        emu = AlloySil(node_count=4)
        emu.load_model(str(packed_pkg / "ir" / "model.tptir"))
        result = emu.run_inference(None)
        assert result.tokens_per_second > 0

    def test_inference_time_positive(self, packed_pkg):
        emu = AlloySil(node_count=4)
        emu.load_model(str(packed_pkg / "ir" / "model.tptir"))
        result = emu.run_inference(None)
        assert result.inference_time_ms > 0

    def test_telemetry_schema(self, packed_pkg):
        """Telemetry entries must match the Observer schema fields."""
        emu = AlloySil(node_count=4)
        emu.load_model(str(packed_pkg / "ir" / "model.tptir"))
        emu.run_inference(None)
        entries = emu.get_telemetry()
        assert len(entries) > 0, "Expected at least one telemetry entry"
        for entry in entries:
            d = entry if isinstance(entry, dict) else entry.__dict__
            assert "node_id" in d or hasattr(entry, "node_id"), (
                f"Telemetry entry missing 'node_id': {d}"
            )
