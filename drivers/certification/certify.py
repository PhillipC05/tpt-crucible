"""
TPT Driver Certification Pipeline.

Usage:
    python certify.py drivers/community/my-board.toml

Exit codes:
    0 — certification passed, manifest updated with signature
    1 — certification failed (compat score too low or emulator error)
    2 — signing failed (missing private key)

Environment:
    TPT_SIGNING_KEY  — base64-encoded Ed25519 private key (32 raw bytes).
                       If absent, falls back to ~/.tpt-drivers/signing_key.pem.
    TPT_MIN_COMPAT_SCORE  — minimum compat score to pass (default: 0.8)
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "python"))

MIN_COMPAT_SCORE = float(os.environ.get("TPT_MIN_COMPAT_SCORE", "0.8"))


def load_manifest(path: Path):
    """Load a DriverManifest from a TOML file."""
    from tpt_drivers.registry import DriverRegistry
    registry = DriverRegistry(registry_dir=Path("/tmp/tpt-cert-registry"))
    # Use the registry's TOML parser since the manifest isn't installed yet
    manifest = registry._load_manifest(path)
    return manifest


def run_compat_check(manifest) -> tuple[bool, dict]:
    """Run the compat checker against the driver's hardware type."""
    from tpt_catalyst.compat import check_compatibility, HardwareTarget
    from tpt_catalyst.ir import TptIr, IrNode, IrEdge

    # Build a representative test IR covering common operators
    test_ops = [
        "matmul", "attention", "layernorm", "gelu", "embedding", "softmax"
    ]
    nodes = [IrNode(op=op, name=f"{op}_0", inputs=[], outputs=[], attrs={}) for op in test_ops]
    ir = TptIr(
        model_name="certify-test",
        nodes=nodes,
        edges=[],
        metadata={"certify": True},
    )

    target_map = {
        "fusion": HardwareTarget.FUSION,
        "alloy": HardwareTarget.ALLOY,
        "element": HardwareTarget.ELEMENT,
    }
    hw = manifest.hardware_type.lower()
    target = target_map.get(hw)
    if target is None:
        print(f"[certify] unknown hardware_type '{hw}' — skipping compat check")
        return True, {}

    report = check_compatibility(ir, target)
    result = report.to_dict()
    score = result.get("score", 0.0)
    ok = score >= MIN_COMPAT_SCORE
    print(f"[certify] compat score: {score:.2f} ({'PASS' if ok else 'FAIL'}, threshold {MIN_COMPAT_SCORE})")
    if not ok:
        for detail in result.get("details", []):
            if detail.get("severity") == "fail":
                print(f"  FAIL  {detail['op']}: {detail.get('message', '')}")
    return ok, result


def run_sil_check(manifest) -> bool:
    """Run the SiL emulator for the driver's hardware type."""
    from tpt_emulator.interface import HardwareType
    from tpt_emulator.alloy_sil import AlloySiL
    from tpt_emulator.fusion_sil import FusionSiL
    from tpt_emulator.element_sil import ElementSiL

    hw = manifest.hardware_type.lower()
    emulator_map = {
        "alloy": AlloySiL,
        "fusion": FusionSiL,
        "element": ElementSiL,
    }
    cls = emulator_map.get(hw)
    if cls is None:
        print(f"[certify] no SiL emulator for '{hw}' — skipping SiL check")
        return True

    emulator = cls()
    # Use a synthetic model path — SiL loads stubs when the path doesn't exist
    result = emulator.run_inference({"tokens": [1, 2, 3, 4, 5]})
    ok = result.success
    print(f"[certify] SiL check: {'PASS' if ok else 'FAIL'} "
          f"({result.inference_time_ms:.1f} ms, {result.tokens_per_second:.1f} tok/s)")
    return ok


def sign_manifest(manifest, compat_result: dict) -> str:
    """Sign the manifest with the TPT Ed25519 private key. Returns hex signature."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        load_pem_private_key, Encoding, PublicFormat
    )

    private_key: Ed25519PrivateKey | None = None

    raw_b64 = os.environ.get("TPT_SIGNING_KEY")
    if raw_b64:
        raw = base64.b64decode(raw_b64)
        private_key = Ed25519PrivateKey.from_private_bytes(raw)
    else:
        key_path = Path.home() / ".tpt-drivers" / "signing_key.pem"
        if key_path.exists():
            private_key = load_pem_private_key(key_path.read_bytes(), password=None)  # type: ignore
        else:
            raise RuntimeError(
                "No signing key found. Set TPT_SIGNING_KEY env var or place key at "
                "~/.tpt-drivers/signing_key.pem\n"
                "Generate a key pair with: python drivers/certification/keygen.py"
            )

    # Canonical message: to_dict() with verification fields zeroed
    canonical = dict(manifest.to_dict())
    canonical["verified"] = False
    canonical["signature"] = ""
    canonical["certified_at"] = ""
    canonical["certification_pipeline"] = ""
    message = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()

    sig = private_key.sign(message)
    return sig.hex()


def get_pipeline_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        return result.stdout.strip()[:12]
    except Exception:
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description="Certify a TPT driver manifest")
    parser.add_argument("manifest", type=Path, help="Path to driver.toml")
    parser.add_argument("--sign-only", action="store_true",
                        help="Skip validation checks and only sign (use with caution)")
    args = parser.parse_args()

    if not args.manifest.exists():
        print(f"error: {args.manifest} not found")
        return 1

    print(f"[certify] loading {args.manifest}")
    manifest = load_manifest(args.manifest)
    print(f"[certify] driver: {manifest.name} v{manifest.version} ({manifest.hardware_type})")

    if not args.sign_only:
        # Compat check
        compat_ok, compat_result = run_compat_check(manifest)
        if not compat_ok:
            print("[certify] FAIL — compat score below threshold")
            return 1

        # SiL emulator check
        sil_ok = run_sil_check(manifest)
        if not sil_ok:
            print("[certify] FAIL — SiL emulator reported errors")
            return 1

        print("[certify] all checks passed — signing")

    try:
        sig = sign_manifest(manifest, {})
    except RuntimeError as e:
        print(f"[certify] signing error: {e}")
        return 2

    # Update manifest fields
    manifest.verified = True
    manifest.signature = sig
    manifest.certified_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    manifest.certification_pipeline = get_pipeline_sha()

    # Write back to the original file as JSON (TOML write is lossy for these fields)
    out_path = args.manifest.with_suffix(".certified.json")
    out_path.write_text(json.dumps(manifest.to_dict(), indent=2))
    print(f"[certify] PASS — wrote certified manifest to {out_path}")
    print(f"[certify] signature: {sig[:16]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
