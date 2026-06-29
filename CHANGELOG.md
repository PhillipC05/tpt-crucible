# Changelog

All notable changes to TPT Crucible are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.0] — 2026-06-29

### Added

**TPT Catalyst** (ingestion + IR)
- GGUF, ONNX, PyTorch `.pt`, and TensorFlow SavedModel ingestion via Python + Rust backend
- TPT-IR custom MLIR dialect with quantization type metadata (Q4_K, Q8_0, etc.)
- Real TVM Relay optimization pass chain: FuseOps, EliminateCommonSubexpr, SimplifyInference, FoldConstant
- `.tptpkg` ZIP package builder with path-traversal guard
- WASM-compiled `check_compatibility()` with per-target op support matrix

**TPT Alloy** (MCU swarm)
- METIS/KaFFPa graph partitioning; auto layer-count from IR
- Per-node C++ firmware generation for ESP32, RP2040, RISC-V; Zephyr RTOS variant
- Hardware lock verification: RP2040 `flash_get_unique_id`, SiFive OTP MMIO, Zephyr `hwinfo_get_device_id`
- Inference dispatch loop in generated firmware; `tpt_sync_neighbors()` inter-node protocol
- PlatformIO real compilation in synthesis-worker (replaces `echo` stub)

**TPT Fusion** (FPGA)
- Amaranth HDL RTL generation; Yosys synthesis + Nextpnr place-and-route pipeline
- LiteX/LiteDRAM HBM controller integration; LLM-assisted Verilog MAC arrays with static timing pre-check

**TPT Element** (analog)
- Weight-to-component mapping; PySpice/Xyce SPICE simulation
- Reality Check PyTorch model for fast thermal/noise drift prediction
- KiCad PCB file export

**TPT Observer** (dashboard)
- Go WebSocket backend with real-time telemetry streaming (TPS, bandwidth, thermal, latency)
- CORS origin validation; per-IP WebSocket connection limiter (max 5 concurrent)
- React/Next.js frontend: Three.js 3D swarm topology, React Flow IR Graph Editor
- TelemetryContext delivering live data to all dashboard charts
- Telemetry replay engine for `.tptlog` files

**TPT Emulator** (SiL)
- Alloy SiL: virtual N-node swarm
- Fusion SiL: Verilator cycle-accurate RTL simulation
- Element SiL: Xyce/ngspice analog simulation
- Identical telemetry schema to real hardware

**TPT Mosaic** (hybrid orchestrator)
- Cross-hardware deployment: single model across FPGA + Swarm + Analog
- Layer annotations in TPT-IR; inter-hardware USB/UART/Ethernet bridge glue

**TPT Drivers** (SDK + registry)
- Standardized Rust trait + Python protocol: board identity, pin map, synthesis constraints, telemetry adapter, flash protocol
- `drivers/probe/` USB auto-detection (udev/WMI/IOKit)
- Community registry: versioned, signed driver packages + verified recipes
- BOM `[bom]` and power `[power]` sections in driver manifests
- LLM-based driver generator from datasheets (`drivers/ai-gen/`)

**Frontend**
- Environment-variable-driven API/WS URLs (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL`)
- Settings page: LLM provider, API key, endpoint, model, carbon region (Zod-validated localStorage)
- Cloud page: real job submission (`POST /api/jobs`), file type/size validation, polling
- IR Graph Editor: export to `.tptir` and save via REST
- Job history page with status badges and `.tptpkg` download links
- Toast notification system with auto-dismiss
- Dark/light mode toggle persisted to localStorage
- ErrorBoundary with blueprint-styled fallback
- 404 not-found page

**Security**
- Zod schema validation for all localStorage reads (SetupWizard, Settings)
- File upload accept list and 10 GB size cap
- WebSocket CORS origin allowlist; configurable via `ALLOWED_ORIGIN` env var
- Per-IP WebSocket rate limiter
- `.tptpkg` extraction path-traversal guard (`..` and leading `/` rejected)
- WASM input validation: 50 MB IR size cap, structured error JSON

### Changed
- License copyright updated to "2026 TPT Solutions"

### Fixed
- `PackageBuilder::build()` now produces a real ZIP archive (was a no-op stub)
- `check_compatibility()` WASM export now evaluates actual IR op types (was hardcoded 0.95)
- Alloy CLI layer count reads from IR instead of hardcoded 100
- Synthesis-worker `runAlloy()` invokes `platformio run` (was `echo`)
- `SaveManifest()` populates `model_name` and `targets` from real job data
