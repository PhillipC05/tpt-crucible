"""
Generate an Ed25519 keypair for TPT driver signing.

The public key is committed to the repository (drivers/certification/keys/tpt_public.pem).
The private key must be stored securely (GitHub Actions secret TPT_SIGNING_KEY as base64).

Usage:
    python drivers/certification/keygen.py

Outputs:
    - drivers/certification/keys/tpt_public.pem  (commit this)
    - ~/.tpt-drivers/signing_key.pem              (keep secret, do NOT commit)
    - TPT_SIGNING_KEY=<base64>                    (paste into GitHub Actions secret)
"""

import base64
import sys
from pathlib import Path

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PublicFormat, PrivateFormat, NoEncryption
    )
except ImportError:
    print("error: install cryptography: pip install cryptography")
    sys.exit(1)

private_key = Ed25519PrivateKey.generate()
public_key = private_key.public_key()

public_pem = public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
private_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.Raw, NoEncryption())
private_raw = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())

keys_dir = Path(__file__).parent / "keys"
keys_dir.mkdir(exist_ok=True)
pub_path = keys_dir / "tpt_public.pem"
pub_path.write_bytes(public_pem)

priv_path = Path.home() / ".tpt-drivers" / "signing_key.pem"
priv_path.parent.mkdir(parents=True, exist_ok=True)
priv_path.write_bytes(private_pem)
priv_path.chmod(0o600)

b64_key = base64.b64encode(private_raw).decode()

print(f"Public key written to:  {pub_path}")
print(f"Private key written to: {priv_path}")
print()
print("Add this to GitHub Actions secrets as TPT_SIGNING_KEY:")
print(b64_key)
print()
print(f"Commit {pub_path} to the repository.")
print("NEVER commit the private key.")
