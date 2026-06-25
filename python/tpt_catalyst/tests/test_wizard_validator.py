"""Tests for wizard, validator, OTA, and diagnostics."""

from tpt_catalyst.validator import AccuracyValidator, ValidationResult, STANDARD_PROMPTS
from tpt_alloy.ota import OtaManager, OtaManifest, NodeFlashStatus
from tpt_catalyst.diagnostics import (
    run_diagnostics, AlloyDiagnostics, FusionDiagnostics, ElementDiagnostics,
    DiagnosticReport,
)


class TestAccuracyValidator:
    def test_validate_matching(self):
        validator = AccuracyValidator()
        refs = ["hello world", "foo bar"]
        hws = ["hello world", "foo bar"]
        result = validator.validate(refs, hws)
        assert result.overall_similarity == 1.0
        assert result.grade == "A"

    def test_validate_partial(self):
        validator = AccuracyValidator()
        refs = ["the quick brown fox", "hello world test"]
        hws = ["quick fox brown", "hello test"]
        result = validator.validate(refs, hws)
        assert 0.0 < result.overall_similarity < 1.0

    def test_validate_empty(self):
        validator = AccuracyValidator()
        result = validator.validate([], [])
        assert result.overall_similarity == 0.0

    def test_standard_prompts(self):
        assert len(STANDARD_PROMPTS) >= 10

    def test_to_dict(self):
        validator = AccuracyValidator()
        result = validator.validate(["a"], ["a"])
        d = result.to_dict()
        assert "overall_similarity" in d
        assert "grade" in d


class TestOtaManager:
    def test_compute_diff(self):
        manager = OtaManager()
        old = {0: b"firmware_v1", 1: b"firmware_v1", 2: b"firmware_v1"}
        new = {0: b"firmware_v2", 1: b"firmware_v1", 2: b"firmware_v2"}
        manifest = manager.compute_diff(old, new)
        assert manifest.changed_nodes == 2
        assert manifest.unchanged_nodes == 1

    def test_create_patch_manifest(self):
        manager = OtaManager()
        old = {0: b"old", 1: b"old"}
        new = {0: b"new", 1: b"old"}
        manifest = manager.compute_diff(old, new)
        patch = manager.create_patch_manifest(manifest)
        assert patch["changed_nodes"] == 1
        assert len(patch["patches"]) == 1

    def test_flash_nodes(self):
        manager = OtaManager()
        old = {0: b"old", 1: b"old"}
        new = {0: b"new", 1: b"old"}
        manifest = manager.compute_diff(old, new)
        statuses = manager.flash_nodes(manifest)
        assert len(statuses) == 2
        assert any(s.status == "done" for s in statuses)
        assert any(s.status == "skipped" for s in statuses)

    def test_manifest_to_dict(self):
        manager = OtaManager()
        manifest = manager.compute_diff({0: b"a"}, {0: b"b"})
        d = manifest.to_dict()
        assert "total_nodes" in d
        assert "update_percentage" in d


class TestDiagnostics:
    def test_alloy_diagnostics(self):
        report = AlloyDiagnostics().run(node_count=4)
        assert report.hardware_type == "alloy"
        assert len(report.results) == 4
        assert report.overall_status in ("pass", "warn")

    def test_fusion_diagnostics(self):
        report = FusionDiagnostics().run()
        assert report.hardware_type == "fusion"
        assert len(report.results) >= 2

    def test_element_diagnostics(self):
        report = ElementDiagnostics().run()
        assert report.hardware_type == "element"
        assert len(report.results) >= 2

    def test_run_diagnostics(self):
        for hw in ["alloy", "fusion", "element"]:
            report = run_diagnostics(hw)
            assert report.hardware_type == hw
            assert report.score >= 0

    def test_report_to_dict(self):
        report = run_diagnostics("fusion")
        d = report.to_dict()
        assert "results" in d
        assert "score" in d
