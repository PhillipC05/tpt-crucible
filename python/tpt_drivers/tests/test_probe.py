"""Tests for device probing, Spark benchmark, and NL topology."""

from tpt_drivers.probe import DeviceProbe, DetectedDevice, DriverLookup
from tpt_catalyst.spark_benchmark import SparkBenchmark, SparkBaseline, BenchmarkComparison
from tpt_mosaic.nl_topology import NLTopologyGenerator, TopologyRequest, TopologyResponse


class TestDeviceProbe:
    def test_probe_returns_list(self):
        probe = DeviceProbe()
        devices = probe.probe_usb_devices()
        assert isinstance(devices, list)

    def test_identify_driver(self):
        probe = DeviceProbe()
        device = DetectedDevice(port="COM3", description="USB-SERIAL", vid="1A86")
        identified = probe.identify_driver(device)
        assert identified.driver_name == "ch340"

    def test_auto_detect(self):
        probe = DeviceProbe()
        devices = probe.auto_detect_all()
        assert isinstance(devices, list)

    def test_detected_device_to_dict(self):
        device = DetectedDevice(port="COM3", description="ESP32", vid="303A")
        d = device.to_dict()
        assert d["port"] == "COM3"
        assert d["vid"] == "303A"


class TestSparkBenchmark:
    def test_compare(self):
        bench = SparkBenchmark()
        bench._baselines["tinyllama"] = SparkBaseline(
            model_name="tinyllama", tokens_per_second=50.0, hardware="CPU",
        )
        comparison = bench.compare("tinyllama", 120.0, "alloy")
        assert comparison is not None
        assert comparison.speedup == 2.4

    def test_compare_unknown_model(self):
        bench = SparkBenchmark()
        comparison = bench.compare("unknown", 100.0, "alloy")
        assert comparison is None

    def test_comparison_to_dict(self):
        spark = SparkBaseline(model_name="m", tokens_per_second=50.0, hardware="GPU")
        crucible = SparkBaseline(model_name="m", tokens_per_second=100.0, hardware="alloy")
        comp = BenchmarkComparison(spark=spark, crucible=crucible)
        d = comp.to_dict()
        assert "speedup" in d
        assert d["speedup"] == 2.0


class TestNLTopology:
    def test_generate_grid(self):
        gen = NLTopologyGenerator()
        request = TopologyRequest(description="16 node grid topology", node_count=16)
        response = gen.generate(request)
        assert response.topology_type == "grid2d"
        assert response.node_count == 16

    def test_generate_star(self):
        gen = NLTopologyGenerator()
        request = TopologyRequest(description="8 node star topology", node_count=8)
        response = gen.generate(request)
        assert response.topology_type == "star"

    def test_extract_node_count(self):
        gen = NLTopologyGenerator()
        count = gen._extract_node_count("use 32 nodes in a mesh")
        assert count == 32

    def test_generate_llm_prompt(self):
        gen = NLTopologyGenerator()
        request = TopologyRequest(description="16 node grid", node_count=16)
        prompt = gen.generate_llm_prompt(request)
        assert "16" in prompt
        assert "grid" in prompt
