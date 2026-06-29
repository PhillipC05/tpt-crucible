# TPT Crucible Architecture

## Overview

TPT Crucible is a hardware-agnostic AI compiler suite that compiles standard AI models onto non-traditional hardware: FPGAs, analog compute circuits, microcontroller swarms, compute-in-memory arrays, neuromorphic chips, and photonic processors.

## Core Architecture

### TPT Catalyst (Core IR Compiler)

The universal translator. Ingests standard AI models and converts them into TPT-IR, a hardware-agnostic intermediate representation.

**Supported Input Formats:**
- PyTorch (.pt, .pth)
- ONNX (.onnx)
- TensorFlow (.pb, .savedmodel)
- GGUF (quantization-preserving)
- SafeTensors
- HuggingFace model directories

**Key Features:**
- Operator fusion (matmul+relu, matmul+gelu, add+relu)
- Auto-quantization with per-layer sensitivity analysis
- Pre-flight compatibility checking
- Content-addressed compilation cache

### TPT Alloy (Swarm Module)

Partitions neural networks across microcontroller swarms (ESP32, RP2040, RISC-V).

**Features:**
- Topology-aware partitioning (2D grid, star, ring, mesh)
- KV cache distribution across nodes
- Fault-tolerant execution with heartbeat protocol
- Parallel firmware flashing (USB + WiFi OTA)
- RISC-V custom ML ISA generation

### TPT Fusion (FPGA Module)

Generates synthesizable RTL for FPGA-based inference.

**Features:**
- MAC array generation (systolic architecture)
- HBM auto-routing with LiteX/LiteDRAM
- Overlay architecture with hot-swap model loading
- Structured sparsity (2:4, 4:8) for skip-zero gating
- Yosys/Nextpnr integration

### TPT Element (Analog Module)

Maps AI weights to physical components and simulates circuit behavior.

**Features:**
- Weight-to-resistance mapping
- SPICE netlist generation (Xyce/ngspice)
- Thermal noise and voltage drift simulation
- Reality Check ML model for fast drift prediction
- KiCad PCB export

### TPT Mosaic (Hybrid Orchestrator)

Coordinates compilation across multiple hardware types.

**Features:**
- Layer-to-hardware annotation
- Cross-hardware communication bridges (USB/UART/Ethernet)
- Speculative decoding (draft on swarm, verify on FPGA)

## Data Flow

```
AI Model (.pt/.onnx/.gguf)
    ↓
TPT Catalyst → TPT-IR (.tptir)
    ↓
┌───┼───────┐
│   │       │
Alloy Fusion Element
│   │       │
▼   ▼       ▼
FW  RTL    SPICE
```

## Package Format (.tptpkg)

ZIP container with manifest, IR, compiled artifacts per target, pre-flight report, quantization profile, and partition plan.

## Testing

- 181 Python unit tests across 11 packages
- 10 Rust unit tests
- Go services build clean
- Next.js frontend builds clean
