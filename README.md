# TPT Crucible

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-cyan)](CHANGELOG.md)

**Hardware-agnostic AI compiler suite.** Compile standard AI models (GGUF, ONNX, PyTorch, TensorFlow) onto non-traditional hardware: FPGAs, analog compute circuits, and microcontroller swarms.

> TPT Crucible is **not** a GPU compiler. It explicitly targets Alloy (ESP32/RP2040 swarms), Fusion (Xilinx FPGA), and Element (analog/SPICE circuits).

---

## Quick Start (5 minutes)

```bash
# 1. Install Rust, Python 3.10+, Go 1.22+, Node 18+

# 2. Build the Rust backend
cargo build --release

# 3. Install Python packages
pip install -e python/tpt_catalyst -e python/tpt_alloy

# 4. Ingest a GGUF model and compile for ESP32 swarm
tpt-catalyst ingest models/tinyllama.gguf --target alloy --output dist/tinyllama.tptpkg

# 5. Start the Observer dashboard
cd frontend && npm install && npm run dev
# Open http://localhost:3000
```

No hardware required — use the Software-in-the-Loop emulator for all three targets.

---

## Modules

| Module | Target | Language |
|--------|--------|----------|
| **TPT Catalyst** | Ingestion → TPT-IR | Python + Rust |
| **TPT Alloy** | MCU swarm (ESP32, RP2040, RISC-V) | Python + Rust |
| **TPT Fusion** | FPGA (Amaranth HDL → Yosys → Nextpnr) | Python |
| **TPT Element** | Analog (SPICE/KiCad) | Python |
| **TPT Observer** | Real-time dashboard | Go + Next.js |
| **TPT Emulator** | Software-in-the-Loop | Python + Rust |
| **TPT Mosaic** | Hybrid orchestration | Python + Rust |
| **TPT Drivers** | Board SDK + community registry | Rust + Python |

## Output: `.tptpkg`

Every compilation produces a `.tptpkg` (ZIP) containing:

```
model.tptpkg/
├── manifest.json         # version, model name, SHA-256 hashes
├── ir/model.tptir        # hardware-agnostic IR
├── targets/alloy/        # firmware binaries + flash script
├── targets/fusion/       # bitstream + board profile
├── targets/element/      # SPICE netlist + KiCad PCB
├── compat/preflight.json
├── quant/quant_profile.json
└── mosaic/partition.json
```

## Architecture

```
AI Model (.pt / .onnx / .gguf)
        ↓
   TPT Catalyst  →  TPT-IR (.tptir)
        ↓
  ┌─────┼──────┐
Alloy  Fusion  Element
  ↓      ↓       ↓
Firmware  RTL   SPICE/KiCad
        ↓
   TPT Observer (live telemetry)
```

## Development Phases

- **Phase 1 (Months 1–6):** Catalyst + Alloy. Milestone: TinyLlama on 16x ESP32.
- **Phase 2 (Months 6–12):** Fusion. Milestone: Xilinx Alveo bitstream from UI.
- **Phase 3 (Year 2):** Element. Milestone: 3-layer analog NN → KiCad PCB.
- **Phase 4 (Year 2+):** Observer dashboard unifying all three hardware types.

## TPT Spark Integration

[TPT Spark](https://github.com/PhillipC05/tpt-spark) is the companion local GGUF runtime (Tauri v2). Spark runs models on standard hardware; Crucible compiles them for custom hardware. Integration is via shared filesystem and optional IPC — both apps are independently runnable.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues and PRs are welcome.

## Security

See [SECURITY.md](SECURITY.md) for how to report vulnerabilities.

## License

Apache 2.0 — Copyright 2026 TPT Solutions. See [LICENSE](LICENSE).
