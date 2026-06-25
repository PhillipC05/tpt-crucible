"""Tests for AI driver generator, topology advisor, and RTL assistant."""

from tpt_drivers.ai_gen import AIDriverGenerator, DatasheetInfo
from tpt_drivers.driver import DriverManifest


class TestAIDriverGenerator:
    def test_extract_from_text(self):
        gen = AIDriverGenerator()
        text = """
        ESP32-S3 Datasheet
        Supply voltage: 3.3V
        Clock speed: 240 MHz
        Flash: 16384 KB
        RAM: 512 KB
        Pin count: 44
        Features: WiFi, Bluetooth, UART, SPI, I2C, GPIO, USB
        """
        info = gen.extract_from_text(text)
        assert info.clock_speed_mhz == 240
        assert info.flash_size_kb == 16384
        assert info.ram_size_kb == 512
        assert info.pin_count == 44
        assert "WiFi" in info.peripherals
        assert "UART" in info.peripherals

    def test_generate_manifest(self):
        gen = AIDriverGenerator()
        info = DatasheetInfo(
            chip_name="ESP32-S3",
            clock_speed_mhz=240,
            flash_size_kb=16384,
            peripherals=["WiFi", "UART"],
        )
        manifest = gen.generate_manifest(info, "esp32-s3")
        assert manifest.name == "esp32-s3"
        assert manifest.hardware_type == "mcu"
        assert manifest.flash_protocol == "ota_wifi"
        assert manifest.synthesis.max_clock_mhz == 240

    def test_parse_llm_response(self):
        gen = AIDriverGenerator()
        response = '{"chip_name": "RP2040", "pin_count": 40, "flash_size_kb": 2048}'
        info = gen.parse_llm_response(response)
        assert info.chip_name == "RP2040"
        assert info.pin_count == 40


class TestTopologyAdvisor:
    def test_recommend(self):
        from tpt_alloy.ai_topology import AITopologyAdvisor, TopologyConstraints
        advisor = AITopologyAdvisor()
        constraints = TopologyConstraints(node_count=16, latency_budget_ms=10, power_budget_mw=5000)
        recs = advisor.recommend(layer_count=12, tensor_shapes=[[4096, 4096]], constraints=constraints)
        assert len(recs) == 4
        assert recs[0].score >= recs[-1].score
        assert all(r.node_count == 16 for r in recs)

    def test_recommendation_has_reasoning(self):
        from tpt_alloy.ai_topology import AITopologyAdvisor, TopologyConstraints
        advisor = AITopologyAdvisor()
        constraints = TopologyConstraints(node_count=8)
        recs = advisor.recommend(layer_count=6, tensor_shapes=[], constraints=constraints)
        assert all(len(r.reasoning) > 0 for r in recs)


class TestAIRtlAssistant:
    def test_analyze_pattern(self):
        from tpt_fusion.ai_rtl import AIRtlAssistant, ComputePattern
        assistant = AIRtlAssistant()
        patterns = [
            ComputePattern(layer_type="matmul", input_shape=[4096, 4096], output_shape=[4096, 4096]),
        ]
        analysis = assistant.analyze_pattern(patterns)
        assert analysis["total_macs"] == 4096 * 4096
        assert analysis["pattern_count"] == 1

    def test_generate_candidates(self):
        from tpt_fusion.ai_rtl import AIRtlAssistant, ComputePattern
        assistant = AIRtlAssistant()
        patterns = [
            ComputePattern(layer_type="matmul", input_shape=[1024, 1024], dtype="int8"),
        ]
        candidates = assistant.generate_candidates(patterns)
        assert len(candidates) == 3
        assert candidates[0].confidence >= candidates[-1].confidence
        assert "module tpt_mac_array" in candidates[0].verilog_code

    def test_resource_constraint(self):
        from tpt_fusion.ai_rtl import AIRtlAssistant, ComputePattern
        assistant = AIRtlAssistant()
        patterns = [
            ComputePattern(layer_type="matmul", input_shape=[64, 64], dtype="int8"),
        ]
        board = {"max_dsp_slices": 10, "max_luts": 1000}
        candidates = assistant.generate_candidates(patterns, board_resources=board)
        low_resource = [c for c in candidates if c.confidence < 0.5]
        assert len(low_resource) > 0
