"""Parallel Firmware Flashing — OTA broadcast and USB parallel flashing."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class FlashTarget:
    node_id: int
    firmware_path: str = ""
    serial_port: str = ""
    ip_address: str = ""
    status: str = "pending"
    progress: float = 0.0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "serial_port": self.serial_port,
            "ip_address": self.ip_address,
            "status": self.status,
            "progress": self.progress,
            "error": self.error,
        }


@dataclass
class FlashJob:
    targets: list[FlashTarget]
    mode: str = "usb"
    total_time_estimate_s: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0

    @property
    def total_nodes(self) -> int:
        return len(self.targets)

    @property
    def completed_nodes(self) -> int:
        return sum(1 for t in self.targets if t.status == "done")

    @property
    def failed_nodes(self) -> int:
        return sum(1 for t in self.targets if t.status == "failed")

    @property
    def overall_progress(self) -> float:
        if not self.targets:
            return 0.0
        return sum(t.progress for t in self.targets) / len(self.targets)

    @property
    def elapsed_s(self) -> float:
        if self.started_at == 0:
            return 0.0
        end = self.completed_at if self.completed_at > 0 else time.time()
        return end - self.started_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_nodes": self.total_nodes,
            "completed_nodes": self.completed_nodes,
            "failed_nodes": self.failed_nodes,
            "overall_progress": round(self.overall_progress, 1),
            "elapsed_s": round(self.elapsed_s, 1),
            "estimated_total_s": round(self.total_time_estimate_s, 1),
            "mode": self.mode,
        }


class ParallelFlasher:
    """Manage parallel firmware flashing across nodes."""

    def __init__(self, flash_time_per_node_s: float = 2.0, parallel_workers: int = 4):
        self.flash_time_per_node_s = flash_time_per_node_s
        self.parallel_workers = parallel_workers

    def estimate_time(self, node_count: int) -> float:
        batches = (node_count + self.parallel_workers - 1) // self.parallel_workers
        return batches * self.flash_time_per_node_s

    def create_job(self, firmware_path: str, ports: list[str] | None = None) -> FlashJob:
        targets = []
        for i, port in enumerate(ports or []):
            targets.append(FlashTarget(
                node_id=i,
                firmware_path=firmware_path,
                serial_port=port,
            ))

        estimated_time = self.estimate_time(len(targets))
        return FlashJob(
            targets=targets,
            mode="usb",
            total_time_estimate_s=estimated_time,
        )

    def create_ota_job(self, firmware_path: str, ip_addresses: list[str] | None = None) -> FlashJob:
        targets = []
        for i, ip in enumerate(ip_addresses or []):
            targets.append(FlashTarget(
                node_id=i,
                firmware_path=firmware_path,
                ip_address=ip,
            ))

        estimated_time = len(targets) * 0.5
        return FlashJob(
            targets=targets,
            mode="ota",
            total_time_estimate_s=estimated_time,
        )

    def simulate_flash(self, job: FlashJob) -> FlashJob:
        job.started_at = time.time()
        for target in job.targets:
            target.status = "flashing"
            target.progress = 50.0
            target.status = "done"
            target.progress = 100.0
        job.completed_at = time.time()
        return job
