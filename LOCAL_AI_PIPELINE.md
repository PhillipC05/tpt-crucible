# Building a Local AI Pipeline with TPT Crucible
### Hardware Tiers, Model Sizing, and What You Can Actually Achieve

---

## Why Local at All?

Before choosing hardware, the case for local AI inference is worth making explicit. Cloud inference (OpenAI API, Anthropic, Google) gives you the best models with zero infrastructure cost — but you pay in three ways: **per-token cost**, **latency**, and **data sovereignty**. At any significant volume, local inference becomes cheaper. For real-time applications, it becomes faster. For regulated industries, it becomes mandatory.

The GPU-local approach (a workstation with an RTX 4090, or a server with an A100) solves the cloud problems but introduces its own: high capital cost, high power draw, active cooling requirements, and vendor lock-in to CUDA. TPT Crucible opens a third path: custom hardware that is purpose-built for your model, your workload, and your power budget.

---

## The Three Model Tiers

AI models are most practically categorised by their **VRAM/memory footprint at inference time**, since that dictates what hardware can physically hold the model. The quantization format matters as much as the parameter count — a 7B model in Q4_K_M is ~4GB; the same model in float16 is ~14GB.

---

## Tier 1: The Embedded Tier
### Models under ~8GB — Small and Quantized

**Representative models:**

| Model | Parameters | Format | Memory Footprint |
|---|---|---|---|
| TinyLlama | 1.1B | Q4_K_M | ~0.6GB |
| Phi-3 Mini | 3.8B | Q4_K_M | ~2.2GB |
| Gemma 2 2B | 2B | Q4_K_M | ~1.3GB |
| Qwen2.5 1.5B | 1.5B | Q4_K_M | ~0.9GB |
| Llama 3.2 3B | 3B | Q4_K_M | ~2.0GB |
| Mistral 7B | 7B | Q4_K_M | ~4.1GB |
| Llama 3.1 8B | 8B | Q4_K_M | ~4.7GB |

**Best suited hardware:**

### Option A — MCU Swarm (ESP32 / RP2040)
*Best for: ultra-low cost, battery-powered, distributed field deployment*

A 16-node ESP32 swarm gives you roughly 64MB of combined PSRAM across nodes — enough for TinyLlama Q4 with careful KV cache sharding. Each node handles a partition of the model's layers; inference is pipelined across the chain.

- **Cost:** ~$80–$150 total hardware
- **Power:** 2–5W continuous (battery viable; solar viable)
- **Throughput:** 0.5–3 tokens/sec (TinyLlama on 16x ESP32)
- **Latency (first token):** 2–6 seconds
- **Best for:** Keyword extraction, classification, on-device assistants in constrained environments, always-on inference in sensor nodes

Scale to 32 nodes and you can push Phi-3 Mini or Llama 3.2 3B at comparable speeds. The swarm is inherently fault-tolerant — a node can drop out mid-inference and neighbouring nodes absorb the layers.

### Option B — Entry FPGA (Lattice ECP5, iCE40 HX8K, Efinix Trion)
*Best for: low-latency, deterministic inference, industrial control loops*

Entry FPGAs in the $30–$100 range have enough logic cells for small quantized models. TPT Fusion synthesises a custom MAC array datapath — every clock cycle does useful work for your specific model, unlike a GPU running generalised CUDA kernels.

- **Cost:** $30–$150 (FPGA board); no ongoing cost
- **Power:** 1–8W
- **Throughput:** 3–15 tokens/sec depending on clock rate and model
- **Latency (first token):** 50–300ms
- **Best for:** Real-time signal classification, embedded control, deterministic latency requirements (medical devices, robotics)

### Option C — Analog Compute (Element)
*Best for: lowest possible energy; physics-based inference*

For classification workloads (not autoregressive generation), analog compute encodes the model weights as physical component values. Inference is literally a voltage propagating through a resistor network — power consumption can drop to microwatts.

- **Cost:** $50–$500 for a custom PCB run; KiCad files output directly from TPT Element
- **Power:** Microwatts to milliwatts
- **Throughput:** Microsecond inference (not token-by-token; entire forward pass at once)
- **Best for:** Always-on classification sensors, implantables, energy harvesting nodes

Analog is not suitable for autoregressive language generation — it excels at fixed-size inference tasks: image classification, anomaly detection, signal labelling.

**GPU comparison at Tier 1:**

| | RTX 4090 | RTX 3060 (12GB) | ESP32 Swarm | Entry FPGA |
|---|---|---|---|---|
| Hardware cost | ~$1,800 | ~$300 | ~$100 | ~$80 |
| Power (inference) | 150–300W | 60–130W | 2–5W | 1–8W |
| Tokens/sec (TinyLlama) | 120–200 | 60–100 | 0.5–3 | 3–15 |
| Latency (first token) | <100ms | <150ms | 2–6s | 50–300ms |
| Battery viable? | No | No | Yes | Yes |
| Offline capable? | Yes | Yes | Yes | Yes |

*The GPU wins on raw throughput by an order of magnitude. The custom hardware wins on cost, power, and deployability — especially in constrained or field environments.*

---

## Tier 2: The Workstation Tier
### Models 8–24GB — The Sweet Spot for Most Tasks

**Representative models:**

| Model | Parameters | Format | Memory Footprint |
|---|---|---|---|
| Mistral 7B | 7B | Q8_0 | ~7.7GB |
| Llama 3.1 8B | 8B | Q8_0 | ~8.5GB |
| Gemma 2 9B | 9B | Q4_K_M | ~5.5GB |
| Llama 3.1 70B | 70B | Q2_K | ~18GB |
| Qwen2.5 14B | 14B | Q4_K_M | ~8.7GB |
| Mistral Small 22B | 22B | Q4_K_M | ~13GB |
| Qwen2.5 32B | 32B | Q4_K_M | ~19GB |
| DeepSeek-R1 14B | 14B | Q4_K_M | ~9GB |
| CodeLlama 34B | 34B | Q4_K_M | ~20GB |

This tier covers the models that most people actually want to run locally for serious work: coding assistants, document analysis, research tools, long-context summarisation.

**Best suited hardware:**

### Option A — Mid-to-High FPGA (Xilinx Alveo U250, Intel Agilex, Xilinx VU9P)
*Best for: production inference, low latency, high throughput without cloud costs*

The Alveo U250 has 64GB of HBM2 across 4 stacks — enough to hold any model in this tier in INT8 or even float16 without compression. TPT Fusion synthesises INT4 and INT8 MAC arrays with HBM auto-routing, achieving memory bandwidth utilisation that GPU inference cannot match because there is no general-purpose overhead.

- **Cost:** $3,000–$7,000 (PCIe card; fits in any workstation)
- **Power:** 35–75W at full inference load
- **Throughput:** 15–60 tokens/sec (8B Q8 model)
- **Latency (first token):** 80–400ms
- **Best for:** Developer workstations, on-premise API servers, regulated-data environments, production edge appliances

For INT4-quantized models (where accuracy loss is acceptable), FPGA throughput improves significantly because INT4 MAC arrays fit more compute in the same logic area.

### Option B — Hybrid Mosaic Deployment (FPGA + MCU Swarm)
*Best for: spreading a large model across both fast and cheap hardware*

The Mosaic orchestrator can split a model across hardware types — attention layers on a fast FPGA (deterministic, bandwidth-hungry), FFN layers on a cheaper MCU swarm (embarrassingly parallel, cheap). A Qwen2.5 32B model that won't fit on a single mid-range FPGA becomes tractable when the 60% FFN parameter mass runs on a 64-node ESP32 swarm while attention heads run on a smaller FPGA.

- **Cost:** ~$800–$2,000 (small FPGA + swarm hardware)
- **Power:** 15–35W combined
- **Throughput:** 3–12 tokens/sec (depending on inter-hardware bridge speed)
- **Best for:** Budget-constrained production deployments; research into hybrid execution

### Option C — Large MCU Swarm (64–128 nodes)
*Best for: volume deployment where per-node cost is paramount*

A 64-node ESP32 swarm has ~256MB combined PSRAM. With INT4 quantization, a Mistral 7B model (originally ~4GB) can be distributed across this swarm. At 128 nodes, 8–12B INT4 models become viable.

- **Cost:** ~$400–$800 (64 nodes at ~$6–$8 each)
- **Power:** 8–16W
- **Throughput:** 1–5 tokens/sec
- **Best for:** Deployments where per-node cost must be under $10; massively scaled edge deployments (thousands of units)

**GPU comparison at Tier 2:**

| | RTX 4090 (24GB) | A6000 (48GB) | Alveo U250 | 64-node Swarm |
|---|---|---|---|---|
| Hardware cost | ~$1,800 | ~$4,000 | ~$5,000 | ~$500 |
| Power (inference) | 200–350W | 200–300W | 35–75W | 8–16W |
| Tokens/sec (Llama 3.1 8B Q8) | 80–120 | 90–130 | 15–60 | 1–5 |
| Tokens/sec (32B Q4) | 20–40 | 30–50 | 10–25 | 0.5–2 |
| Power per token | High | High | 3–5x better | 20–50x better |
| Rack deployable? | With effort | Yes | Yes | Yes |
| Offline / airgapped? | Yes | Yes | Yes | Yes |

---

## Tier 3: The Large Model Tier
### Models 24GB–70GB+ — High-Capability, Frontier-Adjacent

**Representative models:**

| Model | Parameters | Format | Memory Footprint |
|---|---|---|---|
| **Llama 3.1 70B** | **70B** | **Q4_K_M** | **~42GB** |
| Llama 3.3 70B | 70B | Q4_K_M | ~42GB |
| Qwen2.5 72B | 72B | Q4_K_M | ~44GB |
| DeepSeek-R1 70B | 70B | Q4_K_M | ~42GB |
| Mistral Large 123B | 123B | Q4_K_M | ~74GB |
| Llama 3.1 405B | 405B | Q2_K | ~214GB |

These are the models that match or approach frontier capability. Running them locally means either accepting significant GPU hardware cost ($8,000–$50,000+) or finding a creative deployment approach.

**Best suited hardware:**

### Option A — High-End FPGA with HBM (Xilinx Alveo U280, Alveo U55C, AMD Instinct equivalent)
*Best for: dedicated inference appliance; best performance-per-watt in the tier*

The Alveo U280 has 8GB HBM2 + 32GB DDR4 = ~40GB addressable. With INT4 quantization, a 70B model (42GB Q4) is at the edge of what fits; the U55C at 16GB HBM goes further with careful weight streaming. TPT Fusion handles HBM auto-routing automatically.

- **Cost:** $6,000–$12,000
- **Power:** 50–150W (vs. 350–700W for an H100)
- **Throughput:** 8–25 tokens/sec (70B Q4)
- **Best for:** Dedicated production inference appliances; organisations that run a fixed model continuously and cannot justify cloud at scale

### Option B — Multi-FPGA Mosaic Deployment
*Best for: highest throughput without GPU costs*

Two Alveo U250 cards in one server (total 128GB HBM) can hold a 70B model in INT8 across both cards. TPT Mosaic handles the inter-card split at the IR level, generating a communication bridge between the two FPGAs over PCIe.

- **Cost:** ~$10,000–$15,000 (2× Alveo + server)
- **Power:** 80–160W combined FPGA load
- **Throughput:** 20–50 tokens/sec (pipelined across two FPGAs)
- **Best for:** On-premise inference servers for large organisations; regulated industries that cannot use cloud

### Option C — FPGA + Large MCU Swarm (Mosaic Hybrid)
*Best for: maximising capability per dollar*

A hybrid approach runs attention heads on an FPGA (where bandwidth is critical) and the massive FFN blocks on a 256-node swarm (where the embarrassing parallelism of per-layer computation maps naturally). For a 70B model, the FFN represents ~65% of parameters — moving that to cheap swarm hardware is economically significant.

- **Cost:** ~$4,000–$8,000 (mid-range FPGA + 256-node swarm)
- **Power:** 30–60W
- **Throughput:** 3–10 tokens/sec
- **Best for:** Cost-conscious deployments; research; deployments that can tolerate lower throughput for a large cost saving

---

## If You Want to Run a 24GB Model: The Specific Answer

A 24GB footprint typically means one of:
- Llama 3.1 70B in Q2_K (~24GB) — heavily quantized; some quality loss
- Qwen2.5 32B in Q4_K_M (~19–22GB) — well-quantized; excellent quality
- DeepSeek-R1 32B in Q4_K_M (~19GB)
- Mistral Small 22B in Q8_0 (~24GB) — near-lossless quality

### Recommended path: Single Alveo U250 + TPT Fusion

The Alveo U250's 64GB HBM holds a 24GB model comfortably, with headroom for KV cache. TPT Fusion synthesises INT4 MAC arrays automatically, so the physical FPGA logic is right-sized for the model you're running.

**What you get:**
- 20–45 tokens/sec sustained throughput
- 35–75W power draw (compare: RTX 4090 at 200–350W for similar throughput on the same model)
- Zero per-token cloud cost after hardware purchase
- Full data sovereignty — nothing leaves your premises
- Deterministic latency — no shared-GPU cloud throttling

**What you give up vs. an RTX 4090:**
- Raw throughput ceiling — an RTX 4090 at 80–100 tokens/sec on a 24GB model edges ahead at peak
- Ease of setup — GPU inference is `llama.cpp` or `ollama`; FPGA requires initial setup (~1 hour via Docker) and a one-time compile per novel model (1–4 hours, offloadable to a synthesis worker)
- Model switching — switching between models already in HBM cache is <1 second; loading a fresh model from NVMe takes ~90 seconds; novel models with no community cache hit require a compile step

**What you gain vs. an RTX 4090:**
- 3–5× lower power consumption (meaningful at scale or for 24/7 operation)
- No vendor lock-in — the driver SDK means you can target multiple FPGA boards
- Hardware IP locking — your compiled model package can be cryptographically bound to specific hardware serial numbers
- No CUDA dependency — the toolchain is fully open-source

### Budget alternative: Dual Alveo U50 (total 32GB HBM)
- Two Alveo U50 cards (~$1,500–$2,500 each used)
- Mosaic splits the model across both cards
- ~10–20 tokens/sec; significantly lower power

### GPU equivalent comparison:

| | RTX 4090 (24GB) | Alveo U250 | 2× Alveo U50 | Cloud (API) |
|---|---|---|---|---|
| Upfront cost | ~$1,800 | ~$5,000 | ~$3,000–5,000 | $0 |
| Monthly operating cost (24/7) | ~$25–40/mo power | ~$5–10/mo power | ~$4–8/mo power | $200–2,000/mo (volume-dependent) |
| Tokens/sec (24GB model) | 40–80 | 20–45 | 10–20 | 40–120 (shared; variable) |
| Data stays local? | Yes | Yes | Yes | No |
| Recompile needed per model? | No | Yes (~1–4h) | Yes | N/A |
| Break-even vs. cloud (1M tok/day) | ~3–4 months | ~5–6 months | ~3–5 months | Never |

---

## Building a Complete Local Pipeline

Regardless of which hardware tier you choose, the TPT Crucible pipeline works the same way:

```
1. Pick your model
   └── GGUF / HuggingFace / SafeTensors

2. Run pre-flight check
   └── tpt-catalyst check model.tptir --target fusion
   └── See pass/warn/fail per operator; auto-fix suggestions

3. Compile
   └── tpt-catalyst ingest model.gguf --quantize auto --target fusion
   └── TPT Fusion synthesises FPGA bitstream (or Alloy generates firmware)
   └── Output: model.tptpkg

4. Flash or emulate
   └── Flash: tpt-alloy flash model.tptpkg (MCU swarm)
   └── Flash: tpt-fusion flash model.tptpkg --board alveo (FPGA)
   └── Emulate: tpt-emulate model.tptpkg --hardware fusion (SiL, no hardware required)

5. Monitor
   └── Observer dashboard: tokens/sec, memory bandwidth, thermal, node health
```

The SiL emulator (step 4, emulate path) means you can validate the entire pipeline — including performance estimates — before purchasing any hardware. This removes the traditional risk of "buy expensive FPGA, discover the model doesn't fit."

---

## Decision Framework: Which Tier for Which Use Case

| Use Case | Model Size | Recommended Hardware | Why |
|---|---|---|---|
| On-device assistant, IoT | <4GB Q4 | ESP32 swarm (16 nodes) | Cost and power dominate |
| Field sensor classification | Any | Analog (Element) | Near-zero power; fixed inference |
| Developer workstation | 4–8GB | Entry FPGA or small swarm | Low cost; adequate throughput |
| Coding assistant (24/7) | 8–24GB | Alveo U250 | Best power efficiency at this tier |
| On-premise API server | 8–70GB | Multi-FPGA Mosaic | Throughput + no cloud dependency |
| Research / experimentation | Any | SiL emulator | Validate before hardware purchase |
| Regulated industry (medical, finance) | Any | Any local hardware | Data never leaves premises |
| Budget large-model deployment | 24–70GB | FPGA + swarm hybrid | Best capability per dollar |
| Highest throughput, lowest latency | Any | High-end FPGA | Deterministic custom datapath |

---

## The Honest Tradeoff Summary

Custom hardware compiled with TPT Crucible is not a universal replacement for GPUs. For workloads where you need to swap models frequently, need the absolute highest throughput, or are running batch inference jobs, a high-end GPU is still the pragmatic choice.

Where custom hardware wins — sometimes definitively — is:
- **Anywhere power is a constraint** (embedded, battery, solar, thermal envelope)
- **Anywhere cost at scale is a constraint** (deploying thousands of nodes)
- **Anywhere data sovereignty is non-negotiable** (regulated industries, defence)
- **Anywhere you need deterministic latency** (industrial control, real-time systems)
- **Anywhere you're running one model continuously** (dedicated inference appliances)

The GPU paradigm assumes general-purpose hardware. Custom hardware compiled per-model is always more efficient for that specific model — the question is whether the compilation cost and hardware investment are justified by the deployment requirements. For a significant fraction of real-world AI deployments, they are.
