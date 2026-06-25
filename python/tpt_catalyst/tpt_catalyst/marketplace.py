"""Pre-compiled Package Marketplace — browse and download ready-to-use packages."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json
from pathlib import Path


@dataclass
class MarketplacePackage:
    package_id: str
    model_name: str
    hardware_target: str
    quant_type: str
    accuracy_delta: float
    sha256: str
    download_url: str
    description: str = ""
    node_count: int = 1
    size_mb: float = 0.0
    downloads: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "model_name": self.model_name,
            "hardware_target": self.hardware_target,
            "quant_type": self.quant_type,
            "accuracy_delta": self.accuracy_delta,
            "sha256": self.sha256,
            "download_url": self.download_url,
            "description": self.description,
            "node_count": self.node_count,
            "size_mb": self.size_mb,
            "downloads": self.downloads,
        }


BUILTIN_PACKAGES = [
    MarketplacePackage(
        package_id="tinyllama-q4-esp32x16",
        model_name="TinyLlama 1.1B",
        hardware_target="alloy",
        quant_type="Q4_K_M",
        accuracy_delta=0.05,
        sha256="a1b2c3d4e5f6",
        download_url="https://github.com/tpt-crucible/packages/releases/download/v1/tinyllama-q4-esp32x16.tptpkg",
        description="TinyLlama 1.1B quantized Q4_K_M on 16x ESP32 swarm (4x4 grid)",
        node_count=16,
        size_mb=45.0,
        downloads=1250,
    ),
    MarketplacePackage(
        package_id="tinyllama-q8-alveo",
        model_name="TinyLlama 1.1B",
        hardware_target="fusion",
        quant_type="Q8_0",
        accuracy_delta=0.01,
        sha256="b2c3d4e5f6a7",
        download_url="https://github.com/tpt-crucible/packages/releases/download/v1/tinyllama-q8-alveo.tptpkg",
        description="TinyLlama 1.1B quantized Q8_0 on Xilinx Alveo U280",
        node_count=1,
        size_mb=120.0,
        downloads=890,
    ),
    MarketplacePackage(
        package_id="llama2-7b-q4-alveo",
        model_name="Llama 2 7B",
        hardware_target="fusion",
        quant_type="Q4_K_M",
        accuracy_delta=0.08,
        sha256="c3d4e5f6a7b8",
        download_url="https://github.com/tpt-crucible/packages/releases/download/v1/llama2-7b-q4-alveo.tptpkg",
        description="Llama 2 7B quantized Q4_K_M on Xilinx Alveo U280",
        node_count=1,
        size_mb=450.0,
        downloads=2100,
    ),
]


class Marketplace:
    """Browse and manage pre-compiled packages."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or Path.home() / ".tpt-crucible" / "packages"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.packages = list(BUILTIN_PACKAGES)
        self._load_local_packages()

    def _load_local_packages(self) -> None:
        index_file = self.cache_dir / "index.json"
        if index_file.exists():
            try:
                data = json.loads(index_file.read_text())
                for p in data:
                    self.packages.append(MarketplacePackage(**p))
            except (json.JSONDecodeError, KeyError):
                pass

    def list_packages(self, target: str | None = None) -> list[MarketplacePackage]:
        if target:
            return [p for p in self.packages if p.hardware_target == target]
        return self.packages

    def search(self, query: str) -> list[MarketplacePackage]:
        q = query.lower()
        return [p for p in self.packages if q in p.model_name.lower() or q in p.description.lower()]

    def get_package(self, package_id: str) -> MarketplacePackage | None:
        return next((p for p in self.packages if p.package_id == package_id), None)

    def get_popular(self, limit: int = 5) -> list[MarketplacePackage]:
        return sorted(self.packages, key=lambda p: -p.downloads)[:limit]

    def verify_package(self, package_id: str, file_path: Path) -> bool:
        import hashlib
        pkg = self.get_package(package_id)
        if not pkg:
            return False
        sha256 = hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]
        return sha256 == pkg.sha256
