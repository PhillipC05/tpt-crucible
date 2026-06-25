"""Tests for PlatformIO integration."""

from pathlib import Path

from tpt_alloy.firmware import FirmwareTarget, generate_firmware
from tpt_alloy.partition import Partition
from tpt_alloy.platformio import generate_platformio_ini, generate_flash_script


class TestPlatformIO:
    def test_generate_platformio_ini_esp32(self, tmp_path):
        path = generate_platformio_ini(FirmwareTarget.ESP32, tmp_path)
        assert path.exists()
        content = path.read_text()
        assert "esp32dev" in content
        assert "espressif32" in content

    def test_generate_platformio_ini_rp2040(self, tmp_path):
        path = generate_platformio_ini(FirmwareTarget.RP2040, tmp_path)
        assert path.exists()
        content = path.read_text()
        assert "rpipicow" in content

    def test_generate_flash_script(self, tmp_path):
        bundles = [
            generate_firmware(Partition(node_id=0, assigned_layers=[0, 1]), FirmwareTarget.ESP32),
            generate_firmware(Partition(node_id=1, assigned_layers=[2, 3]), FirmwareTarget.ESP32),
        ]
        script_path = tmp_path / "flash_all.sh"
        result = generate_flash_script(bundles, script_path)
        assert result.exists()
        content = script_path.read_text()
        assert "Flashing node 0" in content
        assert "Flashing node 1" in content

    def test_flash_script_with_ports(self, tmp_path):
        bundles = [
            generate_firmware(Partition(node_id=0, assigned_layers=[0]), FirmwareTarget.ESP32),
        ]
        script_path = tmp_path / "flash_all.sh"
        result = generate_flash_script(bundles, script_path, serial_ports=["COM3"])
        assert result.exists()
        content = script_path.read_text()
        assert "COM3" in content
