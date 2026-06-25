"""Tests for Natural Language config module."""

from tpt_catalyst.nl_config import (
    LLMProviderConfig, TopologyRequest, TopologyResponse,
    NLConfigProvider,
)


class TestLLMProviderConfig:
    def test_not_configured(self):
        config = LLMProviderConfig()
        assert not config.is_configured

    def test_configured(self):
        config = LLMProviderConfig(provider_type="openrouter", api_key="sk-test")
        assert config.is_configured

    def test_configured_with_endpoint(self):
        config = LLMProviderConfig(provider_type="ollama", endpoint_url="http://localhost:11434")
        assert config.is_configured


class TestNLConfigProvider:
    def test_unavailable_returns_default(self):
        provider = NLConfigProvider()
        request = TopologyRequest(description="16 node ESP32 swarm", node_count=16)
        response = provider.generate_topology(request)
        assert response.topology_type == "grid2d"
        assert response.confidence == 0.0

    def test_topology_request(self):
        request = TopologyRequest(
            description="Star topology for 8 nodes",
            node_count=8,
            hardware_preference="esp32",
        )
        assert request.node_count == 8

    def test_topology_response(self):
        response = TopologyResponse(
            topology_type="star",
            node_count=8,
            layers_per_node=[[0], [1], [2], [3], [4], [5], [6], [7]],
            confidence=0.9,
            reasoning="Star topology minimizes latency for small clusters.",
        )
        assert response.confidence == 0.9
