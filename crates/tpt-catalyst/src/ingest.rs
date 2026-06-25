use crate::ir::{TptIr, TptIrError};
use std::path::Path;

pub enum ModelFormat {
    PyTorch,
    Onnx,
    TensorFlow,
}

impl ModelFormat {
    pub fn detect(path: &Path) -> Result<Self, TptIrError> {
        let ext = path
            .extension()
            .and_then(|e| e.to_str())
            .ok_or_else(|| TptIrError::UnsupportedFormat("no extension".into()))?;

        match ext {
            "pt" | "pth" | "bin" => Ok(Self::PyTorch),
            "onnx" => Ok(Self::Onnx),
            "pb" | "savedmodel" => Ok(Self::TensorFlow),
            _ => Err(TptIrError::UnsupportedFormat(ext.into())),
        }
    }
}

pub fn ingest_model(path: &Path) -> Result<TptIr, TptIrError> {
    let format = ModelFormat::detect(path)?;
    let name = path
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("unknown")
        .to_string();

    match format {
        ModelFormat::PyTorch => ingest_pytorch(path, name),
        ModelFormat::Onnx => ingest_onnx(path, name),
        ModelFormat::TensorFlow => ingest_tensorflow(path, name),
    }
}

fn ingest_pytorch(_path: &Path, name: String) -> Result<TptIr, TptIrError> {
    let ir = TptIr::new(name, "pytorch".into());
    tracing::info!("PyTorch ingestion stub — real implementation requires Python bridge");
    Ok(ir)
}

fn ingest_onnx(_path: &Path, name: String) -> Result<TptIr, TptIrError> {
    let ir = TptIr::new(name, "onnx".into());
    tracing::info!("ONNX ingestion stub — real implementation requires onnxruntime bindings");
    Ok(ir)
}

fn ingest_tensorflow(_path: &Path, name: String) -> Result<TptIr, TptIrError> {
    let ir = TptIr::new(name, "tensorflow".into());
    tracing::info!(
        "TensorFlow ingestion stub — real implementation requires TF saved model parser"
    );
    Ok(ir)
}
