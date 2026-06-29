# TPT Crucible Module API Reference

## tpt-catalyst

### Core Functions

```python
from tpt_catalyst import TptIr, ingest_model, optimize_graph

# Ingest a model
ir = ingest_model(Path("model.gguf"))

# Optimize the graph
optimized = optimize_graph(ir)

# Save to disk
optimized.save(Path("model.tptir"))
```

### Pre-flight Checking

```python
from tpt_catalyst import check_compatibility, HardwareTarget

report = check_compatibility(ir, HardwareTarget.FUSION)
print(f"Score: {report.score:.0%}")
```

### Quantization

```python
from tpt_catalyst import recommend_quantization, apply_quantization

rec = recommend_quantization(ir, "fusion")
ir = apply_quantization(ir, rec.recommended_profile)
```

### Compilation Cache

```python
from tpt_catalyst.cache import CompilationCache

cache = CompilationCache(Path(".tpt-cache"))
if not cache.check(node):
    cache.store(node, output_data)
```

## tpt-alloy

### Partitioning

```python
from tpt_alloy import Topology, PartitionConfig, partition_model

config = PartitionConfig(topology=Topology.grid2d(4, 4))
partitions = partition_model(layer_count=22, config=config)
```

### Firmware Generation

```python
from tpt_alloy import FirmwareTarget, generate_firmware

bundle = generate_firmware(partition, FirmwareTarget.ESP32)
Path("node_0.c").write_text(bundle.source_code)
```

## tpt-fusion

### MAC Array Generation

```python
from tpt_fusion import MacArray, MacConfig

mac = MacArray(MacConfig(rows=16, cols=16, data_width=8))
verilog = mac.generate_verilog()
```

### Board Selection

```python
from tpt_fusion import get_board, list_boards

board = get_board("xilinx_alveo_u280")
print(f"HBM: {board.hbm.capacity_gb} GB")
```

## tpt-element

### SPICE Simulation

```python
from tpt_element import SpiceNetlistGenerator
from tpt_element.weight_map import WeightMapper

mapper = WeightMapper(tolerance=0.05)
components = mapper.map_weights(weights)

gen = SpiceNetlistGenerator()
for c in components:
    gen.add_component(c)
gen.save_netlist(Path("circuit.spice"))
```

## tpt-drivers

### Driver Registry

```python
from tpt_drivers import DriverRegistry, DriverManifest

registry = DriverRegistry()
manifest = registry.get_driver("xilinx_alveo_u280")
```
