# Qwen Model Hardware Guide
### Which Model, Which Hardware, and What It Actually Costs

---

## The Setup: What We're Solving For

A local AI PC that does two things simultaneously:
1. **General programming workstation** — IDE, builds, Docker, browser, the usual dev environment
2. **AI agents running 24/7** — a model always available to answer, generate code, review PRs, run autonomous tasks in the background

These two requirements pull in different directions. A 24/7 inference workload means the inference hardware is always under load — if that's the same GPU your coding IDE is competing with, you get stuttering and slowdowns. The cleanest solution is to **separate the inference hardware from the dev machine**, or choose hardware that handles inference without touching your CPU/dev workflow.

---

## The Full Qwen Lineup: Memory Requirements

| Model | Q4_K_M Footprint | VRAM Needed (w/ 16K ctx) | Class |
|---|---|---|---|
| Qwen3 0.6B | ~0.4GB | ~1GB | Micro |
| Qwen2.5 1.5B | ~0.9GB | ~1.5GB | Micro |
| Qwen3.5 3B | ~1.8GB | ~3GB | Small |
| Qwen3.5 4B | ~2.4GB | ~4GB | Small |
| Qwen2.5 7B | ~4.1GB | ~6GB | Medium |
| Qwen3.5 9B | ~5.4GB | ~8GB | Medium |
| Qwen2.5 14B | ~8.3GB | ~12GB | Medium-Large |
| Qwen2.5 22B | ~13GB | ~17GB | Large |
| Qwen3.6 27B | ~16GB | ~20GB | Large |
| Qwen3.6 35B-A3B MoE | ~18GB | ~22GB | Large (MoE) |
| Qwen2.5 32B | ~19GB | ~23GB | Large |
| Qwen2.5 72B | ~42GB | ~50GB | Very Large |
| Qwen3-Coder 80B | ~47GB | ~55GB | Very Large |

---

## Tier 1 — Micro Models (0.6B, 1.5B): No GPU Required

At under 1GB of weights, these models run comfortably on CPU inference. You do not need a GPU at all.

**Hardware options:**

| Device | Cost | Tok/s (1.5B Q4) | Power | Notes |
|---|---|---|---|---|
| Raspberry Pi 5 8GB | ~$120 | 3–6 | 5–8W | Excellent for always-on agents; battery viable |
| Mini PC (N100/N150 chip) | ~$150–200 | 8–15 | 8–15W | Compact; fanless options available |
| Old laptop / NUC | ~$100–200 used | 5–12 | 15–25W | Use what you have |
| Mac Mini M4 (16GB base) | ~$700 | 40–60 | 12–18W | Overkill for 1.5B but future-proof |

**Verdict:** A $150–200 mini PC (like an Intel N100 box) runs the 1.5B model as a permanent background agent at near-zero power cost. No GPU, no GPU drivers, no CUDA, no VRAM. This is the cheapest possible always-on AI agent setup.

**ESP32 swarm comparison:**
- 0.6B: ~50 nodes = $350 + coordinator
- 1.5B: ~113 nodes = $890 + coordinator
- Mini PC at $200 is cheaper, faster, and simpler. The swarm only makes sense here for battery/embedded/field deployment where a mini PC isn't an option.

---

## Tier 2 — Small Models (3B, 4B): Budget GPU Wins

At 2–4GB of weights you need a proper GPU to get usable coding-assistant speeds. CPU inference works but drops to 2–5 tok/s — too slow for interactive agents.

**The cheapest GPU that makes sense:**

| Hardware | Total Cost | Tok/s (7B Q4) | Power | Notes |
|---|---|---|---|---|
| RTX 3060 8GB (used) + budget PC | ~$500–600 | 40–65 | 120–160W | Handles up to ~5GB models well |
| RTX 3060 12GB (used) + budget PC | ~$550–650 | 35–55 | 130–170W | More headroom; handles 7B comfortably |
| RTX 4060 8GB (new) + budget PC | ~$650–750 | 45–70 | 90–120W | Lower power than 3060; good efficiency |

**Why custom hardware can't compete here:**
- ESP32 swarm: 225–500 nodes = $1,575–$3,500. More expensive than a GPU and 10× slower.
- Small FPGA: Can technically run quantized 3B models but requires synthesis toolchain, weeks of setup, and won't beat a $550 GPU PC on cost.
- Raspberry Pi / CPU: 2–5 tok/s is unusable for interactive coding agents.

**Verdict:** Used RTX 3060 12GB + a budget PC is the sweet spot for 3B–7B Qwen models. ~$600 total, handles the full small-medium tier, fast enough for real-time coding assistance.

---

## Tier 3 — Medium Models (7B, 9B, 14B): The Best Coding Agent Sweet Spot

This is the tier that matters most for **AI coding agents**. Qwen2.5-Coder 7B and 14B are among the strongest code-focused models available, and they fit on accessible hardware.

**Why this tier is the sweet spot for agents:**
- Fast enough for real-time interaction (30–80 tok/s)
- Strong enough for complex coding tasks (14B rivals much larger general models on code)
- Fits on affordable VRAM (8–16GB)
- Low enough power for 24/7 operation without eye-watering electricity bills

**Hardware options:**

| Hardware | Total Cost | Tok/s (14B Q4) | Power (24/7) | Annual Power Cost |
|---|---|---|---|---|
| RTX 3060 12GB + mid PC | ~$600–800 | 25–40 | 130–180W | ~$240–$330/yr |
| RTX 4060 Ti 16GB + mid PC | ~$900–1,100 | 35–55 | 110–150W | ~$200–$275/yr |
| RTX 3090 24GB + mid PC | ~$1,400–1,800 | 35–55 | 350–420W | ~$640–$770/yr |
| Mac Mini M4 Pro 24GB | ~$1,400 | 45–65 | 25–45W | **~$45–$80/yr** |
| Alveo U250 + old server | ~$1,200–2,000 | 20–40 | 50–75W | **~$90–$140/yr** |

**Important note on the RTX 3090 at this tier:** The 3090's 24GB VRAM is overkill for a 14B model (which only needs 12GB). You're paying for VRAM you don't need, and the power draw penalty (350W+) is severe for 24/7 operation.

**The hidden winner for 24/7 agents: Mac Mini M4 Pro**

At $1,400 with 24GB unified memory and ~30W under inference load, the Mac Mini M4 Pro runs Qwen2.5-Coder 14B at 45–65 tok/s continuously for ~$60/year in electricity. It sits silently on your desk, doesn't compete with your dev machine's CPU, and runs `ollama serve` as a background service. This is the cleanest 24/7 agent setup for the 7B–22B range.

---

## Tier 4 — Large Models (22B, 27B, 32B, 35B MoE): GPU and FPGA Roughly Equal

At 13–22GB of weights you need 24GB VRAM minimum. The only consumer GPU that hits this is the RTX 3090/4090 — and now the prices start to converge with FPGA options.

**Hardware comparison:**

| Hardware | Total Cost | Tok/s (27B Q4) | Power | Annual Power Cost (24/7) |
|---|---|---|---|---|
| Used RTX 3090 + PC | ~$1,600–2,200 | 22–38 | 380–450W | ~$700–830/yr |
| New RTX 4090 + PC | ~$3,200–4,300 | 55–80 | 400–550W | ~$730–1,000/yr |
| Used Alveo U250 + server | ~$1,100–2,000 | 20–40 | 50–75W | ~$90–140/yr |
| Mac Mini M4 Max 64GB | ~$2,600 | 50–70 | 40–65W | ~$70–120/yr |

**The crossover:** At this tier the Alveo U250 starts to make financial sense for always-on use. The hardware cost is similar to a used RTX 3090 build, but you save ~$600/year in power. After 2 years of 24/7 operation the FPGA has paid for itself over the GPU — and you're not competing with your dev machine's GPU at all since it's a PCIe card running independently.

The **Mac Mini M4 Max** is again the clean consumer option — expensive upfront, but near-silent and dirt cheap to run long-term.

---

## Tier 5 — Very Large Models (72B, 80B): FPGA Wins Clearly

At 42–55GB of weights, consumer GPU options become very expensive:
- RTX 6000 Ada 48GB: ~$6,500
- 2× RTX 3090 24GB (NVLink): ~$1,600 + complex multi-GPU setup
- Mac Studio M4 Ultra 192GB: ~$5,000

FPGA via Mosaic multi-card split:
- 2× Alveo U250 (64GB HBM each = 128GB total): ~$1,600–3,000 used
- Old server to host both cards: ~$400–600
- **Total: ~$2,000–3,600**

This is $2,000–4,500 cheaper than the GPU alternatives, and draws ~100–150W combined vs 600–800W for multi-GPU. For a 72B model running 24/7, the power saving alone is ~$900–$1,100/year.

This is the tier where TPT Crucible's Mosaic orchestrator delivers unambiguous, clear-cut value.

---

## The Dev Workstation + 24/7 Agents Architecture

Given that you want **both** a programming workstation and AI agents running permanently, the best architecture separates the two concerns.

### Recommended: Two-Machine Setup

```
┌─────────────────────────────┐     ┌──────────────────────────────┐
│     Dev Workstation          │     │   Dedicated Inference Node   │
│                             │     │                              │
│  Fast CPU (Ryzen 7 / i7)    │◄────│  Runs Ollama / llama.cpp     │
│  32–64GB DDR5               │     │  as a local API server       │
│  No GPU required            │     │  on 0.0.0.0:11434            │
│  2TB NVMe (fast builds)     │     │                              │
│  ~$600–900                  │     │  ~$200–1,400 depending        │
└─────────────────────────────┘     │  on model tier (see below)   │
                                    └──────────────────────────────┘
```

Your IDE, your AI coding extension (Continue, Cursor, Copilot alternative) points at `http://inference-node:11434`. The inference hardware runs independently — heavy inference load never touches your dev machine's CPU or system RAM.

### Inference Node Options by Qwen Model Tier

| Target Model | Inference Node | Node Cost | Node Power | Total Setup Cost |
|---|---|---|---|---|
| Qwen 1.5B (fast, lightweight agents) | Raspberry Pi 5 8GB | ~$120 | 8W | ~$720–$1,020 |
| Qwen 7B (strong coding assistant) | Mini PC + RTX 3060 8GB | ~$550 | 130W | ~$1,150–$1,450 |
| Qwen 14B (best coding quality) | **Mac Mini M4 Pro 24GB** | ~$1,400 | 30W | ~$2,000–$2,300 |
| Qwen 32B (near-frontier quality) | Used RTX 3090 box | ~$1,600 | 400W | ~$2,200–$2,500 |
| Qwen 72B (frontier quality) | 2× Alveo U250 (Crucible) | ~$2,400 | 130W | ~$3,000–$3,300 |

**Dev workstation base cost (no GPU): ~$600–900**
- AMD Ryzen 7 7700 or Intel Core i7-14700
- 64GB DDR5
- 2TB NVMe Gen4
- No dedicated GPU — your programming, compilation, and Docker workloads don't need one

### Why No GPU on the Dev Machine?

Modern development work — compiling, running Docker, using a browser and IDE simultaneously — runs entirely on CPU. Integrated graphics handles display output. The GPU budget is freed entirely for inference.

If you want a GPU on the dev machine too (for game development, ML training, or graphics work), add an RTX 4060 ($250–300) to the dev machine budget — it won't conflict with the inference node since they're separate boxes.

---

## Decision Guide: Which Qwen Model for 24/7 Coding Agents?

```
What do you need the agent to do?
│
├── Quick completions, fast autocomplete, simple Q&A
│   └── Qwen2.5-Coder 7B → RTX 3060 12GB box (~$600)
│       55–80 tok/s; responds before you finish typing
│
├── Complex code generation, multi-file refactoring, PR review
│   └── Qwen2.5-Coder 14B → Mac Mini M4 Pro (~$1,400)
│       45–65 tok/s; strong reasoning; 30W 24/7
│
├── Autonomous agents, long-context codebase analysis
│   └── Qwen2.5 32B → Used RTX 3090 box (~$1,600)
│       22–38 tok/s; handles 32K+ context comfortably
│
└── Best possible quality, frontier-level coding
    └── Qwen3-Coder 80B → 2× Alveo U250 via Crucible (~$2,400)
        10–20 tok/s; ~$120/yr power; cheaper than GPU equivalent
```

---

## Summary: Where Custom Hardware Beats GPU, By Tier

| Qwen Tier | Cheapest Hardware | GPU Cheaper? | Custom Hardware Cheaper? | Notes |
|---|---|---|---|---|
| 0.6B, 1.5B | Mini PC / Raspberry Pi ($120–$200) | N/A | N/A — no GPU needed at all | CPU inference is fine |
| 3B, 4B, 7B, 9B | RTX 3060 + budget PC (~$550–650) | **Yes** | No | GPU wins at this tier |
| 14B | Mac Mini M4 Pro ($1,400) | Equal | Equal | Power cost decides long-term |
| 22B–35B | Alveo U250 + server (~$1,500) | Similar upfront | Wins on power costs | ~$600/yr power saving over GPU |
| 72B, 80B | 2× Alveo U250 Mosaic (~$2,400) | No | **Yes — $2,000–$4,000 cheaper** | Clear FPGA win |

**The crossover line sits at around 22B parameters.** Below that, a GPU PC is the cheapest viable option. Above it, FPGA hardware starts to undercut GPU on upfront cost *and* wins decisively on operating cost for 24/7 workloads.

For a dev workstation + 24/7 agents setup specifically: the **Mac Mini M4 Pro as a dedicated inference node** paired with a **GPU-free dev workstation** is the most practical setup for the 7B–22B range — lower total cost than a single GPU machine, lower power, and your dev environment never competes with inference.
