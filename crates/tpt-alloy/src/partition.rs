use crate::topology::Topology;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PartitionConfig {
    pub topology: Topology,
    pub max_layers_per_node: usize,
    pub minimize_cross_node_edges: bool,
}

impl Default for PartitionConfig {
    fn default() -> Self {
        Self {
            topology: Topology::Grid2D { rows: 4, cols: 4 },
            max_layers_per_node: 4,
            minimize_cross_node_edges: true,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Partition {
    pub node_id: usize,
    pub assigned_layers: Vec<usize>,
    pub cross_node_edges: Vec<CrossEdge>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CrossEdge {
    pub from_node: usize,
    pub to_node: usize,
    pub tensor_name: String,
}

pub fn partition_model(layer_count: usize, config: &PartitionConfig) -> Vec<Partition> {
    let node_count = config.topology.node_count();
    let mut partitions: Vec<Partition> = (0..node_count)
        .map(|id| Partition {
            node_id: id,
            assigned_layers: Vec::new(),
            cross_node_edges: Vec::new(),
        })
        .collect();

    for layer_id in 0..layer_count {
        let node_idx = layer_id % node_count;
        partitions[node_idx].assigned_layers.push(layer_id);
    }

    partitions
}
