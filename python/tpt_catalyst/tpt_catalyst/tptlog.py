"""`.tptlog` binary format — timestamped telemetry stream for replay and time-travel debug."""

from __future__ import annotations
import struct
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MAGIC = b"TPTL"
FORMAT_VERSION = 1


@dataclass
class TptLogEntry:
    timestamp_ms: int
    hardware_type: str
    node_id: str
    metrics: dict[str, Any]

    def to_bytes(self) -> bytes:
        payload = json.dumps(self.metrics).encode("utf-8")
        hw = self.hardware_type.encode("utf-8")
        nid = self.node_id.encode("utf-8")
        return struct.pack(
            "<Q H H I",
            self.timestamp_ms,
            len(hw),
            len(nid),
            len(payload),
        ) + hw + nid + payload

    @classmethod
    def from_bytes(cls, data: bytes, offset: int = 0) -> tuple[TptLogEntry, int]:
        ts, hw_len, nid_len, pay_len = struct.unpack_from("<Q H H I", data, offset)
        pos = offset + 16
        hw = data[pos:pos + hw_len].decode("utf-8")
        pos += hw_len
        nid = data[pos:pos + nid_len].decode("utf-8")
        pos += nid_len
        metrics = json.loads(data[pos:pos + pay_len].decode("utf-8"))
        pos += pay_len
        return cls(timestamp_ms=ts, hardware_type=hw, node_id=nid, metrics=metrics), pos


@dataclass
class TptLogHeader:
    magic: bytes = MAGIC
    version: int = FORMAT_VERSION
    entry_count: int = 0
    start_time_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_bytes(self) -> bytes:
        meta_json = json.dumps(self.metadata).encode("utf-8")
        return struct.pack(
            "<4s I I Q I",
            self.magic,
            self.version,
            self.entry_count,
            self.start_time_ms,
            len(meta_json),
        ) + meta_json

    @classmethod
    def from_bytes(cls, data: bytes) -> tuple[TptLogHeader, int]:
        header_size = struct.calcsize("<4s I I Q I")
        magic, ver, count, start, meta_len = struct.unpack_from("<4s I I Q I", data, 0)
        meta = json.loads(data[header_size:header_size + meta_len].decode("utf-8"))
        return cls(magic=magic, version=ver, entry_count=count, start_time_ms=start, metadata=meta), header_size + meta_len


class TptLogWriter:
    """Write telemetry entries to a `.tptlog` file."""

    def __init__(self, path: Path, metadata: dict[str, Any] | None = None):
        self.path = path
        self.entries: list[TptLogEntry] = []
        self.start_time_ms = int(time.time() * 1000)
        self.metadata = metadata or {}

    def record(self, hardware_type: str, node_id: str, metrics: dict[str, Any]) -> None:
        self.entries.append(TptLogEntry(
            timestamp_ms=int(time.time() * 1000) - self.start_time_ms,
            hardware_type=hardware_type,
            node_id=node_id,
            metrics=metrics,
        ))

    def save(self) -> None:
        header = TptLogHeader(
            entry_count=len(self.entries),
            start_time_ms=self.start_time_ms,
            metadata=self.metadata,
        )
        with open(self.path, "wb") as f:
            f.write(header.to_bytes())
            for entry in self.entries:
                f.write(entry.to_bytes())


class TptLogReader:
    """Read and replay telemetry entries from a `.tptlog` file."""

    def __init__(self, path: Path):
        self.path = path
        self.header: TptLogHeader | None = None
        self.entries: list[TptLogEntry] = []

    def load(self) -> None:
        data = self.path.read_bytes()
        self.header, offset = TptLogHeader.from_bytes(data)
        self.entries = []
        while offset < len(data):
            entry, offset = TptLogEntry.from_bytes(data, offset)
            self.entries.append(entry)

    def get_entries(
        self,
        hardware_type: str | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> list[TptLogEntry]:
        result = self.entries
        if hardware_type:
            result = [e for e in result if e.hardware_type == hardware_type]
        if start_ms is not None:
            result = [e for e in result if e.timestamp_ms >= start_ms]
        if end_ms is not None:
            result = [e for e in result if e.timestamp_ms <= end_ms]
        return result

    def summary(self) -> dict[str, Any]:
        if not self.header:
            return {}
        return {
            "entry_count": self.header.entry_count,
            "duration_ms": self.entries[-1].timestamp_ms if self.entries else 0,
            "hardware_types": list({e.hardware_type for e in self.entries}),
            "node_ids": list({e.node_id for e in self.entries}),
        }
