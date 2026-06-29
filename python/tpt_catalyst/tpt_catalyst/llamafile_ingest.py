"""Llamafile header-strip ingestion — detect .llamafile magic bytes, skip executable prefix, route to GGUF ingestion."""

from __future__ import annotations
from pathlib import Path
from typing import Any
import struct

from .ir import TptIr, OpNode, Edge, ModelMetadata, ComputationalGraph


# Llamafile magic bytes: ELF magic + "LlamaFile" marker
ELF_MAGIC = b"\x7fELF"
LLAMAFILE_MAGIC = b"LlamaFile"
LLAMAFILE_MAGIC_OFFSET = 0x08  # Offset where "LlamaFile" appears in the header

# GGUF magic for routing
GGUF_MAGIC = b"GGUF"


def detect_llamafile(path: Path) -> bool:
    """Detect if a file is a llamafile (ELF executable with embedded GGUF).

    Llamafile format: ELF executable prefix + GGUF model data.
    The "LlamaFile" magic appears somewhere in the first 64 bytes of the ELF header.
    """
    try:
        with open(path, "rb") as f:
            header = f.read(128)
            if len(header) < 32:
                return False
            # Check ELF magic
            if header[:4] != ELF_MAGIC:
                return False
            # Check for LlamaFile marker anywhere in the first 128 bytes
            if LLAMAFILE_MAGIC in header[:128]:
                return True
            return False
    except (OSError, IOError):
        return False


def find_gguf_offset(path: Path) -> int:
    """Find the byte offset where GGUF data starts in a llamafile.

    The GGUF data is appended after the ELF executable. We scan for the
    GGUF magic bytes to find the start of the model data.
    """
    try:
        with open(path, "rb") as f:
            # Read in chunks to find GGUF magic
            chunk_size = 4096
            offset = 0
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                # Check for GGUF magic in this chunk
                pos = chunk.find(GGUF_MAGIC)
                if pos != -1:
                    return offset + pos
                offset += len(chunk)
                # Keep last 4 bytes to handle boundary crossing
                if len(chunk) == chunk_size:
                    f.seek(offset - 4)
                    offset -= 4
        return -1
    except (OSError, IOError):
        return -1


def extract_gguf_from_llamafile(path: Path, output_dir: Path | None = None) -> Path:
    """Extract the GGUF data from a llamafile and write it to a new file.

    Returns the path to the extracted GGUF file.
    """
    gguf_offset = find_gguf_offset(path)
    if gguf_offset < 0:
        raise ValueError(f"Could not find GGUF data in {path}")

    if output_dir is None:
        output_dir = path.parent

    output_path = output_dir / f"{path.stem}.gguf"

    with open(path, "rb") as src:
        src.seek(gguf_offset)
        gguf_data = src.read()

    output_path.write_bytes(gguf_data)
    return output_path


def ingest_llamafile(path: Path) -> TptIr:
    """Ingest a llamafile by stripping the executable prefix and routing to GGUF ingestion.

    Llamafile format is an ELF executable with GGUF model data appended.
    This function detects the format, finds the GGUF offset, extracts the
    model data, and routes it through the GGUF ingestion pipeline.
    """
    if not detect_llamafile(path):
        return _stub_llamafile(path)

    gguf_offset = find_gguf_offset(path)
    if gguf_offset < 0:
        return _stub_llamafile(path)

    # Read the GGUF portion directly from the llamafile
    try:
        with open(path, "rb") as f:
            f.seek(gguf_offset)
            gguf_header = f.read(256)  # Read enough for GGUF header parsing

        # Route to GGUF ingestion by creating a temporary file
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".gguf", delete=False) as tmp:
            with open(path, "rb") as src:
                src.seek(gguf_offset)
                while True:
                    chunk = src.read(65536)
                    if not chunk:
                        break
                    tmp.write(chunk)
            tmp_path = Path(tmp.name)

        try:
            from .gguf_ingest import ingest_gguf
            ir = ingest_gguf(tmp_path)
            # Update source format to indicate llamafile origin
            ir.metadata.source_format = "llamafile"
            ir.metadata.name = path.stem
            return ir
        finally:
            os.unlink(tmp_path)

    except Exception:
        return _stub_llamafile(path)


def _stub_llamafile(path: Path) -> TptIr:
    """Stub when llamafile parsing fails."""
    return TptIr(
        version="1.0.0",
        metadata=ModelMetadata(
            name=path.stem,
            source_format="llamafile",
            parameter_count=0,
        ),
        graph=ComputationalGraph(),
    )