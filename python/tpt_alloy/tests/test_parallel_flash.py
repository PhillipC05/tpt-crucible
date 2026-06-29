"""Tests for parallel flashing, SiL tuner, SPICE pipeline, and LLM diagnosis."""

from tpt_alloy.parallel_flash import ParallelFlasher, FlashJob, FlashTarget
from tpt_alloy.sil_tuner import SiLTuner, TunableParams, TuneResult
from tpt_element.spice_pipeline import SpiceSweepOrchestrator, SweepConfig
from tpt_catalyst.llm_diagnosis import (
    LLMDiagnosisEngine, DiagnosisRequest, DiagnosisResponse,
)


class TestParallelFlasher:
    def test_estimate_time(self):
        flasher = ParallelFlasher(flash_time_per_node_s=2.0, parallel_workers=4)
        time_s = flasher.estimate_time(node_count=16)
        assert time_s == 8.0

    def test_create_job(self):
        flasher = ParallelFlasher()
        job = flasher.create_job("firmware.bin", ports=["COM3", "COM4"])
        assert job.total_nodes == 2
        assert job.mode == "usb"

    def test_create_ota_job(self):
        flasher = ParallelFlasher()
        job = flasher.create_ota_job("fw.bin", ip_addresses=["192.168.1.1", "192.168.1.2"])
        assert job.total_nodes == 2
        assert job.mode == "ota"

    def test_simulate_flash(self):
        flasher = ParallelFlasher()
        job = flasher.create_job("fw.bin", ports=["COM3"])
        result = flasher.simulate_flash(job)
        assert result.completed_nodes == 1
        assert result.overall_progress == 100.0

    def test_job_to_dict(self):
        flasher = ParallelFlasher()
        job = flasher.create_job("fw.bin", ports=["COM3", "COM4"])
        d = job.to_dict()
        assert "total_nodes" in d
        assert "overall_progress" in d


class TestSiLTuner:
    def test_sweep(self):
        tuner = SiLTuner(param_space={
            "wifi_message_size": [512, 1024],
            "batch_size": [4, 8],
            "retry_count": [1, 3],
            "uart_baud_rate": [115200],
        })
        results = tuner.sweep(memory_budget_kb=1024)
        assert len(results) > 0
        assert results[0].p99_latency_ms <= results[-1].p99_latency_ms

    def test_select_best(self):
        tuner = SiLTuner()
        results = tuner.sweep(memory_budget_kb=256)
        best = tuner.select_best(results)
        assert best is not None

    def test_bake_to_firmware(self):
        tuner = SiLTuner()
        params = TunableParams(wifi_message_size=2048, batch_size=16)
        code = tuner.bake_to_firmware(params)
        assert "WIFI_MSG_SIZE 2048" in code
        assert "BATCH_SIZE 16" in code


class TestSpiceSweep:
    def test_sweep(self):
        config = SweepConfig(
            tolerances=[0.05],
            temperature_steps=2,
            voltage_steps=2,
        )
        sweeper = SpiceSweepOrchestrator(config)
        results = sweeper.run_sweep()
        assert len(results) == 4

    def test_pass_rate(self):
        config = SweepConfig(tolerances=[0.01], temperature_steps=1, voltage_steps=1)
        sweeper = SpiceSweepOrchestrator(config)
        sweeper.run_sweep()
        rate = sweeper.get_pass_rate()
        assert 0.0 <= rate <= 1.0

    def test_failure_modes(self):
        config = SweepConfig(tolerances=[0.10], temperature_steps=3, voltage_steps=3)
        sweeper = SpiceSweepOrchestrator(config)
        sweeper.run_sweep()
        modes = sweeper.get_failure_modes()
        assert isinstance(modes, dict)


class TestLLMDiagnosis:
    def test_unconfigured_returns_fallback(self):
        engine = LLMDiagnosisEngine()
        request = DiagnosisRequest(
            error_type="timing_failure",
            tool="yosys",
            stderr="ERROR: timing failed",
            model_info={"layers": 22},
            target_board="alveo_u250",
            synthesis_flags={},
        )
        response = engine.diagnose(request)
        assert "timing" in response.root_cause.lower()

    def test_to_prompt(self):
        request = DiagnosisRequest(
            error_type="resource_overflow",
            tool="yosys",
            stderr="ERROR: overflow",
            model_info={"layers": 32},
            target_board="alveo",
            synthesis_flags={},
        )
        prompt = request.to_prompt()
        assert "yosys" in prompt
        assert "resource_overflow" in prompt

    def test_cache(self):
        engine = LLMDiagnosisEngine()
        request = DiagnosisRequest(
            error_type="timing_failure", tool="yosys", stderr="err",
            model_info={}, target_board="alveo", synthesis_flags={},
        )
        r1 = engine.diagnose(request)
        r2 = engine.diagnose(request)
        assert r1 is r2
