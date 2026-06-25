"""Hardware-Locked Model IP Protection — bind packages to specific hardware."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import hashlib
import json
import time


@dataclass
class HardwareLock:
    fingerprint_sha256: str
    lock_type: str = "hardware_bound"
    locked_at: float = 0.0
    issuer: str = "tpt-crucible"
    allowed_ids: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.locked_at == 0.0:
            self.locked_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint_sha256": self.fingerprint_sha256,
            "lock_type": self.lock_type,
            "locked_at": self.locked_at,
            "issuer": self.issuer,
            "allowed_ids": self.allowed_ids,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HardwareLock:
        return cls(
            fingerprint_sha256=data["fingerprint_sha256"],
            lock_type=data.get("lock_type", "hardware_bound"),
            locked_at=data.get("locked_at", 0.0),
            issuer=data.get("issuer", "tpt-crucible"),
            allowed_ids=data.get("allowed_ids", []),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def create_lock(hardware_ids: list[str]) -> HardwareLock:
    sorted_ids = sorted(hardware_ids)
    combined = "|".join(sorted_ids)
    fingerprint = hashlib.sha256(combined.encode()).hexdigest()

    return HardwareLock(
        fingerprint_sha256=fingerprint,
        lock_type="hardware_bound",
        allowed_ids=sorted_ids,
    )


def verify_lock(lock: HardwareLock, present_ids: list[str]) -> bool:
    if not lock.allowed_ids:
        return True
    present_set = set(present_ids)
    allowed_set = set(lock.allowed_ids)
    return present_set.issubset(allowed_set)


def fingerprint_hardware(hw_info: dict[str, Any]) -> str:
    parts = []
    for key in sorted(hw_info.keys()):
        parts.append(f"{key}={hw_info[key]}")
    combined = "|".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()
