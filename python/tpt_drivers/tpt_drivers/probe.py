"""Hardware Auto-Detection — USB/serial device probing."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import platform
import subprocess


@dataclass
class DetectedDevice:
    port: str
    description: str
    vid: str = ""
    pid: str = ""
    driver_name: str = ""
    driver_version: str = ""
    confirmed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "port": self.port,
            "description": self.description,
            "vid": self.vid,
            "pid": self.pid,
            "driver_name": self.driver_name,
            "driver_version": self.driver_version,
            "confirmed": self.confirmed,
        }


VID_PID_MAP: dict[str, str] = {
    "303A": "esp32",
    "1A86": "ch340",
    "10C4": "cp2102",
    "2341": "arduino",
    "2A03": "arduino_alt",
    "1209": "picocom",
}


class DeviceProbe:
    """Probe for connected hardware devices via USB/serial."""

    def __init__(self):
        self.platform = platform.system()

    def probe_usb_devices(self) -> list[DetectedDevice]:
        if self.platform == "Windows":
            return self._probe_windows()
        elif self.platform == "Linux":
            return self._probe_linux()
        elif self.platform == "Darwin":
            return self._probe_macos()
        return []

    def _probe_windows(self) -> list[DetectedDevice]:
        devices = []
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Get-WmiObject Win32_SerialPort | Select-Object DeviceID, Description"],
                capture_output=True, text=True, timeout=10,
            )
            for line in result.stdout.strip().split("\n"):
                if "COM" in line:
                    parts = line.split()
                    port = parts[0] if parts else ""
                    desc = " ".join(parts[1:]) if len(parts) > 1 else ""
                    devices.append(DetectedDevice(port=port, description=desc))
        except Exception:
            pass
        return devices

    def _probe_linux(self) -> list[DetectedDevice]:
        devices = []
        try:
            result = subprocess.run(
                ["ls", "-la", "/dev/ttyUSB*", "/dev/ttyACM*"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.strip().split("\n"):
                if "tty" in line:
                    parts = line.split()
                    port = parts[-1] if parts else ""
                    devices.append(DetectedDevice(
                        port=port,
                        description="USB Serial Device",
                    ))
        except Exception:
            pass
        return devices

    def _probe_macos(self) -> list[DetectedDevice]:
        devices = []
        try:
            result = subprocess.run(
                ["ls", "-la", "/dev/tty.usbserial*", "/dev/tty.usbmodem*"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.strip().split("\n"):
                if "tty" in line:
                    parts = line.split()
                    port = parts[-1] if parts else ""
                    devices.append(DetectedDevice(
                        port=port,
                        description="USB Serial Device",
                    ))
        except Exception:
            pass
        return devices

    def identify_driver(self, device: DetectedDevice) -> DetectedDevice:
        for vid, driver_name in VID_PID_MAP.items():
            if vid in device.description.upper() or vid in device.vid.upper():
                device.driver_name = driver_name
                return device
        return device

    def auto_detect_all(self) -> list[DetectedDevice]:
        devices = self.probe_usb_devices()
        for device in devices:
            self.identify_driver(device)
        return devices


class DriverLookup:
    """Map detected devices to installed drivers."""

    def __init__(self, registry_dir: Path | None = None):
        self.registry_dir = registry_dir or Path.home() / ".tpt-drivers"

    def lookup(self, device: DetectedDevice) -> str | None:
        index_file = self.registry_dir / "index.json"
        if not index_file.exists():
            return None

        index = json.loads(index_file.read_text())
        for name, info in index.items():
            if device.driver_name and device.driver_name in name.lower():
                return name
            if device.vid and device.vid in str(info):
                return name
        return None
