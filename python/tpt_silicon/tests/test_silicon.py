"""Tests for TPT Silicon CIM module."""

import numpy as np

from tpt_silicon.weight_packer import CimWeightPacker, PackedArray
from tpt_silicon.array_layout import CimArrayLayout, LayoutConfig, ArrayTile
from tpt_silicon.bitline import BitlineOpGenerator, BitlineOp


class TestCimWeightPacker:
    def test_quantize_weights(self):
        packer = CimWeightPacker(bit_precision=8)
        weights = np.array([[0.0, 0.5, 1.0], [0.25, 0.75, 0.1]])
        quantized = packer.quantize_weights(weights)
        assert quantized.dtype == np.uint8
        assert quantized.min() == 0
        assert quantized.max() == 255

    def test_quantize_4bit(self):
        packer = CimWeightPacker(bit_precision=4)
        weights = np.array([[0.0, 1.0]])
        quantized = packer.quantize_weights(weights, bits=4)
        assert quantized.max() <= 15

    def test_serialize_roundtrip(self):
        packer = CimWeightPacker()
        weights = np.random.rand(4, 4).astype(np.float32)
        packed = packer.pack_weights(weights)
        data = packer.serialize_array(packed)
        restored = packer.deserialize_array(data)
        assert restored.rows == packed.rows
        assert restored.cols == packed.cols
        assert restored.data == packed.data


class TestCimArrayLayout:
    def test_from_config(self):
        config = LayoutConfig(array_rows=256, array_cols=256, bit_precision=8)
        layout = CimArrayLayout.from_config(config)
        assert layout.config.array_rows == 256

    def test_map_layer(self):
        config = LayoutConfig(array_rows=64, array_cols=64)
        layout = CimArrayLayout.from_config(config)
        tiles = layout.map_layer("fc1", input_dim=128, output_dim=128)
        assert len(tiles) == 4
        assert layout.get_total_tiles() == 4

    def test_to_dict(self):
        config = LayoutConfig(array_rows=32, array_cols=32)
        layout = CimArrayLayout.from_config(config)
        layout.map_layer("layer0", 64, 64)
        d = layout.to_dict()
        assert "config" in d
        assert d["total_tiles"] == 4


class TestBitlineOpGenerator:
    def test_read_rows(self):
        gen = BitlineOpGenerator()
        op = gen.read_rows(tile_id=0, row_start=0, row_end=32)
        assert op.op_type == "read"
        assert len(gen.get_ops()) == 1

    def test_matmul_sequence(self):
        gen = BitlineOpGenerator()
        ops = gen.matmul_sequence(tile_id=0, input_rows=64, weight_cols=128)
        assert len(ops) > 0
        assert any(op.op_type == "accumulate" for op in ops)

    def test_masked_read(self):
        gen = BitlineOpGenerator()
        op = gen.masked_read(tile_id=0, row_start=0, row_end=32, mask=[1, 0, 1, 0])
        assert op.mask is not None
        assert len(op.mask) == 4

    def test_to_dict(self):
        gen = BitlineOpGenerator()
        gen.read_rows(0, 0, 16)
        gen.accumulate(0)
        result = gen.to_dict()
        assert len(result) == 2
        assert result[0]["op_type"] == "read"
