# TPT Crucible — Industry Context & Business Case

---

## The Problem: AI at the Edge of Physics

The AI compute market has consolidated around a single paradigm: large GPU clusters running transformer workloads. This works well for cloud inference and training, but it leaves an enormous surface area of real-world deployment scenarios either underserved or completely unaddressed.

**Three constraints expose the limits of the GPU model:**

1. **Power budgets** — GPUs require hundreds of watts per chip. Deploying AI into embedded systems, IoT devices, or field hardware is physically constrained by power, not by software.
2. **Latency** — Sending data to a cloud GPU and receiving results introduces unavoidable round-trip latency. Real-time control systems (robotics, industrial automation, sensor fusion) cannot tolerate this.
3. **Cost at scale** — A datacenter GPU is a $10,000–$30,000 device. Deploying AI across thousands of edge nodes using this hardware is cost-prohibitive. The economics simply do not scale.

The alternatives that exist today — NVIDIA Jetson, Intel Neural Compute Stick, Google Coral TPU — are purpose-built inference accelerators. They are better than cloud GPUs for edge deployment, but they are still black boxes: closed hardware, proprietary toolchains, vendor lock-in, and a complete inability to target custom or experimental hardware.

**TPT Crucible exists to solve the toolchain problem**: the absence of a compiler that can take any standard AI model and target non-GPU, non-ASIC hardware — FPGAs, analog compute circuits, microcontroller swarms, compute-in-memory arrays, and neuromorphic chips.

---

## Industry Landscape

### The GPU Supply Chain Monopoly

The AI hardware market is currently dominated by NVIDIA with ~80–90% market share in AI accelerator revenue. AMD and Intel occupy small secondary positions. This concentration gives a single vendor enormous leverage over pricing, availability, and roadmap decisions.

The NVIDIA CUDA ecosystem creates deep platform lock-in: PyTorch, TensorFlow, JAX, and virtually every production ML framework are built around CUDA primitives. This is not a technical inevitability — it is a historical accident reinforced by network effects.

The consequences are well-documented:
- H100/H200 GPUs were supply-constrained for 18+ months post-launch
- Cloud GPU pricing increases are passed directly to inference costs
- Edge deployment remains either impossible (too much power/cost) or dependent on purpose-built vendor ASICs

### The Emerging Heterogeneous Compute Layer

Several independent hardware trends are converging toward a world where AI compute happens on radically different substrates:

| Hardware Type | Representative Devices | Key Advantage |
|---|---|---|
| FPGA | Xilinx Alveo, Intel Agilex, Lattice ECP5 | Reconfigurable; custom datapath; low latency |
| Microcontroller Swarm | ESP32, RP2040, RISC-V MCUs | Ultra-low cost; massively parallel; field-deployable |
| Analog Compute | Memristor arrays, CIM chips | Extreme energy efficiency; physics-native matrix ops |
| Compute-in-Memory | Taalas HC1, Axelera Europa, D-Matrix DIMC | Memory-compute co-location; eliminates data movement bottleneck |
| Neuromorphic | Intel Loihi, BrainScaleS, SpiNNaker | Event-driven; near-zero idle power; time-series native |
| Silicon Photonics | Lightmatter Passage, LightOn OPUs | Speed-of-light inference; near-zero energy per MAC |

Each of these hardware families has dedicated research communities and, in most cases, production hardware available today. What none of them have is a **general-purpose compiler** that can take an arbitrary trained AI model and produce a deployable artifact.

That is the gap TPT Crucible fills.

---

## Who This Is For

### Primary: Hardware-Constrained AI Deployment Teams

Engineers deploying AI inference where GPUs are physically impossible or economically unviable:

- **Industrial IoT** — Predictive maintenance models running on factory floor hardware, where a GPU is not an option and cloud latency is unacceptable
- **Defence and field systems** — Edge inference with no network connectivity, strict power envelopes, and tamper-resistance requirements
- **Agricultural and environmental sensing** — Distributed sensor networks running AI classification on harvested energy
- **Medical devices** — Real-time signal classification (ECG, EEG, EMG) on battery-powered, FDA-regulated hardware
- **Embedded robotics** — Low-latency motor control and perception pipelines where round-trip cloud inference adds 50–200ms of latency

### Secondary: Hardware Researchers and Academics

Research groups building novel compute hardware need a way to run real AI workloads on their designs without writing a custom compiler for every model. TPT Crucible provides the compiler layer; researchers provide the hardware driver. This dramatically lowers the barrier to benchmarking new architectures against established models.

### Tertiary: Cost-Sensitive Commercial Inference

At sufficient scale, the economics of custom hardware compilation become compelling even for workloads that could run on GPUs. A company running millions of inference requests per day on a narrow model category (text classification, embedding, small language models) may find that a custom FPGA or CIM deployment has 5–20x better cost-per-inference than cloud GPU.

---

## Performance Comparison: Custom Hardware vs. GPU

These comparisons are workload-dependent and hardware-specific. The following characterizes the general tradeoff landscape.

### Latency

| Scenario | GPU (Cloud) | GPU (Local, e.g. RTX 4090) | FPGA (e.g. Alveo U250) | MCU Swarm (16x ESP32) |
|---|---|---|---|---|
| Small transformer (TinyLlama, 1.1B) | 20–80ms (network dependent) | 8–20ms | 5–15ms (custom pipeline) | 30–120ms |
| Embedding / classification (BERT-tiny) | 15–40ms (network) | 3–8ms | 1–5ms | 10–40ms |
| Inference on harvested power | Impossible | Impossible | Possible with duty cycling | Possible |

**Key insight:** FPGAs can match or beat local GPU latency on specific workloads because the entire datapath is customised for the model — there is no general-purpose overhead. An FPGA running a fixed transformer topology can sustain inference at near-theoretical memory bandwidth limits.

### Throughput

FPGAs and CIM arrays are not necessarily faster than high-end GPUs on throughput-optimised batch workloads. The GPU's advantage is raw FLOP count and mature software pipelining. The custom hardware advantage is in *sustained, low-latency, single-request throughput* — the use case of real-time inference, not batch processing.

### Energy Efficiency

This is where custom hardware is categorically superior:

| Hardware | Typical Inference Power | Notes |
|---|---|---|
| NVIDIA H100 | 350–700W (full chip) | Idle power ~100W; rarely below 200W under inference load |
| NVIDIA RTX 4090 | 100–300W | Best local option; still impractical for embedded |
| Xilinx Alveo U250 | 25–75W | Custom datapath; scales with model complexity |
| ESP32 Swarm (16 nodes) | 2–8W | Each node 125–500mW; feasible on battery |
| Analog CIM (e.g. Taalas HC1) | <1W | Near-thermodynamic minimum for matrix operations |
| Neuromorphic (Intel Loihi 2) | 0.5–5W | Event-driven; approaches zero idle |

For battery-powered, energy-harvesting, or thermally constrained deployments, the difference is not marginal — it is the difference between possible and impossible.

---

## Cost Comparison

### Hardware Cost (per inference node)

| Hardware | Approximate Unit Cost | Notes |
|---|---|---|
| NVIDIA H100 (PCIe) | $25,000–$35,000 | Datacentre card; not field-deployable |
| NVIDIA RTX 4090 | $1,600–$2,000 | Consumer; not ruggedised or embedded |
| Xilinx Alveo U250 | $3,000–$5,000 | Production FPGA; re-programmable per model |
| Lattice ECP5 FPGA | $15–$60 | Small FPGA; suitable for classification workloads |
| ESP32 (per node) | $4–$8 | Swarm of 16: ~$100 total hardware cost |
| RP2040 (per node) | $1–$3 | Ultra-low cost; constrained memory |
| Analog CIM tile | $50–$500 | Production cost estimates; varies by supplier |

### Total Cost of Ownership at Scale

Consider a deployment of 1,000 inference nodes for edge AI classification (e.g. industrial fault detection, agricultural disease classification):

| Approach | Hardware Cost (1,000 nodes) | Annual Power Cost | Notes |
|---|---|---|---|
| Cloud GPU (shared inference) | $0 upfront + API pricing | ~$50–200K/year (depends on volume) | Requires connectivity; latency variable |
| Edge GPU (Jetson AGX Orin) | ~$1,500 × 1,000 = $1.5M | ~$80/node/year = $80K/year | Capable but expensive; vendor-locked |
| ESP32 Swarm (16-node per site) | ~$100–200 × 1,000 = $100–200K | <$5/node/year = <$5K/year | Requires TPT Crucible to compile |
| FPGA per node (mid-range) | ~$100–500 × 1,000 = $100–500K | ~$20/node/year = $20K/year | Requires TPT Crucible to compile |

The ESP32 and FPGA options are 5–15x cheaper to deploy and 10–50x cheaper to operate over a 3-year horizon — but they require a compiler to be usable. That compiler is TPT Crucible.

---

## The Toolchain Gap: Why This Doesn't Already Exist

### The Standard Toolchain Assumption

Every major AI compiler — TVM, XLA, TensorRT, ONNX Runtime, Core ML — was built with the assumption that the target hardware has a GPU-like execution model: a flat memory hierarchy, SIMD parallelism, and floating-point MAC arrays. The compiler stack was designed to target hardware that already exists and is already dominant.

None of these tools can target:
- A swarm of 16 ESP32 microcontrollers communicating over WiFi
- An FPGA where the entire compute datapath is synthesised per-model
- An analog circuit where weights are encoded as physical component values
- A CIM array where computation occurs inside the memory cells themselves

### Why the Gap Persists

1. **Research-production disconnect.** Hardware research papers describe novel compute substrates but ship MATLAB or Python simulation code, not production compilers.
2. **Narrow-hardware tooling.** Companies like Xilinx (Vitis AI), Lattice (sensAI), and ST (STM32Cube.AI) build compilers for *their own hardware only*. There is no hardware-agnostic layer.
3. **Driver ecosystem absence.** Even if a compiler existed, a new board requires someone to manually write synthesis constraints, pin maps, and flash protocols — a task that currently requires deep hardware expertise and produces non-reusable artifacts.
4. **Analog and neuromorphic are pre-commercial.** The tools to target these substrates are research prototypes. A production-grade compiler for these targets has no incumbent.

TPT Crucible addresses all four gaps: a hardware-agnostic IR, a community driver registry, and module coverage for FPGA, swarm, analog, CIM, and neuromorphic targets.

---

## Competitive Positioning

| Tool | FPGA | MCU/Swarm | Analog | CIM | Neuromorphic | Open Source | Hardware-Agnostic |
|---|---|---|---|---|---|---|---|
| **TPT Crucible** | Yes | Yes | Yes | Yes (Gap 1) | Yes (Gap 2) | Yes | Yes |
| Xilinx Vitis AI | Yes | No | No | No | No | Partial | No (Xilinx only) |
| TVM / Apache | Limited | Limited | No | No | No | Yes | Partial |
| TensorRT | No | No | No | No | No | No | No (NVIDIA only) |
| STM32Cube.AI | No | ST chips only | No | No | No | No | No |
| ONNX Runtime | Partial | No | No | No | No | Yes | Partial |
| lava-nc (Intel) | No | No | No | No | Loihi only | Yes | No |

The closest competitor in philosophy is Apache TVM. TVM is excellent at targeting GPU-class hardware and has some MCU support (microTVM). It does not target FPGAs at the synthesis level, does not target analog circuits, and has no concept of a distributed swarm execution model. TPT Crucible is complementary to TVM in some respects (Catalyst uses TVM for operator fusion) while targeting a different deployment surface area entirely.

---

## The Open-Core Model and Community Flywheel

TPT Crucible is designed as an open-core project:

- **Open:** MLIR IR dialect, compiler passes, hardware module backends, driver SDK, SiL emulator
- **Open:** Community driver registry (hardware contributors add support for new boards without forking)
- **Proprietary (optional):** AI-assisted optimisation passes (quantization search, topology advisor, RTL assistant), cloud synthesis worker managed hosting, advanced hardware IP locking

The driver registry is the network-effects moat. As more hardware drivers are contributed, the platform becomes more valuable to every user — each new board benefits the entire community. This mirrors the npm/PyPI model for software packages, applied to hardware support.

The pre-compiled package marketplace extends this: once someone compiles TinyLlama for a 16-node ESP32 swarm, every subsequent user of that hardware configuration gets that compilation instantly, turning a multi-hour synthesis step into a cache hit.

---

## Strategic Timing

Several industry shifts are converging:

- **Model size plateau.** Frontier models are growing more slowly; inference efficiency is now the primary competitive axis. This increases interest in specialised hardware.
- **Edge AI regulatory push.** GDPR, HIPAA, and similar frameworks create pressure to process sensitive data locally rather than sending it to cloud endpoints.
- **FPGA commoditisation.** Lattice, Efinix, and GoAI are producing low-cost FPGAs ($10–$50 range) that are viable for widespread edge deployment — but require compiler support to target.
- **Post-von Neumann interest.** CIM and neuromorphic hardware are transitioning from research curiosity to commercial availability. The compiler layer does not yet exist; the hardware will be stranded without it.
- **RISC-V adoption.** Custom RISC-V cores with ML extensions are viable today (SiFive X series, Espressif C-series). TPT Crucible's RISC-V ISA generation (Gap 8) positions it to target this category natively.

---

## Summary

TPT Crucible is a compiler for the part of the AI deployment landscape that existing tools were never designed to serve: hardware where GPUs are impossible, economically unviable, or physically constrained out of scope.

The value proposition is simple:
- **Take any standard AI model.** (PyTorch, ONNX, GGUF, TensorFlow)
- **Target any non-GPU hardware.** (FPGA, MCU swarm, analog compute, CIM, neuromorphic)
- **Without writing a custom compiler.** (driver SDK + community registry handles new boards)

The market is not competing with NVIDIA for datacenter workloads. It is serving the deployment scenarios that NVIDIA cannot serve — and that no current compiler addresses.

---

*TPT Crucible is part of the TPT software ecosystem alongside [TPT Spark](https://github.com/PhillipC05/tpt-spark), a local GGUF runtime. Spark runs models on standard hardware; Crucible compiles them for custom hardware.*
