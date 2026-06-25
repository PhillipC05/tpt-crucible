"""Tests for KiCad PCB export."""

from pathlib import Path

from tpt_element.kicad import KiCadExporter, KiCadComponent
from tpt_element.weight_map import PhysicalComponent, ComponentType


class TestKiCadExporter:
    def test_add_components(self):
        exporter = KiCadExporter()
        components = [
            PhysicalComponent(
                component_type=ComponentType.RESISTOR,
                value=1000.0, unit="ohm", tolerance=0.05, position=(0, 0),
            ),
            PhysicalComponent(
                component_type=ComponentType.RESISTOR,
                value=2000.0, unit="ohm", tolerance=0.05, position=(0, 1),
            ),
        ]
        exporter.add_components(components)
        assert len(exporter.components) == 2
        assert exporter.components[0].reference == "R1"
        assert exporter.components[1].reference == "R2"

    def test_generate_kicad_pcb(self):
        exporter = KiCadExporter()
        exporter.add_components([
            PhysicalComponent(
                component_type=ComponentType.RESISTOR,
                value=1000.0, unit="ohm", tolerance=0.05, position=(0, 0),
            ),
        ])
        pcb = exporter.generate_kicad_pcb()
        assert "kicad_pcb" in pcb
        assert "R1" in pcb

    def test_generate_schematic(self):
        exporter = KiCadExporter()
        exporter.add_components([
            PhysicalComponent(
                component_type=ComponentType.RESISTOR,
                value=4700.0, unit="ohm", tolerance=0.05, position=(0, 0),
            ),
        ])
        sch = exporter.generate_schematic()
        assert "kicad_sch" in sch

    def test_save_files(self, tmp_path):
        exporter = KiCadExporter()
        exporter.add_components([
            PhysicalComponent(
                component_type=ComponentType.RESISTOR,
                value=1000.0, unit="ohm", tolerance=0.05, position=(0, 0),
            ),
        ])
        files = exporter.save(tmp_path)
        assert files["pcb"].exists()
        assert files["schematic"].exists()

    def test_value_formatting(self):
        exporter = KiCadExporter()
        exporter.add_components([
            PhysicalComponent(
                component_type=ComponentType.RESISTOR,
                value=4700000.0, unit="ohm", tolerance=0.05, position=(0, 0),
            ),
        ])
        assert exporter.components[0].value == "4.7M"

        exporter2 = KiCadExporter()
        exporter2.add_components([
            PhysicalComponent(
                component_type=ComponentType.RESISTOR,
                value=10000.0, unit="ohm", tolerance=0.05, position=(0, 0),
            ),
        ])
        assert exporter2.components[0].value == "10.0K"
