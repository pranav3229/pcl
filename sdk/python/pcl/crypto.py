"""Cryptographic signing and verification for PCL Attestations."""

from __future__ import annotations

import base64
from typing import Any
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    load_pem_public_key,
)

SUPPORTED_ALGORITHMS = {"ed25519", "ecdsa-p256-sha256"}


def generate_ed25519_keypair() -> tuple[ed25519.Ed25519PrivateKey, str]:
    """Generate an Ed25519 private key and base64-encoded raw public key."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    pub_bytes = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    pub_b64 = base64.b64encode(pub_bytes).decode("ascii")
    return private_key, pub_b64


def generate_ecdsa_p256_keypair() -> tuple[ec.EllipticCurvePrivateKey, str]:
    """Generate an ECDSA P-256 private key and base64-encoded SubjectPublicKeyInfo."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    pub_bytes = public_key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    pub_b64 = base64.b64encode(pub_bytes).decode("ascii")
    return private_key, pub_b64


def sign_digest(
    private_key: Any,
    digest_bytes: bytes,
    algorithm: str = "ed25519",
) -> str:
    """Sign raw digest bytes using the specified private key.

    Returns base64-encoded signature string.
    """
    if algorithm == "ed25519":
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise TypeError("Expected Ed25519PrivateKey for algorithm ed25519")
        sig = private_key.sign(digest_bytes)
        return base64.b64encode(sig).decode("ascii")
    elif algorithm == "ecdsa-p256-sha256":
        if not isinstance(private_key, ec.EllipticCurvePrivateKey):
            raise TypeError("Expected EllipticCurvePrivateKey for algorithm ecdsa-p256-sha256")
        sig = private_key.sign(digest_bytes, ec.ECDSA(hashes.SHA256()))
        return base64.b64encode(sig).decode("ascii")
    else:
        raise ValueError(f"Unsupported cryptographic algorithm '{algorithm}'. Must be one of {SUPPORTED_ALGORITHMS}")


def verify_signature(
    public_key_input: Any,
    signature_b64: str,
    digest_bytes: bytes,
    algorithm: str = "ed25519",
) -> bool:
    """Verify signature over digest_bytes using public key.

    Accepts public key as:
    - Raw base64 string
    - Hex string
    - cryptography PublicKey object

    Returns True if valid; raises or returns False if invalid.
    """
    if algorithm not in SUPPORTED_ALGORITHMS:
        return False

    try:
        sig_bytes = base64.b64decode(signature_b64)
    except Exception:
        return False

    try:
        if algorithm == "ed25519":
            if isinstance(public_key_input, ed25519.Ed25519PublicKey):
                pub = public_key_input
            elif isinstance(public_key_input, str):
                try:
                    pub_bytes = base64.b64decode(public_key_input)
                except Exception:
                    pub_bytes = bytes.fromhex(public_key_input)
                pub = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            elif isinstance(public_key_input, bytes):
                pub = ed25519.Ed25519PublicKey.from_public_bytes(public_key_input)
            else:
                return False

            pub.verify(sig_bytes, digest_bytes)
            return True

        elif algorithm == "ecdsa-p256-sha256":
            if isinstance(public_key_input, ec.EllipticCurvePublicKey):
                pub = public_key_input
            elif isinstance(public_key_input, (str, bytes)):
                if isinstance(public_key_input, str):
                    try:
                        pub_bytes = base64.b64decode(public_key_input)
                    except Exception:
                        pub_bytes = bytes.fromhex(public_key_input)
                else:
                    pub_bytes = public_key_input

                # Try DER format first, then raw encoded point
                try:
                    from cryptography.hazmat.primitives.serialization import load_der_public_key
                    pub = load_der_public_key(pub_bytes)
                except Exception:
                    pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), pub_bytes)
            else:
                return False

            pub.verify(sig_bytes, digest_bytes, ec.ECDSA(hashes.SHA256()))
            return True

    except InvalidSignature:
        return False
    except Exception:
        return False

    return False
