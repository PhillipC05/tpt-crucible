use pyo3::prelude::*;
use std::path::PathBuf;
use tpt_catalyst::TptIr;

#[pyfunction]
fn ingest_model(path: String) -> PyResult<String> {
    let p = PathBuf::from(&path);
    let ir = tpt_catalyst::ingest::ingest_model(&p)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
    ir.to_json()
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
fn fuse_ops(ir_json: String) -> PyResult<String> {
    let mut ir = TptIr::from_json(&ir_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    tpt_catalyst::optimizer::fuse_sequential_ops(&mut ir);
    ir.to_json()
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
fn parse_ir(json: String) -> PyResult<String> {
    let _ir = TptIr::from_json(&json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    Ok("ok".into())
}

#[pymodule]
fn tpt_catalyst_python(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(ingest_model, m)?)?;
    m.add_function(wrap_pyfunction!(fuse_ops, m)?)?;
    m.add_function(wrap_pyfunction!(parse_ir, m)?)?;
    Ok(())
}
