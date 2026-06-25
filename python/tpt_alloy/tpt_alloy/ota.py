"""OTA Update System — incremental firmware updates for swarm nodes."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import hashlib
import json


@dataclass
class FirmwareDiff:
    node_id: int
    changed: bool
    old_hash: str = ""
    new_hash: str = ""
    patch_size: int = 0


@dataclass
class OtaManifest:
    total_nodes: int
    changed_nodes: int
    unchanged_nodes: int
    diffs: list[FirmwareDiff]
    estimated_time_seconds: float = 0.0

    @property
    def update_percentage(self) -> float:
        return self.changed_nodes / max(self.total_nodes, 1) * 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_nodes": self.total_nodes,
            "changed_nodes": self.changed_nodes,
            "unchanged_nodes": self.unchanged_nodes,
            "update_percentage": round(self.update_percentage, 1),
            "estimated_time_seconds": round(self.estimated_time_seconds, 1),
            "diffs": [
                {"node_id": d.node_id, "changed": d.changed, "patch_size": d.patch_size}
                for d in self.diffs
            ],
        }


@dataclass
class NodeFlashStatus:
    node_id: int
    status: str = "pending"
    progress: float = 0.0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status,
            "progress": self.progress,
            "error": self.error,
        }


class OtaManager:
    """Manage OTA firmware updates for swarm nodes."""

    def __init__(self, flash_time_per_node: float = 2.0):
        self.flash_time_per_node = flash_time_per_node

    def compute_diff(
        self,
        old_firmwares: dict[int, bytes],
        new_firmwares: dict[int, bytes],
    ) -> OtaManifest:
        diffs = []
        all_nodes = set(old_firmwares.keys()) | set(new_firmwares.keys())

        for node_id in sorted(all_nodes):
            old = old_firmwares.get(node_id, b"")
            new = new_firmwares.get(node_id, b"")
            changed = old != new
            diffs.append(FirmwareDiff(
                node_id=node_id,
                changed=changed,
                old_hash=hashlib.sha256(old).hexdigest()[:16] if old else "",
                new_hash=hashlib.sha256(new).hexdigest()[:16] if new else "",
                patch_size=len(new) if changed else 0,
            ))

        changed_count = sum(1 for d in diffs if d.changed)
        return OtaManifest(
            total_nodes=len(all_nodes),
            changed_nodes=changed_count,
            unchanged_nodes=len(all_nodes) - changed_count,
            diffs=diffs,
            estimated_time_seconds=changed_count * self.flash_time_per_node,
        )

    def create_patch_manifest(self, manifest: OtaManifest) -> dict[str, Any]:
        changed_nodes = [d for d in manifest.diffs if d.changed]
        return {
            "patch_version": "1.0.0",
            "total_nodes": manifest.total_nodes,
            "changed_nodes": len(changed_nodes),
            "patches": [
                {"node_id": d.node_id, "new_hash": d.new_hash, "size": d.patch_size}
                for d in changed_nodes
            ],
        }

    def flash_nodes(
        self,
        manifest: OtaManifest,
        callback: callable | None = None,
    ) -> list[NodeFlashStatus]:
        statuses = [NodeFlashStatus(node_id=d.node_id) for d in manifest.diffs]

        for status, diff in zip(statuses, manifest.diffs):
            if not diff.changed:
                status.status = "skipped"
                status.progress = 100.0
                continue

            status.status = "flashing"
            status.progress = 50.0
            if callback:
                callback(status)

            status.status = "done"
            status.progress = 100.0
            if callback:
                callback(status)

        return statuses

    def rollback(
        self,
        current_manifest: OtaManifest,
        previous_firmwares: dict[int, bytes],
    ) -> OtaManifest:
        return self.compute_diff(
            {d.node_id: b"" for d in current_manifest.diffs},
            previous_firmwares,
        )
