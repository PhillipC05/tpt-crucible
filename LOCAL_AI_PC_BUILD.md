# Running Qwen 3.5 35B-A3B (MoE) and Qwen 3.5 27B (Dense) Locally
### A Practical Build Guide + TPT Crucible Comparison

---

## Understanding What These Models Actually Need

Before speccing hardware, it helps to understand what each model demands at the memory level.

### Qwen 3.5 35B-A3B (MoE — Mixture of Experts)

A MoE model has a two-tier parameter structure:
- **Total weights on disk:** 35B parameters. At Dynamic 4-bit quantization, that's roughly **17–19GB** of weight data
- **Active weights per inference step:** Only the ~3B "expert" parameters routed for each token are actually computed. The rest sit in memory, unused for that token.

This is the key insight: the model is large *in memory* but computationally light *per token*. The entire weight file must be loaded into VRAM (you cannot stream experts from disk at inference speed), but the compute budget per token is closer to a 3B dense model than a 35B dense model.

**Memory breakdown (Dynamic 4-bit, 24GB VRAM card):**
```
Model weights:    ~18GB
KV cache (8K ctx): ~2–3GB
Activations:       ~1GB
Headroom:          ~2–3GB
─────────────────────────
Total:             ~24GB   ← tight but viable
```

At a 24GB card you are near the ceiling. Context window is limited to roughly 8K–12K tokens before KV cache overflow. If you want 32K context, you need more VRAM.

### Qwen 3.5 27B (Dense)

A standard dense model — every parameter is active on every token. More compute per token, but no expert routing overhead.

**Memory breakdown (Q4_K_M, 24GB VRAM card):**
```
Model weights:     ~15GB
KV cache (16K ctx): ~5–6GB
Activations:        ~1GB
Headroom:           ~2GB
──────────────────────────
Total:              ~23–24GB   ← comfortable at 16K ctx
```

Q4_K_M hits the sweet spot: minimal perceptible quality loss versus Q8 for most tasks, and the 9GB of breathing room above the weights gives you a usable context window for long documents and coding sessions.

---

## The GPU PC Build — Recommended Specification

### Core Constraint: 24GB VRAM

Both models are designed to fit within 24GB VRAM. The only consumer GPU that meets this is the **NVIDIA RTX 4090**. Every other current consumer card either tops out at 16GB (RTX 4080 Super) or 12GB (RTX 4070 Ti Super), which cannot hold the MoE model in VRAM at all.

If you want to future-proof or run both models simultaneously (one loaded, one hot-swapped), professional/prosumer cards exist but at a significant price premium.

---

### Option 1 — The Recommended Build (RTX 4090)

| Component | Recommendation | Price (approx.) |
|---|---|---|
| **GPU** | NVIDIA RTX 4090 24GB | $1,600–$2,000 |
| **CPU** | AMD Ryzen 9 7900X or Intel Core i9-14900K | $300–$450 |
| **Motherboard** | ASUS ProArt X670E-Creator / MSI MEG Z790 ACE | $250–$400 |
| **RAM** | 64GB DDR5-6000 (2×32GB) | $160–$220 |
| **Primary Storage** | 2TB NVMe Gen4 (Samsung 990 Pro, WD Black SN850X) | $150–$200 |
| **Model Storage** | 4TB NVMe Gen4 (model library) | $250–$350 |
| **PSU** | 1000W 80+ Gold (ASUS ROG Thor, Seasonic Prime) | $180–$250 |
| **Cooling** | 360mm AIO liquid cooler | $120–$180 |
| **Case** | Full tower with good airflow (Fractal Torrent, Lian Li O11) | $150–$250 |
| **TOTAL** | | **~$3,200–$4,300** |

**Why 64GB system RAM?** The models themselves live in VRAM, but the inference runtime (llama.cpp, Ollama), the OS, and any applications running alongside need memory. 64GB also lets you buffer model files during load without pagefile thrashing, and gives headroom if you later run models in CPU-offload mode (slower but flexible).

**Why 4TB model storage?** At Q4 sizes, a 27B model is ~15GB and the 35B MoE is ~18GB. You will accumulate a library. 4TB gives you room for 50–80 large models without managing space constantly.

**Why a 1000W PSU?** The RTX 4090 has a 450W TDP. Under sustained inference load (not gaming — inference is sustained, not bursty), you should budget 500–550W for the GPU alone. Add 150W for a Ryzen 9 or Core i9 under load, plus board and drives, and a 1000W PSU gives you clean headroom without running at 90% capacity.

---

### Option 2 — Budget Build (RTX 4090 Used / RTX 3090)

| Component | Recommendation | Price (approx.) |
|---|---|---|
| **GPU** | RTX 4090 (used) or RTX 3090 24GB | $1,000–$1,400 |
| **CPU** | AMD Ryzen 7 7700X or Intel Core i7-13700K | $200–$280 |
| **Motherboard** | B650 or B760 mid-range | $150–$220 |
| **RAM** | 32GB DDR5-5600 | $90–$130 |
| **Storage** | 2TB NVMe + 2TB NVMe | $200–$300 |
| **PSU** | 850W 80+ Gold | $120–$160 |
| **Cooling + Case** | 240mm AIO + mid-tower | $150–$220 |
| **TOTAL** | | **~$1,900–$2,700** |

**RTX 3090 caveat:** The 3090 has the same 24GB VRAM but a significantly lower memory bandwidth (936 GB/s vs. 1,008 GB/s on the 4090) and slower CUDA cores. Inference throughput will be roughly 30–40% lower. For the MoE model specifically, the lower compute cost per token means this gap narrows — the 3090 is more competitive on MoE workloads than on dense models.

---

### Option 3 — Maximum Headroom Build (RTX 6000 Ada / A6000)

| Component | Recommendation | Price (approx.) |
|---|---|---|
| **GPU** | NVIDIA RTX 6000 Ada 48GB | $6,500–$8,000 |
| **CPU** | AMD Threadripper PRO 7960X or Xeon W | $1,500–$3,000 |
| **Motherboard** | WRX90 workstation board | $700–$1,200 |
| **RAM** | 128GB DDR5 ECC | $500–$800 |
| **Storage** | 4TB + 8TB NVMe | $600–$900 |
| **PSU** | 1600W 80+ Platinum | $350–$500 |
| **TOTAL** | | **~$10,000–$14,000** |

With 48GB VRAM you can load both models simultaneously (hot-swap in under 1 second), run the 35B MoE at full Q8 quality (not just Q4), and push context windows to 64K+ tokens without pressure. This is the right spec for a dedicated AI workstation used by a small team or for production-quality output.

---

## Performance Expectations

### Qwen 3.5 35B-A3B MoE — RTX 4090

| Setting | Tokens/sec | Context Window |
|---|---|---|
| Dynamic 4-bit (Q4_K_M) | **55–80 tok/s** | ~8–12K comfortable |
| Q8 quantization (if it fits) | 20–30 tok/s | ~4–6K |
| CPU offload (layers spilled to RAM) | 5–12 tok/s | Larger ctx possible |

The MoE model punches well above its weight here. Because only 3B parameters are active per token, an RTX 4090 can achieve throughput that would normally require a much smaller model. 55–80 tokens/sec means real-time streaming with visible output faster than most people can read. This is why the MoE architecture matters: you get 35B-scale quality at 3B-scale compute cost, within a 24GB memory budget.

### Qwen 3.5 27B Dense — RTX 4090

| Setting | Tokens/sec | Context Window |
|---|---|---|
| Q4_K_M (~15GB weights) | **30–50 tok/s** | ~16K comfortable |
| Q4_K_S (~14GB weights) | 32–52 tok/s | ~18K comfortable |
| Q5_K_M (~17GB weights) | 22–38 tok/s | ~10K |

The dense model is noticeably slower than the MoE because every parameter is active. 30–50 tok/s is still fast enough for interactive use — responses stream at a comfortable pace. The advantage over the MoE is quality on tasks requiring deep reasoning: the dense model has no expert routing overhead and applies its full 27B parameter capacity to every token.

---

## Software Stack

For a GPU PC build, you do not need TPT Crucible. The standard software stack handles these models natively:

### Recommended: Ollama
```bash
ollama run qwen3.5:35b-a3b-moe-q4_K_M
ollama run qwen3.5:27b-q4_K_M
```
Ollama handles model download, VRAM management, and exposes a local API endpoint. Dead simple; works on Windows, Mac, Linux. Hot-swaps models in ~2–5 seconds on NVMe storage.

### Alternative: LM Studio
A GUI for running local models. Good for non-technical users or when you want a clean chat interface. Uses llama.cpp as the backend. Drag-and-drop GGUF loading.

### Advanced: llama.cpp (direct)
Maximum control. Lets you tune KV cache size, rope scaling (extends context beyond training window), batch size, and thread allocation. Required if you want to do anything non-standard.

### For API integration (building apps on top):
```bash
# llama.cpp server mode — OpenAI-compatible API endpoint
./llama-server -m qwen3.5-27b-q4.gguf --port 8080 --ctx-size 16384
```
This exposes a local endpoint compatible with any OpenAI SDK. Your application sees it as `http://localhost:8080/v1` and works identically to calling the OpenAI API, with zero per-token cost.

---

## Where TPT Crucible Fits

For this specific use case — two large language models on a workstation GPU — **a GPU build is the right answer**. It is simpler, better supported, faster to set up, and flexible enough to swap models in seconds.

TPT Crucible becomes relevant when one of the following is true:

### Scenario 1: You want to deploy the same model to many nodes

If you are running inference on 10, 100, or 1,000 edge devices, buying an RTX 4090 per node is not viable. TPT Crucible compiles the 35B MoE or 27B dense model for FPGA or MCU hardware, bringing the per-node hardware cost from $1,800+ down to $100–$500 depending on target.

### Scenario 2: Power cost at scale

A workstation running an RTX 4090 for inference draws 400–600W. At 24/7 operation:
```
600W × 24h × 365 days = 5,256 kWh/year
At $0.15/kWh = ~$788/year in electricity
```
An Alveo U250 running the same model draws 50–80W:
```
80W × 24h × 365 = 701 kWh/year
At $0.15/kWh = ~$105/year in electricity
```
Over 5 years, the FPGA saves ~$3,400 in power alone — approaching the cost of the FPGA card itself. For always-on inference servers, this math becomes decisive.

### Scenario 3: Data sovereignty or airgapped environments

Both the GPU build and FPGA build run fully locally. But the FPGA path allows hardware IP locking — the compiled `.tptpkg` can be cryptographically bound to specific hardware serial numbers. This means your compiled model cannot be copied and run on unauthorised hardware, which matters in defence, medical, or commercial IP protection contexts.

### Scenario 4: The MoE architecture maps exceptionally well to FPGA

Because only ~3B of the 35B parameters are active per token, an FPGA synthesised for this specific routing pattern is extremely efficient. The TPT Fusion MAC arrays are sized for the *active* parameter budget, not the total parameter count. On a well-tuned Alveo U250, the 35B MoE model can match or exceed RTX 4090 tokens/sec while drawing 4–6× less power — the sparsity of MoE is a natural fit for custom hardware.

---

## Direct Comparison: This Specific Use Case

| | RTX 4090 Build | Used RTX 3090 Build | Alveo U250 (TPT Crucible) | ESP32 Swarm |
|---|---|---|---|---|
| **Total hardware cost** | ~$3,200–$4,300 | ~$1,800–$2,600 | ~$5,500–$7,000 | **~$13,000–$18,000** |
| **Nodes / cards required** | 1 GPU | 1 GPU | 1 FPGA | ~1,900–2,250 nodes |
| **Setup time** | 1–2 hours | 1–2 hours | ~1 hour (Docker path) | **Weeks to months** |
| **Model switch (HBM cached)** | 2–5 seconds | 2–5 seconds | **<1 second** | N/A |
| **Model switch (NVMe → HBM)** | 2–5 seconds | 2–5 seconds | **~90 seconds** | Hours |
| **Novel model, no cache** | 2–5 seconds | 2–5 seconds | 1–4h unattended | Not viable |
| **Tokens/sec (35B MoE Q4)** | 55–80 | 40–60 | 30–60 | **<0.1** |
| **Tokens/sec (27B Dense Q4)** | 30–50 | 22–38 | 20–40 | **Not viable** |
| **Power draw (inference)** | 400–600W | 350–420W | 50–80W | 120–180W |
| **Annual power cost (24/7)** | ~$700–$1,000 | ~$640–$770 | ~$90–$130 | ~$220–$330 |
| **Usable as a personal PC?** | Yes | Yes | No | No |
| **Verdict** | Best performance | **Best value for personal use** | Enterprise/production only | **Not viable at this model size** |

> **Why the ESP32 swarm doesn't work here:** The MoE model activates only 3B parameters per token, but all 35B parameters must sit in addressable memory so the router can reach the right experts. Each ESP32 has 8MB PSRAM — holding 18GB of weights requires ~2,250 nodes (~$15,750 in hardware alone), before wiring, power, and coordination overhead. The swarm is the right tool for models under ~2GB (TinyLlama, Phi-3 Mini); at 15–18GB it is more expensive than a GPU and orders of magnitude slower.

> **Crucible is not the right tool for a personal local AI PC.** The setup time, per-model compile requirement, and complete inability to casually swap or experiment with models make it a poor fit for workstation use. TPT Crucible is an industrial compiler — it belongs in a server room running a fixed model at scale, not on a desk.

---

## Bottom Line Recommendation

**For a personal local AI PC running these two models: build a GPU machine.**

The choice comes down to budget:

| Budget | Recommendation | Notes |
|---|---|---|
| ~$1,800–$2,600 | Used RTX 3090 + mid-range build | Best value; 24GB VRAM; 25–35% slower than 4090 |
| ~$3,200–$4,300 | New RTX 4090 + full build | Best performance; future-proof for larger models |
| ~$1,300–$1,500 | Mac Mini M4 Pro (24GB) | Lowest power; simplest setup; not upgradeable |

Install [Ollama](https://ollama.com) or [LM Studio](https://lmstudio.ai) and you are running both models within the hour. No synthesis pipeline, no compile steps, no driver SDK — pull a model and run it.

**Where TPT Crucible enters the picture:** Once you have validated these models meet your quality bar on the GPU workstation and decide to deploy them at scale — multiple servers, 24/7 operation, edge nodes — that is when the FPGA compile cost pays off. The GPU workstation becomes your development environment; Crucible handles production at scale. For a personal PC that you also use for other things, GPU is the only sensible answer.
