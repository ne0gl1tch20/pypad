"""Provide note-encryption helpers used by the security features in the user interface.

This module belongs to the note privacy and security UI layer. It helps explain how
`pypad.ui.security` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

import json
import os
import re

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from pypad.core.crypto_helpers import (
    b64decode_text,
    b64encode_bytes,
    compare_digest,
    derive_key_pbkdf2,
    hmac_counter_keystream,
    hmac_digest,
    xor_bytes,
)

HEADER = "ENCNOTE1"
ARMORED_BEGIN = "PYPAD_ENCNOTE_BEGIN"
ARMORED_END = "PYPAD_ENCNOTE_END"
ARMORED_NOTICE = "This file has been encrypted by PyPad."

PBKDF2_ROUNDS_V1 = 200_000
PBKDF2_ROUNDS_V2 = 600_000
FORMAT_VERSION_V1 = 1
FORMAT_VERSION_V2 = 2
AEAD_NAME = "aes-256-gcm"
KDF_NAME = "pbkdf2-sha256"

_FIELD_RE = re.compile(r"^([a-z_]+):(.*)$")


def _b64encode(data: bytes) -> str:
    """Encode bytes using the shared URL-safe base64 helper."""
    return b64encode_bytes(data)


def _b64decode(data: str) -> bytes:
    """Decode text using the shared URL-safe base64 helper."""
    return b64decode_text(data)


def _derive_key_v1(password: str, salt: bytes) -> bytes:
    """Derive the legacy v1 key used by the original custom note format."""
    return derive_key_pbkdf2(password, salt, rounds=PBKDF2_ROUNDS_V1, dklen=32)


def _derive_key_v2(password: str, salt: bytes) -> bytes:
    """Derive the v2 AES-GCM key."""
    return derive_key_pbkdf2(password, salt, rounds=PBKDF2_ROUNDS_V2, dklen=32)


def _keystream_v1(key: bytes, nonce: bytes, length: int) -> bytes:
    """Build the legacy v1 HMAC counter-mode keystream."""
    return hmac_counter_keystream(key, nonce, length)


def is_encrypted_payload(text: str) -> bool:
    """Return whether the supplied text looks like a PyPad encrypted payload."""
    return text.startswith(HEADER + "\n") or text.startswith(ARMORED_BEGIN + "\n")


def _parse_armored_payload(payload_text: str) -> dict[str, str]:
    """Parse the armored note format."""
    lines = payload_text.splitlines()
    if len(lines) < 3 or lines[0] != ARMORED_BEGIN or lines[-1] != ARMORED_END:
        raise ValueError("Invalid encrypted payload")
    fields: dict[str, str] = {}
    for line in lines[1:-1]:
        if not line or line == ARMORED_NOTICE:
            continue
        match = _FIELD_RE.match(line)
        if not match:
            continue
        fields[match.group(1)] = match.group(2)
    return fields


def _serialize_armored_payload(*, version: int, salt: bytes, nonce: bytes, cipher: bytes, verifier: bytes) -> str:
    """Serialize the armored payload written to disk."""
    return "\n".join(
        [
            ARMORED_BEGIN,
            ARMORED_NOTICE,
            "encrypted_marker:pypad",
            f"version:{version}",
            f"header:{HEADER}",
            f"kdf:{KDF_NAME}",
            f"rounds:{PBKDF2_ROUNDS_V2 if version == FORMAT_VERSION_V2 else PBKDF2_ROUNDS_V1}",
            f"aead:{AEAD_NAME}" if version == FORMAT_VERSION_V2 else "cipher:legacy-hmac-stream",
            f"encrypted_contents:{_b64encode(cipher)}",
            f"encrypted_password:{_b64encode(verifier)}",
            f"salt:{_b64encode(salt)}",
            f"nonce:{_b64encode(nonce)}",
            "pypad_command:encrypted_note",
            ARMORED_END,
        ]
    )


def encrypt_text(plain_text: str, password: str) -> str:
    """Encrypt text using the current versioned AES-GCM note format."""
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _derive_key_v2(password, salt)
    plain = plain_text.encode("utf-8")
    aad = f"{ARMORED_BEGIN}|{HEADER}|v{FORMAT_VERSION_V2}|{KDF_NAME}|{AEAD_NAME}".encode("utf-8")
    cipher = AESGCM(key).encrypt(nonce, plain, aad)
    verifier = hmac_digest(key, b"pypad-note-password-check")
    return _serialize_armored_payload(
        version=FORMAT_VERSION_V2,
        salt=salt,
        nonce=nonce,
        cipher=cipher,
        verifier=verifier,
    )


def _decrypt_armored_v2(fields: dict[str, str], password: str) -> str:
    """Decrypt the current AES-GCM armored payload."""
    salt = _b64decode(fields["salt"])
    nonce = _b64decode(fields["nonce"])
    cipher = _b64decode(fields["encrypted_contents"])
    verifier = _b64decode(fields["encrypted_password"])
    key = _derive_key_v2(password, salt)
    expected_verifier = hmac_digest(key, b"pypad-note-password-check")
    if not compare_digest(verifier, expected_verifier):
        raise ValueError("Wrong password or corrupted payload")
    aad = f"{ARMORED_BEGIN}|{HEADER}|v{FORMAT_VERSION_V2}|{KDF_NAME}|{AEAD_NAME}".encode("utf-8")
    try:
        plain = AESGCM(key).decrypt(nonce, cipher, aad)
    except InvalidTag as exc:
        raise ValueError("Wrong password or corrupted payload") from exc
    try:
        return plain.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Decrypted data is invalid UTF-8") from exc


def _decrypt_armored_v1(fields: dict[str, str], password: str) -> str:
    """Decrypt the older armored v1 custom format."""
    salt = _b64decode(fields["salt"])
    nonce = _b64decode(fields["nonce"])
    cipher = _b64decode(fields["encrypted_contents"])
    tag = _b64decode(fields["encrypted_password"])
    key = _derive_key_v1(password, salt)
    mac_key = hmac_digest(key, b"mac")
    expected = hmac_digest(mac_key, nonce + cipher)
    if not compare_digest(tag, expected):
        raise ValueError("Wrong password or corrupted payload")
    stream = _keystream_v1(key, nonce, len(cipher))
    plain = xor_bytes(cipher, stream)
    try:
        return plain.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Decrypted data is invalid UTF-8") from exc


def _decrypt_legacy_json_v1(payload_text: str, password: str) -> str:
    """Decrypt the oldest JSON-based v1 payload format."""
    raw = payload_text.split("\n", 1)[1]
    payload = json.loads(raw)
    salt = _b64decode(payload["s"])
    nonce = _b64decode(payload["n"])
    cipher = _b64decode(payload["c"])
    tag = _b64decode(payload["t"])
    key = _derive_key_v1(password, salt)
    mac_key = hmac_digest(key, b"mac")
    expected = hmac_digest(mac_key, nonce + cipher)
    if not compare_digest(tag, expected):
        raise ValueError("Wrong password or corrupted payload")
    stream = _keystream_v1(key, nonce, len(cipher))
    plain = xor_bytes(cipher, stream)
    try:
        return plain.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Decrypted data is invalid UTF-8") from exc


def decrypt_text(payload_text: str, password: str) -> str:
    """Decrypt any supported PyPad note-encryption payload version."""
    if not is_encrypted_payload(payload_text):
        raise ValueError("Not an encrypted note payload")
    try:
        if payload_text.startswith(ARMORED_BEGIN + "\n"):
            fields = _parse_armored_payload(payload_text)
            version = int(str(fields.get("version", FORMAT_VERSION_V1) or FORMAT_VERSION_V1))
            if version >= FORMAT_VERSION_V2:
                return _decrypt_armored_v2(fields, password)
            return _decrypt_armored_v1(fields, password)
        return _decrypt_legacy_json_v1(payload_text, password)
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Invalid encrypted payload") from exc
