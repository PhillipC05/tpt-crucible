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

### TPT Fusion — Fast Model Switching (Overlay Hot-Swap)
- [ ] Implement hot-swap protocol: load new `.fusecfg` + weight binary into running overlay without re-flashing the bitstream
- [ ] DMA weight loader: stream model weights from host NVMe → FPGA HBM over PCIe at full bandwidth; target <60s switch time for any model that fits the overlay config
- [ ] Implement model config cache in HBM: reserve a fixed HBM region per slot (configurable N slots); track slot occupancy + LRU eviction when all slots full
- [ ] HBM cache sizing: auto-calculate max slots from available HBM minus model weight size; expose `--cache-slots N` override in CLI
- [ ] CLI: `tpt-fusion load <model.fusecfg>` — hot-load weights to a running overlay; no bitstream flash required
- [ ] CLI: `tpt-fusion cache list` — show HBM slot occupancy, model name, size, last-used timestamp
- [ ] CLI: `tpt-fusion cache evict <model>` — manually free an HBM slot
- [ ] Observer UI: model switcher panel — list of loaded configs in HBM cache with slot indicators; one-click switch; estimated load time shown for uncached models
- [ ] Define overlay compatibility check: verify `.fusecfg` datapath width and layer count match the installed overlay before attempting load; clear error if incompatible
- [ ] Benchmark: measure end-to-end model switch time (unload → transfer → load → first token) on Alveo U250

### TPT Fusion — Multi-Overlay Management
- [ ] Define overlay manifest format: each overlay bitstream tagged with supported datapath (dense/MoE), precision (INT4/INT8), max layer count, max model size
- [ ] Ship at least two reference overlays for Alveo U250: `dense-int4` (covers standard transformer models) and `moe-int4` (covers MoE routing with expert gating)
- [ ] Implement overlay switcher: detect which overlay is currently flashed; if incoming `.fusecfg` requires a different overlay type, auto-flash the correct one (~5–10 min, user notified)
- [ ] Cache current overlay type in a local state file so `tpt-fusion load` can skip the compatibility check on repeat invocations
- [ ] Observer UI: show active overlay type + compatible model families in the sidebar; warn before auto-switching overlay
- [ ] CLI: `tpt-fusion overlay list` — show available overlays for the connected board
- [ ] CLI: `tpt-fusion overlay flash <overlay-name>` — manually flash a specific overlay

### Phase 2 Milestone
- [ ] **DEMO:** Select Xilinx Alveo in UI → TPT Fusion outputs bitstream → flash board → runs quantized AI model using HBM

---

## Automation & Pipeline Intelligence

### Toolchain Error Handling
- [x] Build error interception layer in Fusion tool wrappers (Yosys, Nextpnr): parse stderr, match against pattern catalog, emit structured error type
- [x] Build error catalog: ~30 common Yosys/Nextpnr failure patterns (timing closure, missing module, resource overflow) → plain-English messages + suggested action
- [x] Build equivalent error catalog for Xyce/ngspice (Element) and PlatformIO (Alloy)
- [ ] Observer UI: show structured error message + suggested action; "raw output" toggle for advanced users
- [ ] LLM fallback: if error doesn't match catalog and LLM provider is configured, send full error + context → show "AI Diagnosis" panel in Observer
- [ ] CLI: structured errors also printed to stderr in JSON format for CI/CD consumption

### `tpt-doctor` Toolchain Verifier (`python/tpt_catalyst/doctor.py`)
- [x] Detect and version-check all required external tools: Yosys, Nextpnr, PlatformIO, Xyce/ngspice, Verilator
- [x] Report: installed / wrong version / missing, with platform-specific install instructions per tool
- [ ] Run end-to-end smoke test: compile a minimal 2-layer model through each available hardware path
- [x] Output: green/amber/red per tool; overall readiness score
- [x] CLI: `tpt-doctor` (check all) and `tpt-doctor --target alloy|fusion|element`
- [ ] Integrate into first-run wizard: auto-run `tpt-doctor` on first Observer launch, show results inline

### Quantization Auto-Search Loop (Catalyst)
- [ ] Implement `--quantize auto --accuracy-budget <float>` flag in Catalyst ingest CLI
- [ ] Search strategy: start all layers at INT4 → run fast SiL accuracy check or `.tptprofile` sensitivity delta → promote fragile layers to INT8 until budget is met
- [ ] Add mixed-precision mode: `--quantize mixed-precision` — uses per-layer sensitivity from `.tptprofile` to assign bit-widths independently
- [ ] Emit per-layer quantization decision log into `.tptpkg` for auditability
- [ ] Observer UI: show per-layer quantization map (INT4 = green, INT8 = amber, float = red) after search completes

### Streaming Pre-flight + One-Click Auto-Fix
- [x] Refactor pre-flight graph scan to emit results as a stream (channel/iterator) rather than a blocking report
- [ ] Go backend: expose pre-flight stream as a WebSocket event feed
- [ ] Observer UI: operators flash pass/warn/fail in the Visual IR Graph Editor as they're checked
- [x] Add `fix` action to each pre-flight warning: deterministic substitutions (Flash Attention → MHA, SwiGLU → GELU, RMSNorm → LayerNorm) applied on click
- [ ] Show diff preview for ambiguous substitutions; require confirmation before apply
- [ ] Export fixed IR back to `.tptir` automatically after applying fixes

### Automatic Accuracy Regression on Recompile
- [ ] On every `tpt-catalyst pack` invocation, check for existing `.tptpkg` for same model+target in working directory
- [ ] If prior package found: auto-launch validator in background (SiL), diff accuracy vs. prior package
- [ ] Observer UI: show regression badge (▲ improved / ▼ regressed / = unchanged) on new package card
- [ ] Block flash (with override option) if regression exceeds configurable threshold (default 2%)
- [ ] CLI: `--no-regression-check` flag to skip for CI environments that run it separately

### Parallel Firmware Flashing (Alloy OTA enhancement)
- [ ] Detect WiFi-capable nodes (ESP32); default to parallel OTA broadcast when WiFi configured
- [ ] USB fallback: detect all connected USB hubs, distribute node flashing across ports in parallel
- [ ] Flash progress: per-node status in Observer OTA heatmap (pending → flashing → done → failed)
- [ ] Estimate total flash time before starting; show progress bar with ETA
- [ ] CLI: `tpt-alloy flash --parallel` (USB) / `tpt-alloy flash --ota` (WiFi)

### SiL Communication Parameter Auto-Tuner (Alloy)
- [ ] Define tunable parameters: WiFi message size, batch size, retry count, UART baud rate
- [ ] Implement SiL latency sweep: iterate parameter combinations, measure p99 inter-node latency in virtual swarm
- [ ] Select parameter set that minimizes p99 latency within firmware memory budget
- [ ] Bake tuned parameters into generated firmware as compile-time constants
- [ ] Report: show tuned parameters vs. defaults and expected latency improvement in Observer
- [ ] CLI: `tpt-alloy tune <model.tptpkg> --topology topology.json` → outputs `tuned_params.json`

### SPICE Dataset Auto-Generation Pipeline (Element)
- [ ] Define parametric sweep space: component tolerance (±1/5/10%), temperature range (-20°C to 85°C), supply voltage variance (±10%), circuit topology variants
- [ ] Implement sweep orchestrator: enumerate parameter combinations, generate SPICE netlist per combo, submit to synthesis worker queue
- [ ] Worker integration: Xyce jobs run on synthesis worker cluster (same Docker infra as FPGA synthesis)
- [ ] Collect results: capture output voltages, power dissipation, failure modes per run
- [ ] Auto-train Reality Check ML model when dataset reaches threshold (e.g., 5,000 runs)
- [ ] Ship pre-trained Reality Check checkpoint with the repo; auto-update when new dataset is larger
- [ ] CLI: `tpt-element generate-dataset --runs 10000 --worker-url <url>`

### HuggingFace Model Search in Wizard (`python/tpt_catalyst/hf_search.py`)
- [x] Integrate `huggingface_hub` search API: search by name/tag, filter by model size, quantization type, task
- [x] Display results in Observer wizard step 1: model cards with size, quant type, license, download size
- [ ] One-click download: fetch GGUF or SafeTensors to local model directory (shared with Spark layout)
- [ ] Show download progress in wizard; auto-advance to step 2 when complete
- [ ] Cache model index for offline use; refresh on demand

---

## AI Acceleration Features

### LLM Error Diagnosis (Observer + tool wrappers)
- [ ] Add LLM fallback hook to error interception layer: triggered when structured catalog returns no match
- [ ] Build context bundle: full stderr + model size/operator count + target board + synthesis flags
- [ ] Send context to pluggable LLM provider; render response as "AI Diagnosis" panel in Observer
- [ ] "Apply suggestion" button if LLM response includes a specific actionable fix
- [ ] Log LLM diagnoses locally for future catalog expansion
- [ ] Hidden entirely when no LLM provider is configured

### Mixed-Precision Quantization Search (Catalyst AI pass)
- [ ] Extend auto-search loop to support per-layer bit-width assignment (not just uniform INT4/INT8)
- [ ] Use `.tptprofile` activation sensitivity scores to rank layers by quantization fragility
- [ ] Implement greedy promotion: sort layers by sensitivity, promote until accuracy budget is met
- [ ] Fallback when `.tptprofile` absent: use gradient-free sensitivity estimation (small perturbation test per layer)
- [ ] Benchmark: compare uniform INT4 vs. mixed-precision on TinyLlama accuracy + compression ratio

### Synthesis Constraint Auto-Tuner (Fusion AI pass)
- [ ] Define tunable synthesis parameter space: Yosys strategy (area/speed/balanced), effort level, ABC passes; Nextpnr routing seed, timing margin
- [ ] Log synthesis job outcomes to synthesis worker: (parameters + model shape) → (timing slack, LUT utilization, duration)
- [ ] Train regression model on accumulated job logs to predict optimal parameters given model shape + board
- [ ] Integrate predictor as pre-synthesis pass: set Yosys/Nextpnr parameters automatically before invoking tools
- [ ] Fallback: use sensible defaults when predictor hasn't accumulated enough data yet
- [ ] Observer UI: show predicted vs. actual timing slack after each synthesis run to validate predictor

### Predictive Compile Time Estimator (Fusion + Observer)
- [ ] Log synthesis job durations to synthesis worker alongside model shape metadata
- [ ] Train regression model: (operator count, tensor shapes, board, synthesis mode) → predicted time (minutes)
- [ ] Observer UI: show "Estimated compile time: ~X–Y min" with confidence interval before user confirms compile
- [ ] Update estimate live as synthesis progresses (remaining time = predicted − elapsed)
- [ ] Show historical compile times for same model+board in a tooltip

### AI-Generated Validation Prompt Suite (Validator)
- [ ] Extract model domain hint from GGUF model card metadata (description, tags, model_type)
- [ ] LLM prompt: "Given a model trained for [domain], generate 50 diverse test prompts that stress-test domain-specific vocabulary and edge cases"
- [ ] Combine LLM-generated prompts with fixed 20-prompt standard suite
- [ ] Cache generated suite per model ID to avoid re-generation on every validation run
- [ ] Hidden when no LLM provider configured; falls back to standard 20-prompt suite only

### Bandwidth-Weighted Partition Graph (Alloy)
- [ ] Add communication volume estimator pass before METIS: traverse TPT-IR edges, compute byte volume per edge (tensor dtype × shape × batch size)
- [ ] Annotate partition graph edge weights with byte volumes
- [ ] Pass weighted graph to METIS (already supports edge weights via `adjwgt` parameter)
- [ ] Benchmark: compare unweighted vs. bandwidth-weighted partitioning on inter-node traffic in SiL

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
- [x] Set up React + Next.js frontend
- [x] Implement Tailwind CSS "industrial blueprint" dark theme (dark grays, neon cyan/amber, monospaced data fonts)
- [x] Build unified telemetry dashboard view (all hardware types in one UI)
- [x] Integrate Three.js / React Three Fiber for 3D swarm topology visualizer (nodes + wires)
- [ ] Integrate Three.js / React Three Fiber for PCB layout visualizer (Analog module)
- [x] Build tokens-per-second live chart
- [x] Build memory bandwidth utilization live chart (FPGA)
- [x] Build thermal drift live chart (Analog)
- [x] Build node-latency heatmap (Swarm)

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

- [x] Integrate React Flow into Observer Next.js frontend
- [x] Render TPT-IR as interactive DAG (nodes = operators, edges = tensor shapes/dtypes)
- [x] Show pre-flight compatibility warnings as inline node badges
- [ ] Allow operator swap (right-click → substitute with compatible op)
- [ ] Allow quantization pass insertion between nodes
- [x] Allow layer-to-hardware tagging for Mosaic hybrid deployment
- [ ] Export modified IR back to `.tptir` file

---

## TPT Observer — Telemetry Replay & Time-Travel Debug

- [x] Define `.tptlog` binary format (timestamped telemetry stream + inference metadata)
- [x] Go backend: record all active telemetry streams to `.tptlog` on user request
- [x] Observer UI: replay scrub bar with per-token step navigation (pause/play/step)
- [ ] Overlay mode: compare two `.tptlog` files side-by-side (e.g., before/after firmware update)
- [ ] Emit replay telemetry through same Observer chart components as live data

---

## TPT Spark Integration

- [x] Detect TPT Spark model directory at startup; expose as model source in Catalyst UI
- [x] Catalyst CLI: accept Spark model ID as input (`tpt-catalyst ingest --spark-model llama3-8b`)
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
- [x] Observer: display `.tptpkg` manifest metadata (model name, targets, checksums, readiness score) in UI

---

## TPT Drivers — Hardware Driver SDK & Registry (`drivers/`)

- [x] Define hardware driver interface spec (Rust trait + Python protocol): board identity, pin/resource map, synthesis constraints, telemetry adapter, flash protocol
- [x] Implement driver loader: resolve drivers by name/version from local cache or registry
- [x] Build driver types: FPGA board profiles, MCU variants (ESP32, RP2040, RISC-V), analog component libraries
- [x] Migrate existing Xilinx Alveo board profile to driver format as reference implementation
- [x] Build community registry index format (TOML manifest, versioned, signed)
- [x] CLI: `tpt-drivers install <driver-name>` — downloads and caches driver from registry
- [x] CLI: `tpt-drivers list` — show installed drivers; `tpt-drivers search <query>`
- [x] Implement recipe system: `tpt-drivers install tinyllama-esp32-16node` pulls a verified topology + driver bundle
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
- [x] CLI flag: `tpt-catalyst pack --incremental` - skip operators whose hash matches cache
- [ ] Observer UI: show per-layer cache hit/miss indicators during compilation
- [x] Cache invalidation: bust cache for a layer when its inputs, weights, or target hardware change

---

## Hardware-Aware Training Hooks (`tpt-train/`)

- [x] Implement `TPTProbeCallback` for PyTorch: attaches to all layers, records min/max activations, weight histograms, gradient norms per epoch
- [ ] Implement equivalent JAX/Flax hook
- [x] Output: `model.tptprofile` JSON (per-layer activation stats + weight distributions)
- [x] Catalyst integration: if `.tptprofile` exists alongside model, use it to set per-layer quantization clamps
- [x] Auto-Quantization Advisor: prefer `.tptprofile` data over static weight analysis when available
- [x] Add `.tptprofile` reference to `.tptpkg` manifest if profile was used during compilation
- [ ] Publish `tpt-train` as a standalone pip package (`pip install tpt-train`)

---

## Cloud Synthesis Worker — Self-Hostable (`cloud/synthesis-worker/`)

- [x] Go worker service: accept `.tptpkg` upload, run Yosys + Nextpnr, return updated `.tptpkg` with bitstream
- [x] Redis-based job queue (stateless workers, horizontally scalable)
- [ ] Observer UI: "Offload synthesis to worker" toggle (shown only when a worker URL is configured in settings)
- [x] Dockerfile + Docker Compose for single-node deployment
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

- [x] Implement PDF/URL datasheet text extractor (PyMuPDF for PDF, BeautifulSoup for URLs)
- [x] Define structured LLM extraction prompt: extract pinout, memory map, peripheral specs, flash protocol, clock/timing
- [x] LLM output → driver manifest TOML + Rust trait skeleton + synthesis constraints + flash protocol stub
- [ ] Observer UI: diff-style preview of generated driver; user edits and approves
- [ ] Run SDK schema validator on generated driver before allowing publish to registry
- [ ] "Publish to Registry" flow from the review screen
- [ ] LLM backend: uses same pluggable provider interface as NL Hardware Config

---

## AI Swarm Topology Advisor (`alloy/ai-topology/`)

- [x] Define input schema: TPT-IR profile (layer count, bandwidth matrix) + user constraints (node count, latency budget, power budget, form factor)
- [x] Implement LLM-based topology recommendation (initial approach)
- [ ] Define training data schema: (model profile + constraints + topology) → measured SiL performance
- [ ] Accumulate SiL run results as training data automatically
- [ ] Train ML model on accumulated SiL data when dataset is large enough; swap in as default
- [ ] Output: ranked topology recommendations (ring/mesh/star/tree/hybrid) with predicted latency + power
- [ ] Observer UI: 3D preview of each recommended topology; one-click "use this" to feed into Alloy partitioner

---

## AI RTL Assistant (`fusion/ai-rtl/`)

- [x] Implement compute pattern extractor from TPT-IR (layer types, tensor shapes, dtypes, repetition count)
- [x] Build LLM prompt template: compute pattern + board constraints → candidate Verilog MAC array
- [x] Implement static timing pre-check on generated Verilog (wrap OpenTimer or `yosys stat`)
- [x] Flag timing violations with suggested datapath modifications before full synthesis
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

- [x] Implement 5-step wizard flow in Observer shown on first launch
- [x] Step 1: model picker (file, Spark model selector, HuggingFace URL)
- [x] Step 2: auto-run pre-flight check; show traffic-light results per hardware type
- [x] Step 3: hardware picker with cost estimates + BOM previews; "no hardware yet" path → recommend ESP32 swarm + SiL
- [x] Step 4: compilation with auto-quantization on by default
- [x] Step 5: "Flash or Emulate?" — offer flash if USB device detected, otherwise launch SiL
- [ ] Save wizard state; make it skippable and re-launchable from help menu

---

## Model Accuracy Validator (`validator/`)

- [x] Define standardized prompt suite for accuracy testing (diverse token types, edge cases)
- [x] Implement reference backend connector: Spark IPC or local CPU inference
- [x] Implement hardware output connector: reads inference results from live deployment or SiL
- [x] Compute token-level similarity + perplexity delta between hardware and reference outputs
- [ ] For analog: report per-layer output voltage vs. SPICE-expected value
- [ ] Observer UI: accuracy dashboard tab with per-layer green/amber/red indicators
- [ ] CLI: `tpt-validate <model.tptpkg> --reference spark --hardware alloy`

---

## OTA Update System (`alloy/ota/`)

- [x] Implement per-node firmware binary diff between new and previous `.tptpkg`
- [x] Generate patch manifest: list of node IDs with changed binaries
- [x] OTA flashing: push firmware only to changed nodes; unchanged nodes remain live during update
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

- [x] Implement diagnostic test pattern runner (known-good inputs + expected outputs per hardware type)
- [x] **Alloy diagnostics**: ping each node, measure RTT latency, check firmware version, report CPU temp
- [x] **Fusion diagnostics**: run small test inference through FPGA; verify output vs. golden reference; check HBM bandwidth
- [x] **Element diagnostics**: inject low-amplitude test signal; compare output to SPICE-predicted response; flag components outside tolerance
- [ ] Observer UI: hardware health heatmap — node grid (swarm), block diagram (FPGA), circuit diagram (analog), color-coded by health
- [ ] CLI: `tpt-diagnose <model.tptpkg> --hardware alloy|fusion|element`

---

## Hardware-in-the-Loop Training (`tpt-train/hardware_aware.py`)

- [x] Design `TPTHardwareAwareCallback`: accepts hardware telemetry + CPU reference outputs, computes per-layer deviation profile
- [x] Implement deviation-to-loss conversion: map per-layer output errors to a regularization term
- [x] Wire callback into PyTorch training loop (runs after N steps when hardware telemetry is available)
- [x] Validator integration: `tpt-validate` outputs a `.tptdeviation` file consumable by the callback
- [x] Document workflow: train → deploy to SiL/hardware → collect deviations → fine-tune → recompile
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
- [x] Define package registry manifest format (JSON index: model ID, hardware target, accuracy delta, SHA-256, download URL)
- [x] CLI: `tpt get <package-name>` — downloads and verifies `.tptpkg` from registry
- [x] CLI: `tpt packages list` — browse available pre-compiled packages
- [x] Bootstrap registry with: TinyLlama Q4 × 16× ESP32, TinyLlama Q8 × Alveo
- [ ] Observer UI: "Get pre-compiled package" option on target selection screen
- [ ] Publish registry as static files on GitHub Releases (no server required)

### Open Hardware Reference Board (`hardware/reference-designs/alloy-carrier/`)
- [ ] Design 8-node ESP32 carrier board in KiCad: standardized bus connectors, shared 5V rail, UART headers, per-node LEDs
- [ ] Generate JLCPCB-compatible BOM + CPL (target: < $15 assembled per board)
- [ ] Write assembly guide (step-by-step, photos, ESP32 pinout reference)
- [ ] Validate board design against auto-discovery protocol and heartbeat firmware
- [ ] Publish KiCad source + Gerbers in repo; link from Observer first-run wizard

### One-Line Bootstrap / Developer Experience
- [x] Restructure Python packaging: `pip install tpt-crucible` (base, SiL-only) + `[fpga]` and `[swarm]` extras
- [x] First-run detection: if `[fpga]` extra not installed but FPGA target selected, show install instructions + SiL fallback offer
- [ ] Bundle `tpt-catalyst` and `tpt-alloy` WASM binaries in the pip package for offline browser demo
- [x] Write 5-minute quickstart: `pip install tpt-crucible` → download TinyLlama → SiL run → see tokens/sec
- [ ] Test install experience on clean Windows, macOS, and Ubuntu VMs

### Docker-First Distribution (Setup Friction Reduction)
- [x] Build `tpt-crucible/synthesis` Docker image: Yosys + Nextpnr + MLIR + full toolchain pre-installed; no host toolchain required
- [x] Build `tpt-crucible/runtime` Docker image: minimal XRT + Crucible runtime for machines with a physical FPGA card
- [ ] Write XRT one-line kernel module installer script (`install-xrt.sh`): handles Ubuntu version detection, kernel header install, XRT deb install, card detection verify; target <15 min on a clean Ubuntu LTS
- [ ] Publish both images to Docker Hub; version-pin to matching XRT + Yosys releases to eliminate version mismatch errors
- [ ] Update `tpt-doctor` to detect Docker-based toolchain as valid alternative to host-installed tools
- [ ] Observer UI: "Run synthesis in Docker" toggle — shown when Docker is detected but host toolchain is absent; routes synthesis jobs through the container transparently
- [ ] Document Docker path as the recommended setup route in quickstart guide

### Windows-Native Support
- [ ] Bundle pre-compiled Yosys and Nextpnr Windows binaries in the `[fpga]` pip extra — eliminate build-from-source requirement on Windows
- [ ] Implement WSL2 auto-setup helper: detect WSL2 availability, install Ubuntu 22.04 distro, configure XRT inside WSL2, verify card passthrough; one command from PowerShell
- [ ] Test and document Alveo U250 XRT passthrough on Windows 11 via WSL2
- [ ] Write Windows-specific quickstart guide covering Docker Desktop path as primary and WSL2 as alternative
- [ ] CI: add Windows install smoke test (pip install + tpt-doctor) to CI pipeline

---

## Infrastructure & Cross-Cutting

- [x] Initialize mono-repo (Rust workspace + Python packages + Go service + Next.js app)
- [x] Set up CI/CD pipeline (lint, test, build for all components)
- [x] Write developer onboarding docs / CONTRIBUTING.md
- [ ] Set up docs site (architecture overview, module API references)
- [ ] Define versioning and release strategy (open-core vs. proprietary layers)
- [ ] License: choose open-core licensing (e.g., Apache 2.0 for compilers, commercial for optimization layers)

---

## Gap Features — Competitive Differentiation

### Gap 1: TPT Silicon — Compute-in-Memory Backend (`python/tpt_silicon/`)

No general-purpose compiler exists for arbitrary model → CIM. Targets Taalas HC1, Axelera Europa, D-Matrix DIMC.

- [x] Create `python/tpt_silicon/` module (pyproject.toml + package scaffold)
- [x] `weight_packer.py` — `CimWeightPacker`: quantize + tile weight tensors into memory array row format (row = single MAC unit); `PackedArray` dataclass; `serialize_array()` → bytes
- [x] `array_layout.py` — `CimArrayLayout`: map TPT-IR ops to array dimensions; tile large matmuls across multiple physical arrays; `LayoutConfig` dataclass (array_rows, array_cols, bit_precision)
- [x] `bitline.py` — `BitlineOpGenerator`: emit bitline read/accumulate/ADC-skip op sequences as low-level op list; handle partial-row masking for sparse tiles
- [ ] `package_writer.py` — `write_silicon_artifacts()`: write `targets/silicon/` into `.tptpkg` (weight_arrays.bin, layout.json, config.json)
- [ ] `cli.py` — `tpt-silicon compile <model.tptir> --board <name> [--precision 4|8]`
- [ ] Add `HardwareTarget.CIM` to `python/tpt_mosaic/tpt_mosaic/partition.py`
- [ ] Dispatch CIM target in `python/tpt_mosaic/tpt_mosaic/orchestrator.py`
- [ ] Add CIM column to operator support matrix in `python/tpt_catalyst/tpt_catalyst/compat.py`
- [ ] Add `"cim"` hardware_type + `CimArraySpec` dataclass to `python/tpt_drivers/tpt_drivers/driver.py`
- [ ] Add `"silicon"` to target name set in `crates/tpt-catalyst/src/package.rs`
- [ ] Observer UI: CIM target card in hardware picker with array utilization metric

### Gap 2: TPT Pulse — Neuromorphic / ANN→SNN Compiler (`python/tpt_pulse/`)

No production open-source ANN→SNN compiler exists. Targets Intel Loihi (lava-nc) and BrainScaleS (PyNN).

- [ ] Create `python/tpt_pulse/` module scaffold
- [ ] `lif_node.py` — `LifNeuron` dataclass (threshold, decay, reset_mode: subtract|zero); `SnnGraph` (nodes + spike_edges)
- [ ] `converter.py` — `SnnConverter`: walk TPT-IR ops; replace ReLU activations with LIF nodes; normalize thresholds via `.tptprofile` max-activation if available, else weight-norm heuristic
- [ ] `lava_export.py` — `LavaExporter`: write `targets/pulse/lava_network.py` (Intel Loihi lava-nc API)
- [ ] `pynn_export.py` — `PynnExporter`: write `targets/pulse/pynn_network.py` (BrainScaleS/SpiNNaker via PyNN)
- [ ] `sim_export.py` — `SimExporter`: pure-Python LIF simulation for SiL testing without neuromorphic hardware
- [ ] `package_writer.py` — write `targets/pulse/` (snn_graph.json + backend export + accuracy_estimate.json)
- [ ] `cli.py` — `tpt-pulse convert <model.tptir> --target loihi|brainscales|sim`
- [ ] Add `HardwareTarget.NEUROMORPHIC` to partition.py; dispatch in orchestrator.py
- [ ] Add `"neuromorphic"` hardware_type + `NeuromorphicSpec` to driver.py
- [ ] Add neuromorphic column to compat.py operator support matrix
- [ ] Observer UI: neuromorphic target card; show spike rate + accuracy estimate metrics

### Gap 3: Carbon-Aware Compilation

No compiler offers a `--optimize carbon` flag. Power data already in driver manifests; adds grid carbon intensity + cost function.

- [x] `python/tpt_catalyst/tpt_catalyst/carbon.py` — `GRID_INTENSITY_GCO2_PER_KWH` region map; `CarbonEstimate` dataclass; `estimate_carbon(target, driver, inference_time_s, region)`; `select_lowest_carbon_target(estimates)`
- [ ] Add `--optimize carbon` and `--carbon-region <region>` flags to `tpt-catalyst ingest` and `tpt-catalyst check` CLI
- [ ] Include `CarbonEstimate` per target in `CompatibilityReport` output
- [ ] Add optional `carbon_overhead_gco2: float` to `PowerProfile` in driver.py (embodied carbon amortisation)
- [ ] Add `carbon_profile: Option<CarbonProfile>` to `PackageManifest` in `crates/tpt-catalyst/src/package.rs`
- [ ] Observer UI: carbon cost column in hardware picker table; "lowest carbon" badge on recommended target
- [ ] CLI: `tpt-catalyst check model.tptir --optimize carbon --carbon-region eu` prints ranked carbon table

### Gap 4: Cross-Hardware Speculative Decoding (`python/tpt_mosaic/tpt_mosaic/speculative.py`)

Draft model on Alloy swarm + verify model on Fusion FPGA. Standard speculative decoding loop across physically separate hardware — native to Mosaic, impossible to replicate on single-hardware stacks.

- [x] `speculative.py` — `SpeculativeConfig` dataclass (draft_pkg, verify_pkg, gamma=4, acceptance_threshold=0.8); `SpeculativeOrchestrator.run(prompt_tokens)` async loop; `get_metrics()` → `SpeculativeMetrics`
- [x] Implement standard token acceptance criterion (probability ratio reject/accept) over Mosaic bridge
- [ ] Add `run_speculative(config)` method to `MosaicOrchestrator`
- [ ] Add `tpt-mosaic speculative --draft alloy.tptpkg --verify fusion.tptpkg --gamma 4` CLI command
- [ ] Add `SpeculativeMetrics` struct to Observer telemetry schema (`services/tpt-observer/internal/telemetry/schema.go`)
- [ ] Observer UI: speculative decoding dashboard panel — acceptance rate gauge, draft vs. effective TPS comparison

### Gap 5: Hardware-Locked Model IP Protection

Cryptographically bind a `.tptpkg` to specific hardware serial numbers. Package refuses to load on mismatched hardware.

- [x] `python/tpt_catalyst/tpt_catalyst/ip_lock.py` — `HardwareLock` dataclass (fingerprint_sha256, lock_type, locked_at, issuer); `create_lock(hardware_ids)`; `verify_lock(lock, present_ids)`
- [x] `crates/tpt-catalyst/src/ip_lock.rs` — `HardwareLock` struct; `verify_lock()` called in `PackageReader::open()` before returning contents
- [ ] Add `hardware_lock: Option<HardwareLock>` to `PackageManifest` in package.rs
- [ ] Add `--lock-to-hardware <id1,id2,...>` flag to `tpt-catalyst pack` CLI
- [ ] Alloy firmware generator: embed fingerprint verification at boot before inference (reads node serial from efuse/OTP)
- [ ] Observer UI: lock icon + hardware IDs in package manifest view; "Locked" badge on locked packages
- [ ] CLI: `tpt-catalyst unpack` prints lock status; errors clearly on fingerprint mismatch

### Gap 6: Structured Sparsity Exploitation

2:4 sparsity (≥2 zeros per 4 weights) lets FPGA MAC arrays skip zero multiplications, halving compute. Source: `.tptprofile` activation_sparsity per layer.

- [x] `python/tpt_catalyst/tpt_catalyst/sparsity.py` — `SparsityMode` enum (NONE, TWO_FOUR, FOUR_EIGHT, AUTO); `SparsityPattern` dataclass; `SparsityAnalyzer.analyze(ir, profile)`; `enforce_2_4(weights)` pruning function
- [x] `python/tpt_fusion/tpt_fusion/sparse_mac.py` — `SparseMacArray`: Amaranth HDL with skip-zero gating; compressed index sidecar for routing non-zero values
- [ ] Add `sparsity_map: dict[str, SparsityPattern]` to `QuantizationProfile` in `python/tpt_catalyst/tpt_catalyst/quantize.py`
- [ ] Extend `MacConfig` with `sparsity_mode: SparsityMode`; dispatch to `SparseMacArray` in `mac_array.py`
- [ ] Add `--sparsity auto|2:4|4:8|none` flag to `tpt-catalyst ingest` CLI
- [ ] Observer UI: per-layer sparsity map in IR Graph Editor (density heatmap overlay)

### Gap 7: Community Compilation Cache

FPGA synthesis takes hours. A content-addressed public registry turns repeated compilations of common model+board combos from hours to seconds.

- [x] `python/tpt_catalyst/tpt_catalyst/community_cache.py` — `CommunityCacheClient.lookup(model_sha256, board, synthesis_flags)`; `publish(tptpkg_path, ...)`; local index cache with 1h TTL
- [ ] `cloud/synthesis-broker/internal/cache/cache.go` — `CacheClient` struct; `Lookup(modelSHA, board, flagsHash)` called before synthesis job dispatch in broker.go
- [ ] Define `community_cache_index.json` schema: array of `{model_sha256, board, flags_hash, download_url, verified_at, accuracy_delta}`
- [ ] Add `--community-cache` / `--no-community-cache` flags to `tpt-catalyst pack` CLI
- [ ] Integrate `CacheClient.Lookup()` into `cloud/synthesis-broker/internal/broker/broker.go` dispatch path
- [ ] Bootstrap index with TinyLlama Q4 × Alveo U250 entry on GitHub Releases
- [ ] Observer UI: "Using community build (saved ~4h synthesis)" notification on cache hit

### Gap 8: RISC-V Custom ML ISA Generation (`python/tpt_alloy/tpt_alloy/riscv_isa.py`)

Generate per-model RISC-V custom instructions (using RISC-V custom opcode spaces) as Chisel source, then synthesize to soft-core RISC-V FPGA — bridges Alloy and Fusion.

- [x] `riscv_isa.py` — `RiscVCustomOp` dataclass (mnemonic, opcode_space, funct3, funct7, latency_cycles); `RiscVExtensionGenerator.analyze(ir)` profiles op frequency; `generate_chisel(ops)` emits Chisel3 VexRiscV plugin source; `generate_gnu_binutils_patch(ops)` emits GAS assembler extension
- [ ] Add `tpt-alloy riscv-isa <model.tptir> [--top-n 8] --output <dir>` subcommand to Alloy CLI
- [ ] Add `--riscv-ext <custom_ext.scala>` flag to `tpt-fusion generate` CLI; include extension in soft-core synthesis when provided
- [ ] Observer UI: RISC-V ISA panel showing generated instructions with estimated speedup per op

### Gap 9: TPT Photon — Photonic Backend Stub (`python/tpt_photon/`)

Experimental forward-looking backend for silicon photonics inference (MZI mesh). No open-source compiler exists. Targets Lightmatter Passage, LightOn OPUs. Marked EXPERIMENTAL throughout.

- [x] Create `python/tpt_photon/` module scaffold
- [x] `mzi_mesh.py` — `MziMeshGenerator`: SVD decompose weight matrix (Clements decomposition); `phase_encode(U)` → MZI phase angles (radians); `MziConfig` dataclass (mesh_size, phase_angles, nonlinearity)
- [ ] `package_writer.py` — write `targets/photon/` (phase_config.json, mzi_layout.json, EXPERIMENTAL marker)
- [ ] `cli.py` — `tpt-photon compile <model.tptir>` (prints EXPERIMENTAL warning prominently)
- [ ] Add `HardwareTarget.PHOTONIC` (experimental flag) to partition.py; dispatch in orchestrator.py
- [ ] Add `"photonic"` hardware_type + `PhotonicSpec` (mesh_size, wavelength_nm, modulation) to driver.py
- [ ] Observer UI: photonic target card with EXPERIMENTAL badge; phase angle visualizer

### Gap 10: Intermittent / Energy-Harvesting Computing Support

Batteryless sensors lose power mid-inference. Checkpoint ops in TPT-IR let firmware save and resume state across power cycles.

- [x] `python/tpt_catalyst/tpt_catalyst/intermittent.py` — `CheckpointGranularity` enum (LAYER, BLOCK, OPERATOR); `IntermittentProfile` dataclass; `CheckpointPlanner.insert_checkpoints(ir, profile)`; `estimate_energy_per_layer(ir, driver)`; `validate_budget(ir, profile)` → budget warnings
- [ ] Add `--intermittent`, `--checkpoint-granularity layer|block|operator`, `--energy-budget-mj <float>` flags to `tpt-catalyst ingest` CLI
- [ ] Alloy firmware generator: recognise `tpt.checkpoint` ops; emit EEPROM write/read around boundaries; add power-monitor ISR hook (GPIO voltage-drop interrupt)
- [ ] Add `checkpoint_storage: str | None` and `power_monitor_pin: str | None` to `DriverManifest` in driver.py
- [ ] Observer UI: energy budget progress bar; checkpoint marker overlay on IR graph timeline; estimated inferences per harvest cycle

### Gap Features — Cross-Cutting Changes

- [ ] `python/tpt_mosaic/tpt_mosaic/partition.py` — extend `HardwareTarget` enum: add CIM, NEUROMORPHIC, PHOTONIC
- [ ] `python/tpt_drivers/tpt_drivers/driver.py` — add `CimArraySpec`, `NeuromorphicSpec`, `PhotonicSpec` dataclasses; extend hardware_type literals; add `carbon_overhead_gco2` to `PowerProfile`; add `checkpoint_storage` + `power_monitor_pin` to `DriverManifest`
- [ ] `crates/tpt-catalyst/src/package.rs` — add `hardware_lock: Option<HardwareLock>` and `carbon_profile: Option<CarbonProfile>` to `PackageManifest`
- [ ] `services/tpt-observer/internal/telemetry/schema.go` — add `SpeculativeMetrics` and `CarbonMetrics` structs
