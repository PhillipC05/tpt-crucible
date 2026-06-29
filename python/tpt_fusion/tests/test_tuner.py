"""Tests for synthesis tuner, compile estimator, validation prompts, bandwidth partition."""

from tpt_fusion.synthesis_tuner import SynthesisTuner, SynthParams, SynthResult
from tpt_fusion.compile_estimator import CompileEstimator, CompileEstimate, JobRecord
from tpt_catalyst.validation_prompts import PromptSuiteGenerator, PromptSuite, BUILTIN_PROMPTS
from tpt_alloy.bandwidth_partition import BandwidthEstimator, WeightedGraph, EdgeWeight


class TestSynthesisTuner:
    def test_predict_no_history(self):
        tuner = SynthesisTuner()
        params = tuner.predict_params({"total_ops": 1000})
        assert params.yosys_strategy == "area"

    def test_log_and_predict(self):
        tuner = SynthesisTuner()
        tuner.log_job(SynthResult(
            params=SynthParams(yosys_strategy="speed"),
            timing_slack_ns=0.5,
            lut_utilization=0.8,
            dsp_utilization=0.6,
            duration_s=120,
            model_shape={"total_ops": 1000},
        ))
        params = tuner.predict_params({"total_ops": 1000})
        assert params.yosys_strategy == "speed"

    def test_stats(self):
        tuner = SynthesisTuner()
        tuner.log_job(SynthResult(
            params=SynthParams(), timing_slack_ns=1.0,
            lut_utilization=0.5, dsp_utilization=0.3, duration_s=60,
        ))
        stats = tuner.get_stats()
        assert stats["jobs"] == 1


class TestCompileEstimator:
    def test_estimate_no_history(self):
        estimator = CompileEstimator()
        estimate = estimator.estimate(model_ops=1_000_000, board="alveo_u250")
        assert estimate.estimated_minutes > 0
        assert estimate.confidence_low < estimate.confidence_high

    def test_estimate_with_history(self):
        estimator = CompileEstimator()
        estimator.log_job(JobRecord(
            model_ops=1_000_000, tensor_shapes=[4096, 4096],
            board="alveo_u250", synthesis_mode="full", duration_minutes=45,
        ))
        estimate = estimator.estimate(model_ops=1_000_000, board="alveo_u250")
        assert estimate.estimated_minutes == 45.0

    def test_estimate_to_dict(self):
        estimator = CompileEstimator()
        estimate = estimator.estimate(model_ops=500_000, board="alveo_u250")
        d = estimate.to_dict()
        assert "estimated_minutes" in d
        assert "confidence_range" in d


class TestPromptSuite:
    def test_builtin_prompts(self):
        assert len(BUILTIN_PROMPTS) >= 15

    def test_generator(self, tmp_path):
        gen = PromptSuiteGenerator(cache_dir=tmp_path)
        suite = gen.get_suite("test/model", "code")
        assert len(suite.prompts) >= 20
        assert suite.domain == "code"

    def test_cache_hit(self, tmp_path):
        gen = PromptSuiteGenerator(cache_dir=tmp_path)
        s1 = gen.get_suite("test/model")
        s2 = gen.get_suite("test/model")
        assert len(s1.prompts) == len(s2.prompts)

    def test_combine_suites(self):
        gen = PromptSuiteGenerator()
        s1 = gen.get_suite("m1", "code")
        s2 = gen.get_suite("m2", "math")
        combined = gen.combine_suites(s1, s2)
        assert len(combined) >= 25


class TestBandwidthEstimator:
    def test_estimate_edge_volume(self):
        estimator = BandwidthEstimator()
        volume = estimator.estimate_edge_volume([4096, 4096], "float32", batch_size=1)
        assert volume == 4096 * 4096 * 4

    def test_build_weighted_graph(self):
        estimator = BandwidthEstimator()
        edges = [(0, 1, "x", [1024, 1024], "float32")]
        graph = estimator.build_weighted_graph(node_count=2, edges=edges)
        assert graph.total_bytes == 1024 * 1024 * 4

    def test_compute_partition_cost(self):
        estimator = BandwidthEstimator()
        edges = [(0, 1, "x", [100, 100], "float32")]
        graph = estimator.build_weighted_graph(2, edges)
        partition = {0: [0], 1: [1]}
        cost = estimator.compute_partition_cost(partition, graph)
        assert cost > 0

    def test_same_partition_zero_cost(self):
        estimator = BandwidthEstimator()
        edges = [(0, 1, "x", [100, 100], "float32")]
        graph = estimator.build_weighted_graph(2, edges)
        partition = {0: [0, 1]}
        cost = estimator.compute_partition_cost(partition, graph)
        assert cost == 0
