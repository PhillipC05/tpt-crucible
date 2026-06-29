"""Spark IPC auto-detection — platform-aware socket/pipe presence check."""

from __future__ import annotations
import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SparkDetectionResult:
    detected: bool
    socket_path: str = ""
    platform: str = ""

    def to_dict(self) -> dict:
        return {
            "detected": self.detected,
            "socket_path": self.socket_path,
            "platform": self.platform,
        }


def _socket_candidates() -> list[Path]:
    """Return platform-appropriate IPC socket/pipe paths to probe."""
    if sys.platform == "win32":
        return [Path(r"\\.\pipe\tpt-spark")]
    if sys.platform == "darwin":
        return [Path("/tmp/tpt-spark.sock")]
    # Linux — prefer XDG_RUNTIME_DIR, fall back to /tmp
    xdg = os.environ.get("XDG_RUNTIME_DIR")
    candidates: list[Path] = []
    if xdg:
        candidates.append(Path(xdg) / "tpt-spark.sock")
    candidates.append(Path("/tmp/tpt-spark.sock"))
    return candidates


def detect_spark() -> SparkDetectionResult:
    """Check whether TPT Spark is running by probing its IPC socket/pipe.

    On Windows, named pipes appear as filesystem paths under \\\\.\\\pipe\\.
    On POSIX, we probe for a UNIX domain socket file.
    """
    platform = sys.platform
    for candidate in _socket_candidates():
        try:
            if sys.platform == "win32":
                # Named pipes exist as files under the pipe pseudo-directory.
                if candidate.exists():
                    return SparkDetectionResult(detected=True, socket_path=str(candidate), platform=platform)
            else:
                import stat
                st = candidate.stat()
                if stat.S_ISSOCK(st.st_mode):
                    return SparkDetectionResult(detected=True, socket_path=str(candidate), platform=platform)
        except (OSError, PermissionError):
            continue

    return SparkDetectionResult(detected=False, platform=platform)


def spark_install_url() -> str:
    """Return the TPT Spark repository URL for the install prompt."""
    return "https://github.com/PhillipC05/tpt-spark"
