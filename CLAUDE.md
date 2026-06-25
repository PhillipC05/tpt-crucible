# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TPT Crucible is a hardware-agnostic AI compiler suite that compiles standard AI models (PyTorch, ONNX, TensorFlow, GGUF) onto non-traditional hardware: FPGAs, analog compute circuits, and microcontroller swarms. It is **not** a GPU-targeting tool — it explicitly bypasses the GPU path.

## Model Formats

| Role | Format | Notes |
|------|--------|-------|
| **Input** | GGUF (primary) | Quantization-preserving ingestion; reads from Spark's model library |
| **Input** | ONNX, PyTorch `.pt`, TensorFlow SavedModel | Secondary ingestion paths |
| **Internal IR** | TPT-IR (`.tptir`) | Custom MLIR dialect; hardware-agnostic compiled graph |
| **Output** | TPT Package (`.tptpkg`) | ZIP container — the canonical deliverable |

**TPT Package (`.tptpkg`)** is a ZIP-compatible container bundling everything needed to deploy a model to custom hardware: TPT-IR, compiled artifacts per target (firmware, RTL bitstream, SPICE netlist), hardware profiles, pre-flight compatibility report, quantization profile, and Mosaic partition plan. All module outputs write into a `.tptpkg` — there are no loose output files. A package with only `ir/` and `compat/` is a valid "analyzed, not compiled" artifact.

```
model.tptpkg/
├── manifest.json         # version, model name, SHA-256 hashes
├── ir/model.tptir
├── targets/alloy/        # firmware binaries + topology + flash script
├── targets/fusion/       # bitstream + mem_init + board profile
├── targets/element/      # SPICE netlist + KiCad PCB + confidence score
├── compat/preflight.json
├── quant/quant_profile.json
└── mosaic/partition.json
```

## Architecture

The system follows a **Core + Modules** pattern:

1. **TPT Catalyst** (`catalyst/`) — Python ingestion layer + Rust compiler backend. Parses AI models and emits **TPT-IR**, a hardware-agnostic intermediate representation built as a custom [MLIR](https://mlir.llvm.org/) dialect. Uses Apache TVM for operator fusion. All other modules consume TPT-IR.

2. **TPT Alloy** (`alloy/`) — Swarm/microcontroller module. Partitions TPT-IR into sub-graphs using METIS/KaFFPa, then generates unique per-node C++/Rust firmware for each microcontroller (ESP32, RP2040, RISC-V). Integrates PlatformIO or Zephyr RTOS for flashing.

3. **TPT Fusion** (`fusion/`) — FPGA module. Takes TPT-IR and generates synthesizable RTL via Amaranth HDL (Python → Verilog). Wraps Yosys (synthesis) and Nextpnr (place-and-route). Uses LiteX/LiteDRAM for HBM controller auto-routing.

4. **TPT Element** (`element/`) — Analog compute module. Maps AI weights to physical components (resistors, memristors, op-amps). Runs SPICE simulation via Xyce/PySpice and uses a trained PyTorch model to predict thermal/noise drift fast. Outputs SPICE netlists and KiCad PCB files.

5. **TPT Observer** (`observer/`) — Unified dashboard. Go backend streams real-time telemetry via WebSockets. React/Next.js frontend with Three.js for 3D swarm topology/PCB visualization, React Flow for the Visual IR Graph Editor, and a telemetry replay engine (`.tptlog` files).

6. **TPT Emulator** (`emulator/`) — Software-in-the-Loop emulator for all three hardware types. Alloy SiL: virtual N-node swarm. Fusion SiL: Verilator-backed cycle-accurate RTL simulation. Element SiL: Xyce/ngspice analog simulation. All emit the same telemetry schema as real hardware so Observer treats them identically.

7. **TPT Mosaic** (`mosaic/`) — Hybrid cross-hardware deployment orchestrator. Reads per-layer hardware annotations from TPT-IR, calls the appropriate module per partition, and generates inter-hardware communication glue (USB/UART/Ethernet bridges). Enables a single model to run across FPGA + Swarm + Analog simultaneously.

8. **TPT Drivers** (`drivers/`) — Hardware driver SDK and community registry. Defines a standardized driver interface (Rust trait + Python protocol) covering board identity, pin/resource map, synthesis constraints, telemetry adapter, and flash protocol. Includes a `probe/` submodule for USB auto-detection. The community registry is a public index of versioned, signed driver packages and verified compilation recipes.

9. **tpt-train** (`tpt-train/`) — Standalone pip package providing PyTorch/JAX training hooks (`TPTProbeCallback`) that record per-layer activation ranges and weight distributions into a `model.tptprofile` file. Catalyst consumes `.tptprofile` to make better quantization decisions than static weight analysis alone.

10. **Cloud Workers** (`cloud/`) — Self-hostable infrastructure only; TPT provides Docker images and docs, does not operate these services.

11. **TPT Validator** (`validator/`) — Model accuracy validator. Connects to a live hardware deployment (or SiL) and a reference backend (Spark IPC or local CPU), sends a standardized prompt suite, and compares outputs via token-level similarity + perplexity delta. For analog: additionally checks per-layer output voltage vs. SPICE-expected values.

12. **AI Generation Subsystems** — Each hardware module has an AI-assisted design layer:
    - `drivers/ai-gen/` — LLM-based driver generator from datasheets; uses pluggable LLM backend
    - `alloy/ai-topology/` — Swarm topology advisor; starts LLM-based, accumulates SiL training data, graduates to a trained ML model
    - `fusion/ai-rtl/` — LLM-assisted Verilog MAC array generation with static timing pre-check; falls back to Amaranth templates if no LLM configured
    - `element/ai-circuit/` — Generative analog circuit designer; retrieval-augmented (Phase 1), generative model (Phase 2); validated by Reality Check after each candidate
    - `cloud/synthesis-worker/`: Go worker + Redis queue for offloading slow FPGA synthesis (Yosys + Nextpnr) to remote machines.
    - `cloud/crucible-cloud/` *(optional/bonus)*: Full pipeline web service — upload GGUF, select target, download `.tptpkg`. Docker Compose + Helm chart for self-hosted deployment.

## Data Flow

```
AI Model (.pt / .onnx / .tf)
        ↓
   TPT Catalyst  →  TPT-IR (.tptir)
        ↓
  ┌─────┼──────┐
Alloy  Fusion  Element
  ↓      ↓       ↓
Firmware  RTL   SPICE/KiCad
        ↓
   TPT Observer (telemetry)
```

## Technology Stack

| Component | Languages | Key Dependencies |
|-----------|-----------|-----------------|
| Catalyst | Python + Rust | MLIR, Apache TVM, PyTorch, ONNX Runtime, gguf-py |
| Alloy | Python + Rust | METIS/KaFFPa, PlatformIO, Zephyr RTOS |
| Fusion | Python | Amaranth HDL, Yosys, Nextpnr, LiteX/LiteDRAM |
| Element | Python | Xyce/ngspice, PySpice, PyTorch |
| Observer | Go + TypeScript | React, Next.js, Three.js/R3F, React Flow, Tailwind CSS |
| Emulator | Python + Rust | Verilator (Fusion SiL), Xyce/ngspice (Element SiL) |
| Mosaic | Python + Rust | (orchestrates Alloy/Fusion/Element) |
| Drivers | Rust + Python | (SDK + registry client; probe uses udev/WMI/IOKit) |
| tpt-train | Python | PyTorch, JAX/Flax |
| Cloud Workers | Go | Redis, Docker, Yosys + Nextpnr (synthesis worker) |

## Development Phases

- **Phase 1 (Months 1–6):** Catalyst + Alloy. Milestone: TinyLlama on 16x ESP32.
- **Phase 2 (Months 6–12):** Fusion. Milestone: Xilinx Alveo bitstream from UI.
- **Phase 3 (Year 2):** Element. Milestone: 3-layer analog NN → KiCad PCB.
- **Phase 4 (Year 2+):** Observer dashboard unifying all three hardware types.

## Key Design Decisions

- **Do not build a custom IR from scratch.** Use MLIR and define a TPT-IR dialect on top of it.
- **Wrap CLI tools (Yosys, Nextpnr, Xyce), never expose them raw** to the user — the UI abstracts all synthesis/simulation toolchains.
- **Reality Check (TPT Element):** Brute-force SPICE is too slow for interactive use. A PyTorch model trained on SPICE runs provides fast drift prediction; full SPICE is reserved for final validation.
- **Pre-flight check before compiling.** Always run `tpt-catalyst check` before `tpt-catalyst ingest` when targeting a new hardware type. The operator support matrix lives in `catalyst/compat/`.
- **SiL emulator uses the same telemetry schema as real hardware.** Observer cannot tell the difference — this is intentional. Don't add emulator-specific telemetry fields.
- **Mosaic layer annotations live in TPT-IR, not in module code.** Each module reads its own tagged layers; the Mosaic orchestrator handles cross-module coordination.
- **GGUF ingestion is quantization-preserving.** Unlike PyTorch/ONNX/TF models (ingested as float32 graphs), GGUF models arrive pre-quantized. TPT-IR must carry quantization type metadata (Q4_K, Q8_0, etc.) so Fusion and Alloy can generate hardware-appropriate compute (e.g., INT4 MAC arrays for Q4 models).
- **Reality Check and Circuit Designer are separate models with different tasks.** Reality Check is *discriminative* (given a circuit, predict failure probability). The AI Circuit Designer is *generative* (given a target operation, produce a circuit). Both are trained on the same SPICE dataset but solve different problems. Don't conflate them.
- **Driver manifests include `[bom]` and `[power]` sections.** `[bom]` carries part numbers + supplier SKUs (DigiKey/Mouser/LCSC). `[power]` carries idle/active/peak mW. Both are required for BOM generation and cost/power estimation to work.
- **AI generation features degrade gracefully.** Driver Generator, Topology Advisor, and RTL Assistant are hidden when no LLM provider is configured. Fusion falls back to Amaranth template generation. The Circuit Designer's retrieval-augmented Phase 1 works without an LLM.
- **Hardware drivers are a standardized SDK, not hardcoded board configs.** All board support lives in `drivers/` as versioned, community-contributable packages. The Xilinx Alveo profile is the reference implementation. New boards require only a driver package — no changes to core modules.
- **Natural language features are LLM-agnostic and optional.** The provider interface supports OpenRouter, Anthropic API, any Ollama-compatible endpoint, and TPT Spark IPC. If no provider is configured, NL features are hidden — no degraded experience and no hard dependency on any LLM service.
- **Cloud features are self-hostable infrastructure.** TPT provides Docker images + deployment docs; the project does not operate any cloud services. All cloud features are opt-in via user-configured URLs in settings.
- **`.tptprofile` improves but never blocks compilation.** If `tpt-train` hooks were used during training, Catalyst uses the profile for better quantization. If not present, Catalyst falls back to static weight analysis — the pipeline always works.
- **Open-core:** Underlying compilers (MLIR, Yosys, Xyce) are open-source. TPT-proprietary layers are the glue, UI, and AI-driven optimization passes.
- **UI theme:** Tailwind CSS, dark mode, "industrial blueprint" aesthetic — dark grays, neon cyan/amber accents, monospaced fonts for data readouts.

## TPT Spark Integration

[TPT Spark](https://github.com/PhillipC05/tpt-spark) is a sibling app — a local GGUF runtime (Tauri v2, Rust, wgpu GPU / HuggingFace Candle CPU fallback). They share the GGUF model format and form a complementary stack: Spark runs models on standard hardware, Crucible compiles them for custom hardware.

**Integration points:**
- **Shared model library**: Catalyst reads from Spark's local model directory; no re-downloading. Accept a `--spark-model <id>` flag in the Catalyst CLI.
- **Baseline benchmarks**: Observer pulls Spark's tokens/sec from its local conversation JSON and displays it alongside Crucible hardware metrics.
- **Prompt replay**: The SiL emulator can consume Spark's conversation JSON as regression benchmark input.
- **Spark UI hook**: A "Compile for Custom Hardware" button in Spark's sidebar hands off the loaded model to Crucible (file path + model ID via IPC or temp file).

**Boundary**: Do not add Crucible as a Spark dependency. Integration is filesystem + optional IPC only. Both apps must remain independently runnable.
