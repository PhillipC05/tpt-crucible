# Versioning and Release Strategy

## Version Scheme

TPT Crucible follows Semantic Versioning (SemVer):

```
MAJOR.MINOR.PATCH
```

- **MAJOR**: Breaking changes to TPT-IR format, API, or package structure
- **MINOR**: New hardware targets, new optimization passes, new CLI features
- **PATCH**: Bug fixes, documentation updates, test improvements

## Current Version

- **TPT Crucible**: 0.1.0 (alpha)
- **TPT-IR Format**: 1.0.0
- **Package Format (.tptpkg)**: 1.0.0

## Release Cadence

- **Alpha (0.x)**: Active development, breaking changes expected
- **Beta (1.0-rc)**: Feature-complete, API stabilization
- **Stable (1.0+)**: Production-ready, backward compatibility guaranteed

## Component Versioning

Each Python package maintains independent versioning:
- `tpt-catalyst`: Core compiler
- `tpt-alloy`: Swarm module
- `tpt-fusion`: FPGA module
- `tpt-element`: Analog module
- `tpt-emulator`: SiL emulator
- `tpt-mosaic`: Orchestrator
- `tpt-train`: Training hooks
- `tpt-drivers`: Driver SDK
- `tpt-silicon`: CIM backend
- `tpt-photon`: Photonic backend
- `tpt-pulse`: Neuromorphic backend

## Compatibility Matrix

| TPT-IR | .tptpkg | Catalyst | Alloy | Fusion | Element |
|--------|---------|----------|-------|--------|---------|
| 1.0.0  | 1.0.0   | 0.1.x    | 0.1.x | 0.1.x  | 0.1.x   |

## Breaking Changes

Changes requiring MAJOR version bump:
- TPT-IR format changes (new fields, removed fields)
- .tptpkg manifest schema changes
- CLI command syntax changes
- Python API signature changes

Changes requiring MINOR version bump:
- New hardware target support
- New optimization passes
- New CLI flags
- Backward-compatible Python API additions
