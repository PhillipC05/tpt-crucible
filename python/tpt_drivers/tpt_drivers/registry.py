"""Driver registry — local cache, install, search."""

from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .driver import DriverManifest

# Path to the TPT public key bundled with the SDK (Ed25519, PEM format).
_PUBLIC_KEY_PATH = Path(__file__).parent / "keys" / "tpt_public.pem"


def _verify_signature(manifest: DriverManifest) -> bool:
    """Return True if the manifest's Ed25519 signature is valid, False otherwise."""
    if not manifest.signature:
        return False
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        from cryptography.exceptions import InvalidSignature
        import hashlib

        pem = _PUBLIC_KEY_PATH.read_bytes()
        public_key: Ed25519PublicKey = load_pem_public_key(pem)  # type: ignore[assignment]

        # Signature covers the canonical JSON of to_dict() with verification fields zeroed
        canonical = dict(manifest.to_dict())
        canonical["verified"] = False
        canonical["signature"] = ""
        canonical["certified_at"] = ""
        canonical["certification_pipeline"] = ""
        message = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()

        sig_bytes = bytes.fromhex(manifest.signature)
        public_key.verify(sig_bytes, message)
        return True
    except InvalidSignature:
        return False
    except Exception:
        return False


@dataclass
class RegistryEntry:
    name: str
    version: str
    hardware_type: str
    description: str
    verified: bool = False
    local_path: Path | None = None


class DriverRegistry:
    """Local driver registry with install/search capabilities."""

    def __init__(self, registry_dir: Path | None = None):
        self.registry_dir = registry_dir or Path.home() / ".tpt-drivers"
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.registry_dir / "index.json"
        self.index: dict[str, dict[str, Any]] = self._load_index()

    def _load_index(self) -> dict[str, dict[str, Any]]:
        if self.index_path.exists():
            try:
                return json.loads(self.index_path.read_text())
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_index(self) -> None:
        self.index_path.write_text(json.dumps(self.index, indent=2))

    def install_driver(self, manifest: DriverManifest, source_path: Path | None = None) -> Path:
        driver_dir = self.registry_dir / manifest.name / manifest.version
        driver_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = driver_dir / "driver.toml"
        manifest_path.write_text(manifest.to_toml())

        if source_path and source_path.exists():
            import shutil
            target = driver_dir / source_path.name
            shutil.copy2(source_path, target)

        self.index[manifest.name] = {
            "version": manifest.version,
            "hardware_type": manifest.hardware_type,
            "description": manifest.description,
            "path": str(driver_dir),
        }
        self._save_index()
        return driver_dir

    def get_driver(self, name: str) -> DriverManifest | None:
        entry = self.index.get(name)
        if not entry:
            return None
        manifest_path = Path(entry["path"]) / "driver.toml"
        if manifest_path.exists():
            return self._load_manifest(manifest_path)
        return None

    def list_drivers(self) -> list[RegistryEntry]:
        return [
            RegistryEntry(
                name=name,
                version=data["version"],
                hardware_type=data["hardware_type"],
                description=data["description"],
                verified=data.get("verified", False),
                local_path=Path(data["path"]) if Path(data["path"]).exists() else None,
            )
            for name, data in self.index.items()
        ]

    def search(self, query: str) -> list[RegistryEntry]:
        q = query.lower()
        return [
            entry for entry in self.list_drivers()
            if q in entry.name.lower() or q in entry.description.lower() or q in entry.hardware_type.lower()
        ]

    def uninstall(self, name: str) -> bool:
        if name in self.index:
            del self.index[name]
            self._save_index()
            return True
        return False

    def _load_manifest(self, path: Path) -> DriverManifest:
        content = path.read_text()
        data: dict[str, Any] = {}
        current_section = data
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("["):
                section_name = line.strip("[]")
                data[section_name] = {}
                current_section = data[section_name]
            elif "=" in line:
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"')
                try:
                    current_section[key] = float(val)
                except ValueError:
                    current_section[key] = val

        driver_data = data.get("driver", {})
        syn_data = data.get("synthesis", {})
        pw_data = data.get("power", {})

        from .driver import SynthesisConstraints, PowerProfile
        return DriverManifest(
            name=driver_data.get("name", "unknown"),
            version=driver_data.get("version", "0.1.0"),
            hardware_type=driver_data.get("hardware_type", "unknown"),
            description=driver_data.get("description", ""),
            synthesis=SynthesisConstraints(
                max_clock_mhz=syn_data.get("max_clock_mhz", 200.0),
                max_luts=int(syn_data.get("max_luts", 0)),
                max_dsp_slices=int(syn_data.get("max_dsp_slices", 0)),
                max_bram_kbits=int(syn_data.get("max_bram_kbits", 0)),
            ),
            power=PowerProfile(
                idle_mw=pw_data.get("idle_mw", 0.0),
                active_mw=pw_data.get("active_mw", 0.0),
                peak_mw=pw_data.get("peak_mw", 0.0),
                voltage_v=pw_data.get("voltage_v", 3.3),
            ),
            flash_protocol=driver_data.get("flash_protocol", "serial"),
            telemetry_adapter=driver_data.get("telemetry_adapter", "default"),
        )
