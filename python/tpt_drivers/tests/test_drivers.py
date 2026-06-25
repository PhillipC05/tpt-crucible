"""Tests for TPT Drivers module."""

from pathlib import Path
import json

from tpt_drivers.driver import (
    DriverManifest, BomEntry, PowerProfile,
    SynthesisConstraints, PinMapping,
)
from tpt_drivers.registry import DriverRegistry
from tpt_drivers.bom import BomGenerator


def _make_test_manifest() -> DriverManifest:
    return DriverManifest(
        name="xilinx_alveo_u280",
        version="1.0.0",
        hardware_type="fpga",
        description="Xilinx Alveo U280 FPGA accelerator card",
        synthesis=SynthesisConstraints(max_clock_mhz=300, max_dsp_slices=9024),
        power=PowerProfile(idle_mw=50, active_mw=75, peak_mw=225, voltage_v=12.0),
        bom=[
            BomEntry(part_number="XCUI30P-FSGD2104-2L-E", description="FPGA chip", quantity=1,
                     supplier="DigiKey", supplier_sku="1234", unit_price_usd=8500.0),
            BomEntry(part_number="AS4C256M16D4A", description="DDR4 SDRAM", quantity=4,
                     supplier="Mouser", supplier_sku="5678", unit_price_usd=12.50),
        ],
        flash_protocol="jtag",
        telemetry_adapter="fpga_axi",
    )


class TestDriverManifest:
    def test_to_dict_roundtrip(self):
        manifest = _make_test_manifest()
        d = manifest.to_dict()
        restored = DriverManifest.from_dict(d)
        assert restored.name == "xilinx_alveo_u280"
        assert restored.version == "1.0.0"
        assert len(restored.bom) == 2

    def test_to_toml(self):
        manifest = _make_test_manifest()
        toml = manifest.to_toml()
        assert 'name = "xilinx_alveo_u280"' in toml
        assert "max_clock_mhz" in toml
        assert "active_mw" in toml

    def test_power_profile(self):
        manifest = _make_test_manifest()
        assert manifest.power.active_mw == 75
        assert manifest.power.voltage_v == 12.0


class TestDriverRegistry:
    def test_install_and_list(self, tmp_path):
        registry = DriverRegistry(registry_dir=tmp_path)
        manifest = _make_test_manifest()
        path = registry.install_driver(manifest)
        assert path.exists()
        assert (path / "driver.toml").exists()

        drivers = registry.list_drivers()
        assert len(drivers) == 1
        assert drivers[0].name == "xilinx_alveo_u280"

    def test_get_driver(self, tmp_path):
        registry = DriverRegistry(registry_dir=tmp_path)
        manifest = _make_test_manifest()
        registry.install_driver(manifest)
        loaded = registry.get_driver("xilinx_alveo_u280")
        assert loaded is not None
        assert loaded.hardware_type == "fpga"

    def test_search(self, tmp_path):
        registry = DriverRegistry(registry_dir=tmp_path)
        registry.install_driver(_make_test_manifest())
        results = registry.search("alveo")
        assert len(results) == 1

    def test_uninstall(self, tmp_path):
        registry = DriverRegistry(registry_dir=tmp_path)
        registry.install_driver(_make_test_manifest())
        assert registry.uninstall("xilinx_alveo_u280") is True
        assert registry.get_driver("xilinx_alveo_u280") is None


class TestBomGenerator:
    def test_add_driver(self):
        gen = BomGenerator()
        manifest = _make_test_manifest()
        gen.add_driver(manifest, node_count=1)
        assert gen.get_total_components() == 5
        assert gen.get_total_cost() > 0

    def test_multiple_nodes(self):
        gen = BomGenerator()
        manifest = _make_test_manifest()
        gen.add_driver(manifest, node_count=4)
        fpga_items = [i for i in gen.items.values() if "FPGA" in i.description]
        assert fpga_items[0].quantity == 4

    def test_to_csv(self):
        gen = BomGenerator()
        gen.add_driver(_make_test_manifest())
        csv = gen.to_csv()
        assert "Part Number" in csv
        assert "XCUI30P" in csv

    def test_to_dict(self):
        gen = BomGenerator()
        gen.add_driver(_make_test_manifest())
        d = gen.to_dict()
        assert "total_cost_usd" in d
        assert len(d["items"]) == 2
