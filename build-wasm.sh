#!/usr/bin/env bash
# Build TPT Catalyst and Alloy for WebAssembly
set -euo pipefail

echo "=== TPT Crucible WASM Build ==="
echo ""

# Check prerequisites
if ! command -v wasm-pack &> /dev/null; then
    echo "Error: wasm-pack not found. Install with: cargo install wasm-pack"
    exit 1
fi

if ! command -v rustup &> /dev/null; then
    echo "Error: rustup not found"
    exit 1
fi

# Ensure wasm32 target is installed
echo "[1/4] Installing wasm32-unknown-unknown target..."
rustup target add wasm32-unknown-unknown 2>/dev/null || true

# Build tpt-catalyst for WASM
echo "[2/4] Building tpt-catalyst for WASM..."
wasm-pack build crates/tpt-catalyst \
    --target web \
    --features wasm \
    --release \
    --out-dir ../../pkg/wasm \
    2>&1

# Copy WASM output to frontend
echo "[3/4] Copying WASM artifacts to frontend..."
mkdir -p frontend/public/wasm
cp pkg/wasm/*.wasm frontend/public/wasm/ 2>/dev/null || true
cp pkg/wasm/*.js frontend/public/wasm/ 2>/dev/null || true

# Create Web Worker wrapper
echo "[4/4] Creating Web Worker wrapper..."
cat > frontend/public/wasm/compile-worker.js << 'WORKER_EOF'
import init, { compile, validate_ir, check_compatibility } from './tpt_catalyst.js';

let initialized = false;

async function ensureInit() {
    if (!initialized) {
        await init();
        initialized = true;
    }
}

self.onmessage = async function(e) {
    const { id, action, payload } = e.data;

    try {
        await ensureInit();

        let result;
        switch (action) {
            case 'compile':
                result = compile(payload.ir_json, payload.targets_json);
                break;
            case 'validate':
                result = { valid: true, result: validate_ir(payload.ir_json) };
                break;
            case 'compatibility':
                result = { result: check_compatibility(payload.ir_json, payload.target) };
                break;
            default:
                result = { error: `Unknown action: ${action}` };
        }

        self.postMessage({ id, result, error: null });
    } catch (err) {
        self.postMessage({ id, result: null, error: err.message });
    }
};
WORKER_EOF

echo ""
echo "=== Build complete ==="
echo "WASM artifacts: frontend/public/wasm/"
echo "Worker: frontend/public/wasm/compile-worker.js"
echo ""
echo "To use in browser:"
echo "  const worker = new Worker('/wasm/compile-worker.js');"
echo "  worker.postMessage({ id: 1, action: 'compile', payload: { ir_json: '...', targets_json: '[\"alloy\"]' } });"
