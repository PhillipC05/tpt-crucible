"""Tests for TPT Emulator module."""

from tpt_emulator.interface import EmulatorInterface, EmulatorResult, HardwareType
from tpt_emulator.alloy_sil import AlloySil
from tpt_emulator.fusion_sil import FusionSil
from tpt_emulator.element_sil import ElementSil


class TestEmulatorResult:
    def test_to_dict(self):
        result = EmulatorResult(success=True, inference_time_ms=10.5, tokens_per_second=100.0)
        d = result.to_dict()
        assert d["success"] is True
        assert d["inference_time_ms"] == 10.5


class TestAlloySil:
    def test_load_and_run(self):
        emu = AlloySil(node_count=4)
        assert emu.load_model("test.ptir")
        result = emu.run_inference(None)
        assert result.success
        assert result.tokens_per_second > 0

    def test_telemetry_collected(self):
        emu = AlloySil(node_count=2)
        emu.load_model("test.ptir")
        emu.run_inference(None)
        assert len(emu.get_telemetry()) >= 2


class TestFusionSil:
    def test_timing_estimate(self):
        emu = FusionSil(clock_mhz=200)
        emu.load_model("test.v")
        result = emu.run_inference(None)
        assert result.success
        assert result.metadata["mode"] == "timing_estimate"


class TestElementSil:
    def test_analog_simulation(self):
        emu = ElementSil(vdd=3.3, temperature_k=300)
        emu.load_model("test.spice")
        result = emu.run_inference(None)
        assert result.success
        assert result.metadata["vdd"] == 3.3
