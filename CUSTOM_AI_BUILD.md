# Can You Build Custom AI Hardware Cheaper Than a GPU?
### Running Qwen 3.5 35B-A3B and Qwen 3.5 27B Without an RTX 4090

---

## The Honest Answer First

Yes — but with an important asterisk. The *cheapest upfront cost* is not the same as the *cheapest total cost*, and the answer depends on which you care about more.

For these specific models (15–18GB at Q4), you cannot escape a hardware minimum: you need somewhere between 18–24GB of fast memory. That memory costs money regardless of whether it lives on a GPU, an FPGA HBM stack, or a cluster of DRAM modules. What changes is how much compute surrounds that memory, how efficient the inference is, and what you pay in electricity every month.

Three distinct paths exist. Each has a different upfront cost, different ongoing cost, and a different break-even point.

---

## The Memory Reality for These Models

This constraint matters enough to state clearly before speccing hardware:

```
Qwen 3.5 35B-A3B MoE (Dynamic Q4):  ~18GB of weights in memory
Qwen 3.5 27B Dense (Q4_K_M):        ~15GB of weights in memory
```

Any hardware that cannot hold 18GB of data accessible at memory-bandwidth speeds will fail to run the MoE model usably. This rules out:

- **ESP32 swarms at practical node counts** — Each ESP32 has 8MB PSRAM. Holding 18GB requires ~2,250 nodes (~$18,000 in hardware). Not viable.
- **Raspberry Pi clusters** — 8GB max per board; 3 boards minimum just for the MoE weights, plus inter-board bandwidth collapses throughput to unusable levels for LLMs.
- **Small/mid FPGAs** (Lattice ECP5, Xilinx Artix-7) — Insufficient on-chip SRAM; require external DDR4 which lacks the bandwidth for smooth inference at this model size.

What *can* hold 18GB at inference-appropriate bandwidth:
- GPU VRAM (HBM2/GDDR6X)
- FPGA HBM stacks (Alveo-class cards)
- Unified memory systems (Apple Silicon — covered below)
- Large DDR5 pools with CPU inference (slower, but viable)

---

## Path 1: The Cheapest GPU Route (Used Cards)

Before exploring custom hardware, it is worth establishing the cheapest GPU baseline — because buying used changes the economics significantly.

### Used RTX 3090 (24GB GDDR6X) — ~$600–$900

The RTX 3090 has the same 24GB VRAM as the RTX 4090 and was the previous generation's flagship. Used prices have dropped to $600–$900 on eBay and Facebook Marketplace as 4090 owners upgrade.

| | RTX 4090 (New) | RTX 3090 (Used) |
|---|---|---|
| VRAM | 24GB | 24GB |
| Memory bandwidth | 1,008 GB/s | 936 GB/s |
| Tokens/sec (35B MoE Q4) | 55–80 | 40–60 |
| Tokens/sec (27B Dense Q4) | 30–50 | 22–38 |
| Power draw | 350–450W | 350–420W |
| Price | ~$1,800 | ~$600–$900 |

**Verdict:** If you just want to run these models cheaply with minimal complexity, a used RTX 3090 is the fastest path to 24GB for under $1,000. Performance is 25–35% behind the 4090. Power draw is almost identical — you save on purchase price, not electricity.

### Used Professional Cards — RTX A5000 (24GB) — ~$600–$900

The RTX A5000 is a professional workstation card with 24GB GDDR6, ECC memory, and a lower power profile (230W TDP) than the consumer 3090. Performance is slightly below the 3090 for gaming but comparable for inference. The ECC memory has value for always-on inference servers where memory errors matter.

| | RTX 3090 | RTX A5000 |
|---|---|---|
| VRAM | 24GB | 24GB |
| Power TDP | 350W | 230W |
| Tokens/sec (35B MoE Q4) | 40–60 | 35–55 |
| Annual power cost (24/7) | ~$640/yr | ~$420/yr |
| Price (used) | ~$600–$900 | ~$600–$900 |

**Verdict:** Similar price to the 3090, noticeably lower power. For always-on use the A5000 saves ~$200/year in electricity over the 3090.

### Dual GPU — 2× RTX 3060 12GB — ~$350–$500

`llama.cpp` supports splitting model layers across multiple GPUs using `--tensor-split`. Two RTX 3060 12GB cards give you 24GB of total addressable VRAM for the model. Inter-GPU communication happens over PCIe rather than NVLink, which introduces some latency per layer crossing.

```bash
# llama.cpp splits layers across both GPUs automatically
./llama-server -m qwen35-27b-q4.gguf -ngl 100 --tensor-split 0.5,0.5
```

| | 2× RTX 3060 12GB | RTX 3090 |
|---|---|---|
| Total VRAM | 24GB | 24GB |
| Hardware cost | ~$350–$500 | ~$600–$900 |
| Tokens/sec (27B Dense Q4) | 15–25 | 22–38 |
| Tokens/sec (35B MoE Q4) | 20–35 | 40–60 |
| Power draw | 280–340W (combined) | 350–420W |
| PCIe slots required | 2× PCIe x16 | 1× PCIe x16 |

**Verdict:** Cheapest GPU path at ~$400. Performance takes a meaningful hit from PCIe inter-GPU transfers — expect roughly 40–50% fewer tokens/sec than a single 3090 for the same total VRAM. Still responsive for interactive use. The MoE model (lower per-token compute) tolerates this split better than the dense model.

---

## Path 2: The TPT Crucible Route (FPGA)

This is where custom hardware compiled with TPT Crucible becomes relevant. The target is not to beat GPU throughput — it is to match *good enough* throughput at significantly lower power draw and a competitive upfront cost.

### What FPGA Can Hold These Models?

The FPGA must have enough on-board HBM or DRAM to hold 18GB (MoE) or 15GB (Dense) at memory bandwidth speeds adequate for token generation. Slow DDR4 on cheap FPGAs is insufficient — inference stalls waiting on memory.

| FPGA Card | On-board Memory | Adequate for These Models? | Used Price |
|---|---|---|---|
| Xilinx Alveo U50 | 8GB HBM2 | No (too small) | $200–$400 |
| Xilinx Alveo U280 | 8GB HBM2 + 32GB DDR4 | Marginal (27B only, slow) | $400–$800 |
| **Xilinx Alveo U250** | **64GB HBM2** | **Yes — both models comfortably** | **$600–$1,500** |
| Xilinx Alveo U55C | 16GB HBM2 | Marginal for 27B Dense | $800–$1,500 |
| Intel Stratix 10 MX | Up to 32GB HBM | Yes for 27B; marginal for MoE | $1,500–$3,000 |

The **used Alveo U250** is the target card. At $600–$1,500 on the used market, it matches or undercuts a used RTX 3090 on purchase price while drawing 4–5× less power.

### The Full Crucible Build

The Alveo U250 is a PCIe card — it needs a host machine. You do not need a powerful CPU for inference (the FPGA does the compute), but you need PCIe x16 bandwidth.

**Option A — Old Workstation Host**

Pick up an old Dell Precision, HP Z-series, or Supermicro 1U server from eBay. These are decommissioned enterprise machines that can be had for $100–$400 and have the PCIe slots and power infrastructure to host an Alveo card.

| Component | Cost |
|---|---|
| Used Alveo U250 | $600–$1,500 |
| Used workstation / server host (Dell Precision T7600, HP Z840) | $150–$400 |
| PSU upgrade if needed (750W+) | $60–$100 |
| **Total** | **~$810–$2,000** |

**Option B — Mini ITX Host**

If you want a smaller form factor (closer to a consumer PC), an Alveo U250 fits in a full-tower consumer build with the right riser/power adapter. A modest CPU host (no gaming GPU needed) runs ~$500.

| Component | Cost |
|---|---|
| Used Alveo U250 | $600–$1,500 |
| Budget host PC (CPU + mobo + RAM + NVMe, no GPU) | $400–$600 |
| **Total** | **~$1,000–$2,100** |

### Performance: FPGA vs. GPU

Once the overlay bitstream is flashed (once per board, ~10 min), models load via DMA weight transfer — no re-synthesis required for common models.

| | 2× RTX 3060 | Used RTX 3090 | Alveo U250 (Crucible) |
|---|---|---|---|
| **Upfront cost** | ~$400–$500 | ~$700–$900 | ~$810–$2,000 |
| **Tokens/sec (35B MoE Q4)** | 20–35 | 40–60 | 30–60 |
| **Tokens/sec (27B Dense Q4)** | 15–25 | 22–38 | 20–40 |
| **Power draw (inference)** | 280–340W | 350–420W | **50–80W** |
| **Annual power cost (24/7)** | ~$530–$640/yr | ~$640–$770/yr | **~$90–$145/yr** |
| **Model switch (HBM cached)** | Seconds | Seconds | **<1 second** |
| **Model switch (load from NVMe)** | Seconds | Seconds | **~90 seconds** |
| **Model switch (new overlay needed)** | Seconds | Seconds | ~5–10 minutes |
| **Novel model, no community cache** | Seconds | Seconds | 1–4h (unattended) |
| **Setup complexity** | Low | Low | Medium (Docker path) |

**The power difference is decisive for always-on use.** An Alveo U250 running inference continuously costs ~$100–$145/year in electricity. The same workload on an RTX 3090 costs ~$640–$770/year — a difference of ~$550/year. The FPGA's higher upfront cost recouped in roughly 2 years of 24/7 operation.

---

## Path 3: Apple Silicon (The Hidden Contender)

This deserves a mention because it legitimately undercuts everything above for a certain type of user. Apple's M-series chips use unified memory — the same physical RAM is shared between CPU and the "GPU". This means a Mac Studio with 192GB of unified memory can hold these models in the fast memory pool without any GPU VRAM limit.

| Device | Unified Memory | Tokens/sec (35B MoE Q4) | Tokens/sec (27B Dense Q4) | Price (new) |
|---|---|---|---|---|
| Mac Mini M4 Pro (24GB) | 24GB | 35–55 | 25–40 | ~$1,400 |
| Mac Studio M4 Max (64GB) | 64GB | 60–90 | 45–70 | ~$2,000 |
| Mac Studio M4 Ultra (192GB) | 192GB | 80–110 | 65–95 | ~$5,000 |

The **Mac Mini M4 Pro at $1,400** is the most interesting comparison here. 24GB unified memory, ~38W idle / ~60W peak under LLM load, and native llama.cpp Metal support. It is quieter, smaller, simpler, and cheaper to run than any GPU build — at the cost of not being upgradeable and being locked to Apple's platform.

This is not a TPT Crucible path — Apple Silicon is not a target hardware type. But if your goal is simply "cheapest way to run these models well," the Mac Mini M4 Pro is difficult to argue with.

---

## The Crucible Custom Hardware Path: Where It Actually Wins

TPT Crucible's advantage for these specific models is not upfront cost — it is **cost at deployment scale** and **power efficiency over time**.

### Scenario: Running as a Dedicated Inference Server (24/7)

Assume you pick one model (the 35B MoE) and want to run it continuously as a local API endpoint — coding assistant, document processing, internal tool.

| Approach | Upfront | Annual Power | 3-Year Total |
|---|---|---|---|
| Used RTX 3090 host | ~$1,200 | ~$700/yr | **~$3,300** |
| Mac Mini M4 Pro | ~$1,400 | ~$130/yr | **~$1,790** |
| Alveo U250 + used server | ~$1,500 | ~$120/yr | **~$1,860** |
| New RTX 4090 host | ~$4,000 | ~$780/yr | **~$6,340** |

Over 3 years, the Mac Mini M4 Pro and Alveo U250 converge at roughly the same total cost — both dramatically cheaper than running a GPU 24/7.

### Scenario: Deploying to 10 Inference Nodes

Scale changes everything. Multiply the above costs by 10:

| Approach | 10-Node Upfront | 10-Node Annual Power | 3-Year Total |
|---|---|---|---|
| Used RTX 3090 × 10 | ~$12,000 | ~$7,000/yr | **~$33,000** |
| Alveo U250 × 10 | ~$15,000 | ~$1,200/yr | **~$18,600** |
| RTX 4090 × 10 | ~$40,000 | ~$7,800/yr | **~$63,400** |

At 10 nodes the FPGA path is $14,000 cheaper over 3 years despite the higher upfront cost. At 100 nodes the savings are $140,000+.

---

## Build Summary: Cheapest Viable Options Ranked

These prices assume used hardware where applicable and running both target models.

| Build | Upfront Cost | Tokens/sec (MoE) | Power | Complexity | Best For |
|---|---|---|---|---|---|
| 2× RTX 3060 12GB | **~$400–$500** | 20–35 | 300W | Low | Budget, single user, occasional use |
| Used RTX 3090 | ~$700–$900 | 40–60 | 380W | Low | Best single-GPU value |
| Mac Mini M4 Pro (24GB) | ~$1,400 | 35–55 | 60W | Very Low | Quiet, low-power, simple setup |
| Used Alveo U250 + host | ~$1,000–$2,000 | 30–60 | **55W** | High | Always-on server, scale deployment |
| RTX A5000 24GB (used) | ~$700–$1,000 | 35–55 | 230W | Low | Professional workstation |

---

## What Actually Gets Built with TPT Crucible

The pipeline for the FPGA path:

```
1. Download model (GGUF format)

2. Check community cache — skip steps 3–4 if a pre-built package exists
   tpt get qwen35-27b-alveo-u250
   → Downloads verified .tptpkg (~10–20 min); go straight to step 5

3. Pre-flight check (if compiling fresh)
   tpt-catalyst check qwen35-27b.gguf --target fusion
   → Shows which operators are supported, suggests substitutions

4. Compile (first time only; unattended; ~1–4 hours)
   tpt-catalyst ingest qwen35-27b.gguf --quantize auto --target fusion --board alveo-u250
   → Offload to cloud synthesis worker to avoid blocking your machine
   → Output: qwen35-27b.tptpkg (ready-to-flash package)

5. Flash overlay + load model (~10 min first time; <2 min model switches after)
   tpt-fusion overlay flash dense-int4 --board alveo-u250   # one-time per board
   tpt-fusion load qwen35-27b.tptpkg                        # hot-load weights, no reflash

5. Run — TPT Observer dashboard shows live tokens/sec, HBM utilisation, power draw
```

After the initial compile, the FPGA simply runs. No CUDA drivers. No Python environment. No runtime overhead. The hardware *is* the model.

---

## Bottom Line

**If cheapest upfront cost is the priority:** 2× RTX 3060 12GB at ~$400–$500 runs both models. Slower than ideal but functional.

**If cheapest ongoing cost is the priority:** Mac Mini M4 Pro or Alveo U250 via TPT Crucible — both run at ~60W vs. 350–400W for a GPU, saving $500–$600/year.

**If you want to build something purpose-built for these two models:** The Alveo U250 path through Crucible is the answer. You compile each model once, the FPGA becomes a dedicated inference appliance, and you are not paying the GPU tax in power bills for years to come.

**The cheapest path that scales:** Crucible. The unit economics of FPGA deployment improve with every node you add.
