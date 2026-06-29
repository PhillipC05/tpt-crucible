# tpt-crucible Integration Todos

These items were identified by analysing the three-repo TPT AI compute suite (tpt-gpu, tpt-spark, tpt-crucible) for cross-repo synergies. None of these are required for tpt-crucible to work standalone — they are optional improvements that strengthen the suite.

---

## 1. Evaluate adopting tpt-gpu's TPTIR as Catalyst's output dialect (depends on tpt-gpu item 1)

**Why:** tpt-gpu defines TPTIR as its MLIR-based intermediate representation (Layer 3). Crucible's Catalyst module generates its own TPT-IR from GGUF/ONNX/PyTorch inputs. If both dialects are the same (or if Crucible adopts tpt-gpu's published spec), a model compiled once to TPTIR can route to GPU (tpt-gpu runtime), FPGA (Fusion), MCU swarm (Alloy), or analog (Element) — single IR, all targets.

**What to do:**
- Wait for tpt-gpu to publish `tptir-spec` (see tpt-gpu `todo1.md` item 1)
- Compare tpt-gpu's TPTIR dialect with Catalyst's current TPT-IR output format (op names, type system, attributes, text-format serialisation)
- If the dialects are compatible: add `tptir-spec` as a dependency to Catalyst and align Catalyst's output to the published spec
- If there are gaps: open a discussion issue in tpt-gpu listing the ops Crucible needs that TPTIR doesn't cover yet
- Once aligned, Catalyst's output becomes a strict subset of tpt-gpu's TPTIR — Alloy/Fusion/Element consume the same IR that tpt-gpu's runtime does

---

## 2. Adopt Spark as the default local LLM backend (depends on tpt-spark item 2)

**Why:** Crucible currently lists Spark IPC as one of several optional LLM backends (alongside OpenRouter, Anthropic API, Ollama). Spark is the only one that is fully offline, privacy-preserving, and part of the same open-source suite. It should be the default when available, with cloud providers as explicit opt-in fallbacks.

**What to do:**
- Wait for tpt-spark to publish its `HEADLESS_API.md` spec (see tpt-spark `todo1.md` item 2)
- Implement Spark auto-detection: on startup, check for `$XDG_RUNTIME_DIR/tpt-spark.sock` (Linux), `\\.\pipe\tpt-spark` (Windows), or `/tmp/tpt-spark.sock` (macOS)
- If Spark is detected, set it as the default LLM backend in Observer's settings panel
- If Spark is not detected, show a "Install TPT Spark for offline AI assistance" prompt with a link, then fall back to cloud providers
- Update `LLM_BACKENDS.md` (or equivalent config doc) to document the priority order: Spark IPC → Ollama-compatible → OpenRouter → Anthropic API

---

## 3. Adopt shared model registry (`~/.tpt/models/`)

**Why:** tpt-spark downloads and manages GGUF models in `~/.tpt/models/`. Crucible's Catalyst ingests the same GGUF models as compilation inputs. Without a shared convention, users download models twice.

**What to do:**
- Update Catalyst's model loading code to scan `~/.tpt/models/` as the primary GGUF source
- Read `~/.tpt/models/models.json` (see tpt-gpu `todo1.md` item 2 for the manifest spec) to pre-populate the model selector in Observer without filesystem scanning
- If `~/.tpt/models/` doesn't exist, fall back to the current behaviour (explicit file path)
- Show a "No models found — open TPT Spark to download models" message in Observer when the directory is empty

---

## 4. Read Spark benchmark baselines for emulator validation (depends on tpt-spark item 4)

**Why:** Crucible's emulator validates compiled edge targets against expected performance bounds. Spark writes GPU benchmark records to `~/.tpt/benchmarks/spark-{date}.json`. Reading these gives the emulator a real-world GPU reference baseline automatically, without the user manually entering numbers.

**What to do:**
- On emulator startup, scan `~/.tpt/benchmarks/spark-*.json` and load the most recent record for the current model (matched by model name)
- Use `tokens_per_second` and `time_to_first_token_ms` as the GPU reference baseline in emulator comparison reports
- If no Spark benchmark exists for the model, fall back to the current hardcoded reference values
- Show the baseline source in Observer's benchmark panel ("GPU reference: TPT Spark, 2026-06-29, RTX 4090, 142 tok/s")

---

## 5. TPT Script as a Catalyst input format (deferred — depends on items 1 and tpt-gpu item 3)

Once TPTIR is unified (item 1) and tpt-gpu's TPT Script compiler frontend is stable, add TPT Script (`.tpt` files) as an optional Catalyst input format. This would mean a single language — TPT Script — can target GPU (via tpt-gpu), FPGA (via Fusion), MCU swarm (via Alloy), and analog (via Element). No Crucible implementation work needed until TPTIR unification is confirmed; this is a note to revisit at that point.
