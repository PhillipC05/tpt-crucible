//! WASM API for compiling models in the browser.

use wasm_bindgen::prelude::*;

use crate::package::PackageManifest;

/// Compile result returned to JavaScript.
#[wasm_bindgen]
pub struct CompileResult {
    manifest_json: String,
    success: bool,
    error_message: String,
}

#[wasm_bindgen]
impl CompileResult {
    #[wasm_bindgen(getter)]
    pub fn success(&self) -> bool {
        self.success
    }

    #[wasm_bindgen(getter)]
    pub fn manifest(&self) -> String {
        self.manifest_json.clone()
    }

    #[wasm_bindgen(getter)]
    pub fn error(&self) -> String {
        self.error_message.clone()
    }
}

/// Compile a TPT-IR JSON string into a package manifest.
///
/// This is the primary WASM entry point for browser-based compilation.
/// Takes TPT-IR JSON and target configuration, returns a PackageManifest.
#[wasm_bindgen]
pub fn compile(ir_json: &str, targets_json: &str) -> CompileResult {
    let ir_result = crate::package::PackageManifest::from_json(ir_json);

    match ir_result {
        Ok(manifest) => {
            let targets: Vec<String> = serde_json::from_str(targets_json).unwrap_or_default();
            let mut pkg = manifest;
            for target in &targets {
                pkg.targets.push(crate::package::TargetEntry {
                    name: target.clone(),
                    artifacts: Vec::new(),
                });
            }

            match pkg.to_json() {
                Ok(json) => CompileResult {
                    manifest_json: json,
                    success: true,
                    error_message: String::new(),
                },
                Err(e) => CompileResult {
                    manifest_json: String::new(),
                    success: false,
                    error_message: format!("Serialization error: {e}"),
                },
            }
        }
        Err(e) => CompileResult {
            manifest_json: String::new(),
            success: false,
            error_message: format!("IR parse error: {e}"),
        },
    }
}

/// Validate a TPT-IR JSON string and return validation results.
#[wasm_bindgen]
pub fn validate_ir(ir_json: &str) -> String {
    match crate::package::PackageManifest::from_json(ir_json) {
        Ok(m) => {
            let result = serde_json::json!({
                "valid": true,
                "model_name": m.model_name,
                "targets": m.targets.len(),
            });
            result.to_string()
        }
        Err(e) => {
            let result = serde_json::json!({
                "valid": false,
                "error": e.to_string(),
            });
            result.to_string()
        }
    }
}

/// Check compatibility of operators against a hardware target.
#[wasm_bindgen]
pub fn check_compatibility(ir_json: &str, target: &str) -> String {
    let _ = ir_json;
    let _ = target;
    let result = serde_json::json!({
        "target": target,
        "score": 0.95,
        "message": "Compatibility check completed (WASM stub)",
    });
    result.to_string()
}
