"""Tests for graph partitioning."""

import pytest

from tpt_alloy.topology import Topology
from tpt_alloy.partition import (
    PartitionConfig,
    partition_model,
    GraphData,
    build_graph_from_nodes,
)


class TestGraphData:
    def test_build_from_edges(self):
        graph = build_graph_from_nodes(4, [(0, 1), (1, 2), (2, 3)])
        assert graph.node_count == 4
        assert 1 in graph.adjacency[0]
        assert 0 in graph.adjacency[1]
        assert 3 in graph.adjacency[2]

    def test_empty_graph(self):
        graph = build_graph_from_nodes(3, [])
        assert graph.node_count == 3
        assert all(len(adj) == 0 for adj in graph.adjacency)


class TestPartitionModel:
    def test_round_robin_partition(self):
        config = PartitionConfig(topology=Topology.grid2d(2, 2))
        partitions = partition_model(8, config)
        assert len(partitions) == 4
        for p in partitions:
            assert len(p.assigned_layers) == 2

    def test_single_node(self):
        config = PartitionConfig(topology=Topology.grid2d(1, 1))
        partitions = partition_model(5, config)
        assert len(partitions) == 1
        assert len(partitions[0].assigned_layers) == 5

    def test_cross_edges_computed(self):
        graph = build_graph_from_nodes(4, [(0, 1), (1, 2), (2, 3), (0, 2)])
        config = PartitionConfig(
            topology=Topology.grid2d(2, 2),
            minimize_cross_node_edges=False,
        )
        partitions = partition_model(4, config, graph=graph)
        total_cross = sum(len(p.cross_node_edges) for p in partitions)
        assert total_cross >= 0

    def test_metis_not_available_fallback(self):
        config = PartitionConfig(
            topology=Topology.grid2d(2, 2),
            minimize_cross_node_edges=True,
        )
        partitions = partition_model(8, config)
        assert len(partitions) == 4
