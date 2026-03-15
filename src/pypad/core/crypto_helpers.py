"""Provide low-level cryptographic helper functions that support secure note and privacy workflows.

This module belongs to the low-level helper layer used by higher-level services and UI code. It helps explain how `pypad.core` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

import base64
import hashlib
import hmac


def b64encode_bytes(data: bytes) -> str:
    """Base64-encode raw bytes."""
    return base64.urlsafe_b64encode(data).decode("ascii")


def b64decode_text(data: str) -> bytes:
    """Base64-decode text into bytes."""
    return base64.urlsafe_b64decode(data.encode("ascii"))


def derive_key_pbkdf2(password: str, salt: bytes, rounds: int, dklen: int = 32) -> bytes:
    """Derive key PBKDF2."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds, dklen=dklen)


def hmac_digest(key: bytes, data: bytes) -> bytes:
    """Compute the HMAC digest for the payload."""
    return hmac.new(key, data, hashlib.sha256).digest()


def compare_digest(a: bytes, b: bytes) -> bool:
    """Compare digest."""
    return hmac.compare_digest(a, b)


def xor_bytes(left: bytes, right: bytes) -> bytes:
    """XOR two byte strings."""
    return bytes(a ^ b for a, b in zip(left, right))


def hmac_counter_keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    """Build an HMAC-based counter keystream."""
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hmac_digest(key, nonce + counter.to_bytes(8, "big"))
        out.extend(block)
        counter += 1
    return bytes(out[:length])