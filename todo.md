# TPT Crucible — Master Task Checklist

---

## Phase 1: The Catalyst & The Swarm (Months 1–6)

### TPT Catalyst — Core IR Compiler
- [x] Set up mono-repo project structure (Rust workspace + Python packages)
- [x] Integrate MLIR toolchain and define custom TPT-IR MLIR dialect
- [x] Implement PyTorch model ingestion (.pt / TorchScript)
- [x] Implement ONNX model ingestion
- [x] Implement TensorFlow/SavedModel ingestion
- [x] Implement GGUF model ingestion (llama.cpp format, quantization-preserving)
- [x] Preserve GGUF quantization metadata (Q4_K, Q8_0, etc.) through TPT-IR
- [x] Integrate Apache TVM for initial graph optimization pass
- [x] Implement operator fusion (fuse sequential ops like MatMul + activation into single blocks)
- [x] Define and implement TPT-IR serialization format (JSON + binary)
- [x] Write unit tests for ingestion and IR correctness
- [x] CLI: `tpt-catalyst ingest <model>` → outputs `.tptir` file

### TPT Catalyst — Extended Input Formats
- [ ] Implement SafeTensors ingestion (`safetensors` library; memory-mapped, dtype/shape metadata preserved)
- [ ] Implement HuggingFace model directory ingestion: auto-detect config.json + weights file, load tokenizer metadata
- [ ] CLI: `tpt-catalyst ingest <hf-model-dir>` and `tpt-catalyst ingest --hf-repo org/model-name`
- [ ] Implement HuggingFace Hub pull: download model to local cache if not present, then ingest
- [ ] Implement TFLite ingestion (`.tflite`): parse FlatBuffer schema, map pre-quantized ops to TPT-IR, preserve quantization params
- [ ] Implement AWQ/GPTQ ingestion: read `quantize_config.json` from HF repo, extract per-layer bit-width assignments, pass to TPT-IR quantization metadata
- [ ] Implement EXL2 ingestion (`.exl2`): extract per-layer quantization scale/zero tables into TPT-IR
- [ ] Implement JAX/Flax orbax checkpoint ingestion: load parameter tree, convert to float32 weight tensors, map to TPT-IR ops via model config
- [ ] Implement Llamafile header-strip: detect `.llamafile` magic bytes, skip executable prefix, route to GGUF ingestion
- [ ] Implement Keras `.h5` ingestion: convert via `tf.keras.models.load_model` → route to TF SavedModel path
- [ ] Auto-detect input format from file extension + magic bytes (no `--format` flag required)
- [ ] Unit tests: ingest one model per format, verify TPT-IR output is structurally equivalent to PyTorch baseline

### TPT Catalyst — Pre-flight Compatibility Analyzer
- [x] Define operator support matrix per hardware target (FPGA / Swarm / Analog)
- [x] Implement graph scan pass that flags unsupported operators for a given target
- [x] Suggest operator substitutions where possible (e.g., Flash Attention → standard MHA for analog)
- [x] Output structured compatibility report with pass/warn/fail per hardware type + readiness score
- [x] Expose via CLI: `tpt-catalyst check <model.tptir> --target alloy`
- [ ] Surface warnings inline in Visual IR Graph Editor

### TPT Catalyst — Auto-Quantization Advisor
- [x] Define per-hardware quantization profiles (FPGA: INT8/INT4, Swarm: INT8, Analog: float/unquantized)
- [x] Implement quantization advisor pass: recommend scheme + estimated accuracy loss vs. resource tradeoff
- [x] Implement auto-apply quantization pass (rewrite TPT-IR weights to target dtype)
- [x] CLI flag: `tpt-catalyst ingest <model> --quantize auto --target fusion`
- [ ] UI toggle in Observer compilation panel

### TPT Alloy — Swarm / Microcontroller Module
- [x] Integrate METIS or KaFFPa C++ graph partitioning library
- [x] Build Python bindings for the partitioning library
- [x] Implement TPT-IR → neural network graph conversion for partitioning
- [x] Implement topology-aware partitioning (accept 2D grid / star / custom wiring layout as input)
- [x] Build Rust-based per-node firmware code generator (C++/Rust output)
- [x] Integrate PlatformIO build system for targeting ESP32 / RP2040 / RISC-V
- [ ] Optionally integrate Zephyr RTOS support for custom RISC-V targets
- [x] Generate master flashing script (flash all N nodes from one command)
- [ ] Test partition + firmware gen against TinyLlama on 16x ESP32 swarm
- [x] CLI: `tpt-alloy partition <model.tptir> --topology grid2d --nodes 16`

### TPT Alloy — KV Cache Distribution
- [ ] Design KV cache sharding scheme: each node owns KV heads for its assigned attention layers
- [ ] Implement second-pass KV allocation in partition planner after layer assignment
- [ ] Add per-node memory budget enforcement: block generation if KV + activations exceed node PSRAM
- [ ] Stream only query/key vectors between nodes (not full cache dumps) in inter-node protocol
- [ ] Add KV allocation report to pre-flight output
- [ ] Test: verify no OOM on TinyLlama 16× ESP32 across a 128-token generation

### TPT Alloy — Fault-Tolerant Execution
- [ ] Define heartbeat protocol: each node sends a keepalive packet every N ms to coordinator
- [ ] Coordinator firmware: detect node timeout, trigger layer reassignment to neighbors
- [ ] Implement degraded-mode rerouting: redistribute dead node's layers across k nearest nodes
- [ ] Add `fault_tolerance` field to `topology.json` (enabled/disabled + timeout threshold)
- [ ] Observer UI: dead-node heatmap — nodes color-coded green/amber/red by heartbeat status
- [ ] Auto-recover: when a dead node responds again, re-integrate it and rebalance partitioning
- [ ] CLI: `tpt-alloy partition ... --fault-tolerance enabled`

### TPT Alloy — Attention-Head Parallel Partitioning
- [ ] Detect transformer attention layers in TPT-IR during partitioning analysis
- [ ] Implement head-parallel partitioning strategy in `crates/tpt-alloy/src/partition.rs`
- [ ] Implement hybrid mode: head-parallel for attention sublayers, layer-serial for FFN sublayers
- [ ] Add sum-reduce handshake to firmware inter-node protocol for head aggregation
- [ ] Topology Advisor: auto-recommend head-parallel strategy for transformer models
- [ ] Add `--partition-strategy layer|head-parallel|hybrid` flag to Alloy CLI
- [ ] Benchmark: compare layer-wise vs. head-parallel throughput on TinyLlama swarm SiL

### TPT Alloy — Physical Topology Auto-Discovery (`alloy/auto-discovery/`)
- [ ] Design broadcast protocol: each node pings all others, measures round-trip time
- [ ] Nodes aggregate RTT matrix and report to coordinator node over WiFi
- [ ] Alloy Python: reconstruct graph from RTT matrix (minimum spanning tree inference)
- [ ] Present inferred topology to user for confirmation before partitioning begins
- [ ] Observer UI: show auto-discovered topology in 3D viewer before compile
- [ ] Fallback: if auto-discovery fails, fall through to manual topology input
- [ ] CLI: `tpt-alloy discover --nodes 16 --timeout 30s` → outputs `topology.json`

### TPT Alloy — Pipeline Parallelism
- [ ] Design pipeline scheduler: rolling token window across the node chain
- [ ] Implement pipeline depth configuration in firmware generator (depth 1 = sequential)
- [ ] Nodes buffer in-flight KV state for pipeline_depth tokens simultaneously
- [ ] Add `pipeline_depth` field to `topology.json`; default to `min(node_count, 4)`
- [ ] Benchmark pipeline depth vs. throughput vs. PSRAM usage on SiL
- [ ] Observer UI: show pipeline utilization chart (pipeline bubble %) alongside tokens/sec

### Phase 1 Milestone
- [ ] **DEMO:** Load TinyLlama → TPT Catalyst → TPT Alloy → flash 16x ESP32 → run basic chat interface

---

## Phase 2: The Silicon Canvas (Months 6–12)

### TPT Fusion — FPGA / HBM Module
- [x] Set up Amaranth HDL Python environment
- [x] Implement TPT-IR → MAC array hardware description in Amaranth HDL
- [x] Integrate Yosys for open-source logic synthesis (wrap CLI, no raw shell exposure to user)
- [x] Integrate Nextpnr for place-and-route (wrap CLI)
- [x] Build FPGA board library (starting with Xilinx Alveo)
- [x] Integrate LiteX + LiteDRAM for HBM controller generation
- [x] Implement HBM Auto-Router: auto-wire compute arrays to HBM pins given a board selection
- [x] Handle complex HBM timing constraint injection automatically
- [x] Generate synthesizable RTL (Verilog/VHDL output)
- [x] Generate memory initialization files
- [ ] UI: board selector → triggers Fusion pipeline → outputs ready-to-flash bitstream
- [ ] Test end-to-end on Xilinx Alveo with a quantized AI model

### TPT Fusion — FPGA Overlay Architecture (`fusion/overlay/`)
- [ ] Design overlay bitstream spec: parameterized MAC array + weight BRAM banks + HBM controller as fixed bitstream
- [ ] Define `.fusecfg` config file format: datapath width, layer count, weight loading addresses
- [ ] Implement overlay compiler: TPT-IR → `.fusecfg` + weight binary (no Yosys/Nextpnr invoked)
- [ ] Build reference Alveo overlay bitstream (shipped with Fusion; covers INT8 + INT4 MAC configurations)
- [ ] Add overlay-vs-resynthesis decision in Fusion pipeline: use overlay if target board has a pre-built overlay, else fall through to full synthesis
- [ ] CLI: `tpt-fusion compile <model.tptir> --board alveo --mode overlay|full`
- [ ] Benchmark: measure overlay compile time vs. full resynthesis on same model
- [ ] Observer UI: show compile mode (overlay / full synthesis) and estimated time before starting

### Phase 2 Milestone
- [ ] **DEMO:** Select Xilinx Alveo in UI → TPT Fusion outputs bitstream → flash board → runs quantized AI model using HBM

---

## Phase 3: The Physics Engine (Year 2)

### TPT Element — Analog Compute Module
- [x] Set up Xyce SPICE simulator (preferred) with PySpice Python wrapper
- [x] Add ngspice fallback support
- [x] Implement floating-point weight → physical component mapping (resistors, memristors, op-amp gains)
- [x] Build SPICE netlist generator from TPT-IR weights
- [x] Implement thermal noise injection in simulations
- [x] Implement voltage drift simulation
- [x] Implement component tolerance error simulation (1%, 5%, 10% tolerance profiles)
- [x] Build "Reality Check" dataset: run thousands of SPICE simulations, capture failure modes
- [x] Train lightweight PyTorch ML model on SPICE dataset to predict thermal/noise drift instantly
- [x] Integrate Reality Check model as fast inference pass (replacing slow brute-force SPICE for routine checks)
- [x] Generate human-readable mitigation suggestions (e.g., "Add heatsink to Node 4", "Use 1% resistors here")
- [x] Generate SPICE netlist output files
- [x] Generate PCB layout recommendations
- [x] Integrate KiCad file export for PCB manufacturing
- [x] Compute and output analog "Confidence Score" for each design
- [ ] Test on a 3-layer analog neural network design

### Phase 3 Milestone
- [ ] **DEMO:** Design 3-layer analog NN → TPT Element simulates thermal drift → outputs KiCad PCB file ready for manufacturing

---

## Phase 4: The Observer (Year 2+)

### TPT Observer — Unified Dashboard
- [x] Set up Go (Golang) backend service
- [x] Implement WebSocket server for real-time hardware telemetry streaming
- [x] Define unified telemetry data schema (tokens/s, memory bandwidth, thermal drift, node latency)
- [x] Implement FPGA telemetry adapter (memory bandwidth utilization)
- [x] Implement Analog telemetry adapter (thermal drift over time)
- [x] Implement Swarm telemetry adapter (per-node latency)
- [ ] Set up React + Next.js frontend
- [ ] Implement Tailwind CSS "industrial blueprint" dark theme (dark grays, neon cyan/amber, monospaced data fonts)
- [ ] Build unified telemetry dashboard view (all hardware types in one UI)
- [ ] Integrate Three.js / React Three Fiber for 3D swarm topology visualizer (nodes + wires)
- [ ] Integrate Three.js / React Three Fiber for PCB layout visualizer (Analog module)
- [ ] Build tokens-per-second live chart
- [ ] Build memory bandwidth utilization live chart (FPGA)
- [ ] Build thermal drift live chart (Analog)
- [ ] Build node-latency heatmap (Swarm)

### Phase 4 Milestone
- [ ] **DEMO:** Single Observer dashboard shows live telemetry from FPGA, Analog, and Swarm hardware simultaneously

---

## Software-in-the-Loop (SiL) Emulator (`emulator/`)

- [x] Define unified emulator interface (same telemetry schema as real hardware)
- [x] **Alloy SiL**: Implement virtual N-node swarm simulator (message-passing, inter-node latency model)
- [x] **Fusion SiL**: Wrap Verilator for cycle-accurate RTL simulation of generated Verilog
- [x] **Element SiL**: Wire Xyce/ngspice (already in spec) as the analog emulator backend
- [x] Emulator output streams to Observer via same WebSocket telemetry path as real hardware
- [x] CLI: `tpt-emulate <compiled-output> --hardware alloy|fusion|element`

---

## Hybrid Cross-Hardware Deployment (`mosaic/`)

- [x] Define layer annotation format in TPT-IR (tag each layer with target: fpga/swarm/analog)
- [x] Implement `mosaic/` orchestrator: reads annotations, calls relevant module per partition
- [x] Define inter-hardware communication protocol (USB/UART/Ethernet bridge spec)
- [x] Generate inter-hardware glue code (data serialization between segments)
- [ ] Observer: unified pipeline view showing per-segment latency across hardware types
- [ ] UI: drag-and-drop layer-to-hardware assignment in Visual IR Graph Editor

---

## TPT Observer — Visual TPT-IR Graph Editor

- [ ] Integrate React Flow into Observer Next.js frontend
- [ ] Render TPT-IR as interactive DAG (nodes = operators, edges = tensor shapes/dtypes)
- [ ] Show pre-flight compatibility warnings as inline node badges
- [ ] Allow operator swap (right-click → substitute with compatible op)
- [ ] Allow quantization pass insertion between nodes
- [ ] Allow layer-to-hardware tagging for Mosaic hybrid deployment
- [ ] Export modified IR back to `.tptir` file

---

## TPT Observer — Telemetry Replay & Time-Travel Debug

- [x] Define `.tptlog` binary format (timestamped telemetry stream + inference metadata)
- [x] Go backend: record all active telemetry streams to `.tptlog` on user request
- [ ] Observer UI: replay scrub bar with per-token step navigation (pause/play/step)
- [ ] Overlay mode: compare two `.tptlog` files side-by-side (e.g., before/after firmware update)
- [ ] Emit replay telemetry through same Observer chart components as live data

---

## TPT Spark Integration

- [x] Detect TPT Spark model directory at startup; expose as model source in Catalyst UI
- [ ] Catalyst CLI: accept Spark model ID as input (`tpt-catalyst ingest --spark-model llama3-8b`)
- [x] Define IPC/file-based protocol for Spark → Crucible model handoff
- [ ] Observer: pull Spark tokens/sec baseline from local JSON conversation history
- [ ] Observer: display side-by-side benchmark — Spark (GPU/CPU) vs. Crucible (custom hardware)
- [ ] SiL emulator: accept Spark conversation JSON as prompt replay input for regression benchmarking
- [ ] (Spark-side) Add "Compile for Custom Hardware" button to Spark sidebar — exports model to Crucible

---

## TPT Package Format (`.tptpkg`)

- [x] Define `.tptpkg` container spec and `manifest.json` schema (format version, model name, source SHA-256, targets list, per-node firmware checksums)
- [x] Implement `.tptpkg` writer in Catalyst (Rust) — ZIP container produced after compilation
- [x] Implement `.tptpkg` reader — used by each module to load its compiled artifacts at flash/deploy time
- [x] Implement SHA-256 checksumming for source model, TPT-IR, and all per-node firmware files
- [x] CLI: `tpt-catalyst pack <model.tptir> --targets alloy,fusion` → `model.tptpkg`
- [x] CLI: `tpt-catalyst unpack <model.tptpkg>` → inspect/extract contents
- [x] Update TPT Alloy to write firmware + topology.json + flash.sh into `.tptpkg` structure
- [x] Update TPT Fusion to write bitstream + mem_init + board.json into `.tptpkg` structure
- [x] Update TPT Element to write netlist.spice + pcb.kicad_pcb + confidence.json into `.tptpkg` structure
- [x] Write pre-flight report into `compat/preflight.json` in the package
- [x] Write quantization profile into `quant/quant_profile.json` in the package
- [x] Write Mosaic partition plan into `mosaic/partition.json` in the package
- [ ] Observer: display `.tptpkg` manifest metadata (model name, targets, checksums, readiness score) in UI

---

## TPT Drivers — Hardware Driver SDK & Registry (`drivers/`)

- [x] Define hardware driver interface spec (Rust trait + Python protocol): board identity, pin/resource map, synthesis constraints, telemetry adapter, flash protocol
- [x] Implement driver loader: resolve drivers by name/version from local cache or registry
- [x] Build driver types: FPGA board profiles, MCU variants (ESP32, RP2040, RISC-V), analog component libraries
- [x] Migrate existing Xilinx Alveo board profile to driver format as reference implementation
- [x] Build community registry index format (TOML manifest, versioned, signed)
- [x] CLI: `tpt-drivers install <driver-name>` — downloads and caches driver from registry
- [x] CLI: `tpt-drivers list` — show installed drivers; `tpt-drivers search <query>`
- [ ] Implement recipe system: `tpt-drivers install tinyllama-esp32-16node` pulls a verified topology + driver bundle
- [ ] Write driver authoring docs + driver SDK template repo

### Hardware Auto-Detection (`drivers/probe/`)
- [ ] Implement USB/serial device probing (udev on Linux, WMI on Windows, IOKit on macOS)
- [ ] Build VID/PID → driver registry lookup
- [ ] Observer UI: auto-populate board profile on device connect; prompt user to confirm
- [ ] Fallback: guided manual board selection wizard if device isn't in registry

---

## Natural Language Hardware Config

- [x] Define pluggable LLM provider interface (OpenRouter, Anthropic, Ollama/OpenAI-compatible, TPT Spark IPC)
- [x] Implement LLM provider config in user settings (API key, model selection, endpoint URL)
- [x] Hide NL config feature entirely when no LLM provider is configured
- [x] Implement structured topology JSON generation prompt + schema validation
- [ ] Observer UI: free-text input field → confirmed topology preview in Visual IR Graph Editor
- [ ] Save natural language description in `.tptpkg` alongside `topology.json` (for reproducibility)
- [ ] Test against: OpenRouter (cloud), Ollama (local), TPT Spark (local GGUF via IPC)

---

## Hot Recompilation (TPT Catalyst)

- [x] Implement content-addressed cache: per-operator hash keyed on TPT-IR subgraph
- [x] Store cache in `.tpt-cache/` directory adjacent to working `.tptpkg`
- [ ] CLI flag: `tpt-catalyst pack --incremental` - skip operators whose hash matches cache
- [ ] Observer UI: show per-layer cache hit/miss indicators during compilation
- [x] Cache invalidation: bust cache for a layer when its inputs, weights, or target hardware change

---

## Hardware-Aware Training Hooks (`tpt-train/`)

- [x] Implement `TPTProbeCallback` for PyTorch: attaches to all layers, records min/max activations, weight histograms, gradient norms per epoch
- [ ] Implement equivalent JAX/Flax hook
- [x] Output: `model.tptprofile` JSON (per-layer activation stats + weight distributions)
- [ ] Catalyst integration: if `.tptprofile` exists alongside model, use it to set per-layer quantization clamps
- [ ] Auto-Quantization Advisor: prefer `.tptprofile` data over static weight analysis when available
- [ ] Add `.tptprofile` reference to `.tptpkg` manifest if profile was used during compilation
- [ ] Publish `tpt-train` as a standalone pip package (`pip install tpt-train`)

---

## Cloud Synthesis Worker — Self-Hostable (`cloud/synthesis-worker/`)

- [ ] Go worker service: accept `.tptpkg` upload, run Yosys + Nextpnr, return updated `.tptpkg` with bitstream
- [ ] Redis-based job queue (stateless workers, horizontally scalable)
- [ ] Observer UI: "Offload synthesis to worker" toggle (shown only when a worker URL is configured in settings)
- [ ] Dockerfile + Docker Compose for single-node deployment
- [ ] Worker deployment docs

---

## TPT Crucible Cloud — Self-Hostable Full Pipeline (`cloud/crucible-cloud/`) *(optional/bonus)*

- [ ] Go API server: model upload, compilation job management, `.tptpkg` download endpoints
- [ ] Containerized Catalyst + module workers (one image per hardware target type)
- [ ] Minimal Next.js web UI: upload model → select target → track job → download `.tptpkg`
- [ ] Docker Compose stack for self-hosted single-server deployment
- [ ] Helm chart for Kubernetes deployment
- [ ] Deployment and configuration docs

---

## AI Driver Generator (`drivers/ai-gen/`)

- [ ] Implement PDF/URL datasheet text extractor (PyMuPDF for PDF, BeautifulSoup for URLs)
- [ ] Define structured LLM extraction prompt: extract pinout, memory map, peripheral specs, flash protocol, clock/timing
- [ ] LLM output → driver manifest TOML + Rust trait skeleton + synthesis constraints + flash protocol stub
- [ ] Observer UI: diff-style preview of generated driver; user edits and approves
- [ ] Run SDK schema validator on generated driver before allowing publish to registry
- [ ] "Publish to Registry" flow from the review screen
- [ ] LLM backend: uses same pluggable provider interface as NL Hardware Config

---

## AI Swarm Topology Advisor (`alloy/ai-topology/`)

- [ ] Define input schema: TPT-IR profile (layer count, bandwidth matrix) + user constraints (node count, latency budget, power budget, form factor)
- [ ] Implement LLM-based topology recommendation (initial approach)
- [ ] Define training data schema: (model profile + constraints + topology) → measured SiL performance
- [ ] Accumulate SiL run results as training data automatically
- [ ] Train ML model on accumulated SiL data when dataset is large enough; swap in as default
- [ ] Output: ranked topology recommendations (ring/mesh/star/tree/hybrid) with predicted latency + power
- [ ] Observer UI: 3D preview of each recommended topology; one-click "use this" to feed into Alloy partitioner

---

## AI RTL Assistant (`fusion/ai-rtl/`)

- [ ] Implement compute pattern extractor from TPT-IR (layer types, tensor shapes, dtypes, repetition count)
- [ ] Build LLM prompt template: compute pattern + board constraints → candidate Verilog MAC array
- [ ] Implement static timing pre-check on generated Verilog (wrap OpenTimer or `yosys stat`)
- [ ] Flag timing violations with suggested datapath modifications before full synthesis
- [ ] Observer UI: generated RTL shown in Visual IR Editor for review before entering Fusion pipeline
- [ ] Fallback: if no LLM configured, Fusion uses existing Amaranth HDL template generation (no regression)

---

## AI Analog Circuit Designer (`element/ai-circuit/`)

- [ ] Define training data schema: (target op spec: matrix size, precision, activation) ↔ (netlist + SPICE-measured accuracy)
- [ ] Build dataset generation pipeline: enumerate known analog implementations, run SPICE, record results
- [ ] Implement retrieval-augmented circuit generator (Phase 1): find closest circuit in dataset, adapt component values
- [ ] Integrate Reality Check model as fast validation pass on generated candidates
- [ ] Implement iterative refinement loop: generate → validate → perturb if low confidence → repeat
- [ ] Output: top-N ranked candidate circuits with confidence scores and predicted failure modes
- [ ] Observer UI: side-by-side candidate circuit viewer with confidence scores
- [ ] Phase 2 (later): train generative model (VAE or diffusion over circuit graph space) to replace retrieval approach

---

## Bill of Materials (BOM) Generator

- [x] Add `[bom]` section to driver manifest spec: part numbers, quantities, supplier SKUs (DigiKey, Mouser, LCSC)
- [x] Populate `[bom]` for all first-party drivers (ESP32, RP2040, Xilinx Alveo, etc.)
- [x] Compilation pipeline: extract BOM from all used drivers, write `bom/parts.json` + `bom/parts.csv` into `.tptpkg`
- [x] Element BOM: extract component list from generated SPICE netlist (resistor values, tolerances, memristor specs)
- [ ] Observer UI: "BOM" tab with parts list and supplier links; one-click CSV export
- [ ] JLCPCB integration: generate JLCPCB-compatible BOM + CPL from Element's KiCad output for automated PCB assembly quotes

---

## Hardware Cost Estimator

- [x] Add `[pricing]` section to driver manifest: typical unit price range, supplier URL
- [ ] Observer UI: cost estimate shown on target selection screen before compilation
- [x] Estimate breakdown: component cost × node count + PCB fab estimate + board cost
- [x] "Cheap / Medium / Expensive" tier badge on each hardware target card
- [ ] Link to actual supplier pages; display caveat that prices are estimates

---

## First-Run Guided Wizard (Observer UI)

- [ ] Implement 5-step wizard flow in Observer shown on first launch
- [ ] Step 1: model picker (file, Spark model selector, HuggingFace URL)
- [ ] Step 2: auto-run pre-flight check; show traffic-light results per hardware type
- [ ] Step 3: hardware picker with cost estimates + BOM previews; "no hardware yet" path → recommend ESP32 swarm + SiL
- [ ] Step 4: compilation with auto-quantization on by default
- [ ] Step 5: "Flash or Emulate?" — offer flash if USB device detected, otherwise launch SiL
- [ ] Save wizard state; make it skippable and re-launchable from help menu

---

## Model Accuracy Validator (`validator/`)

- [ ] Define standardized prompt suite for accuracy testing (diverse token types, edge cases)
- [ ] Implement reference backend connector: Spark IPC or local CPU inference
- [ ] Implement hardware output connector: reads inference results from live deployment or SiL
- [ ] Compute token-level similarity + perplexity delta between hardware and reference outputs
- [ ] For analog: report per-layer output voltage vs. SPICE-expected value
- [ ] Observer UI: accuracy dashboard tab with per-layer green/amber/red indicators
- [ ] CLI: `tpt-validate <model.tptpkg> --reference spark --hardware alloy`

---

## OTA Update System (`alloy/ota/`)

- [ ] Implement per-node firmware binary diff between new and previous `.tptpkg`
- [ ] Generate patch manifest: list of node IDs with changed binaries
- [ ] OTA flashing: push firmware only to changed nodes; unchanged nodes remain live during update
- [ ] Store previous firmware in `targets/alloy/firmware/prev/` inside `.tptpkg` for rollback
- [ ] Observer UI: OTA progress heatmap — per-node status (pending / flashing / done / failed)
- [ ] One-click rollback from Observer UI
- [ ] CLI: `tpt-alloy ota --pkg new.tptpkg --prev old.tptpkg --topology topology.json`

---

## Power Consumption Estimator + Monitor

- [ ] Add `[power]` section to driver manifest: idle mW, active mW/MHz, peak mW
- [ ] Pre-flight: compute total estimated power draw (active mW × node count + overhead)
- [ ] Include power estimate in pre-flight report and BOM output
- [ ] Observer telemetry: add optional power monitoring channel (INA219 or similar; shown only if hardware supports it)
- [ ] Element: extract power estimate from Xyce SPICE simulation results (already available)

---

## Hardware Diagnostics Mode

- [ ] Implement diagnostic test pattern runner (known-good inputs + expected outputs per hardware type)
- [ ] **Alloy diagnostics**: ping each node, measure RTT latency, check firmware version, report CPU temp
- [ ] **Fusion diagnostics**: run small test inference through FPGA; verify output vs. golden reference; check HBM bandwidth
- [ ] **Element diagnostics**: inject low-amplitude test signal; compare output to SPICE-predicted response; flag components outside tolerance
- [ ] Observer UI: hardware health heatmap — node grid (swarm), block diagram (FPGA), circuit diagram (analog), color-coded by health
- [ ] CLI: `tpt-diagnose <model.tptpkg> --hardware alloy|fusion|element`

---

## Hardware-in-the-Loop Training (`tpt-train/hardware_aware.py`)

- [ ] Design `TPTHardwareAwareCallback`: accepts hardware telemetry + CPU reference outputs, computes per-layer deviation profile
- [ ] Implement deviation-to-loss conversion: map per-layer output errors to a regularization term
- [ ] Wire callback into PyTorch training loop (runs after N steps when hardware telemetry is available)
- [ ] Validator integration: `tpt-validate` outputs a `.tptdeviation` file consumable by the callback
- [ ] Document workflow: train → deploy to SiL/hardware → collect deviations → fine-tune → recompile
- [ ] Test: measure accuracy delta before/after hardware-aware fine-tuning on TinyLlama + 16× ESP32 SiL

---

## Accessibility & Democratization

### WASM Browser Demo
- [ ] Configure Cargo targets to compile `tpt-catalyst` and `tpt-alloy` to WASM (`wasm32-unknown-unknown`)
- [ ] Expose WASM API: `compile(modelBytes, targetConfig)` → `.tptpkg` binary
- [ ] Wrap WASM in a Web Worker (non-blocking UI)
- [ ] Wire WASM SiL output to Observer frontend via in-browser WebSocket mock
- [ ] Build hosted demo page: drag-and-drop model file → compile → watch SiL swarm visualization
- [ ] Target: <60 seconds from page load to running SiL visualization for a quantized TinyLlama

### Pre-compiled Package Marketplace (`tpt-packages/`)
- [ ] Define package registry manifest format (JSON index: model ID, hardware target, accuracy delta, SHA-256, download URL)
- [ ] CLI: `tpt get <package-name>` — downloads and verifies `.tptpkg` from registry
- [ ] CLI: `tpt packages list` — browse available pre-compiled packages
- [ ] Bootstrap registry with: TinyLlama Q4 × 16× ESP32, TinyLlama Q8 × Alveo
- [ ] Observer UI: "Get pre-compiled package" option on target selection screen
- [ ] Publish registry as static files on GitHub Releases (no server required)

### Open Hardware Reference Board (`hardware/reference-designs/alloy-carrier/`)
- [ ] Design 8-node ESP32 carrier board in KiCad: standardized bus connectors, shared 5V rail, UART headers, per-node LEDs
- [ ] Generate JLCPCB-compatible BOM + CPL (target: < $15 assembled per board)
- [ ] Write assembly guide (step-by-step, photos, ESP32 pinout reference)
- [ ] Validate board design against auto-discovery protocol and heartbeat firmware
- [ ] Publish KiCad source + Gerbers in repo; link from Observer first-run wizard

### One-Line Bootstrap / Developer Experience
- [ ] Restructure Python packaging: `pip install tpt-crucible` (base, SiL-only) + `[fpga]` and `[swarm]` extras
- [ ] First-run detection: if `[fpga]` extra not installed but FPGA target selected, show install instructions + SiL fallback offer
- [ ] Bundle `tpt-catalyst` and `tpt-alloy` WASM binaries in the pip package for offline browser demo
- [ ] Write 5-minute quickstart: `pip install tpt-crucible` → download TinyLlama → SiL run → see tokens/sec
- [ ] Test install experience on clean Windows, macOS, and Ubuntu VMs

---

## Infrastructure & Cross-Cutting

- [x] Initialize mono-repo (Rust workspace + Python packages + Go service + Next.js app)
- [x] Set up CI/CD pipeline (lint, test, build for all components)
- [x] Write developer onboarding docs / CONTRIBUTING.md
- [ ] Set up docs site (architecture overview, module API references)
- [ ] Define versioning and release strategy (open-core vs. proprietary layers)
- [ ] License: choose open-core licensing (e.g., Apache 2.0 for compilers, commercial for optimization layers)
