use pyo3::prelude::*;
use tpt_alloy::firmware::generate_firmware;
use tpt_alloy::partition::{partition_model, Partition};
use tpt_alloy::{FirmwareTarget, PartitionConfig, Topology};

#[pyfunction]
fn partition_swarm(layer_count: usize, node_count: usize) -> PyResult<String> {
    let config = PartitionConfig {
        topology: Topology::Grid2D {
            rows: (node_count as f64).sqrt().ceil() as usize,
            cols: (node_count as f64).sqrt().ceil() as usize,
        },
        ..Default::default()
    };
    let partitions = partition_model(layer_count, &config);
    serde_json::to_string_pretty(&partitions)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
fn generate_node_firmware(partition_json: String, target: String) -> PyResult<String> {
    let partition: Partition = serde_json::from_str(&partition_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let fw_target = match target.as_str() {
        "esp32" => FirmwareTarget::Esp32,
        "rp2040" => FirmwareTarget::Rp2040,
        "riscv" => FirmwareTarget::RiscV,
        _ => {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "unknown target: {target}"
            )))
        }
    };
    let bundle = generate_firmware(&partition, &fw_target);
    serde_json::to_string_pretty(&bundle)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[pymodule]
fn tpt_alloy_python(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(partition_swarm, m)?)?;
    m.add_function(wrap_pyfunction!(generate_node_firmware, m)?)?;
    Ok(())
}
