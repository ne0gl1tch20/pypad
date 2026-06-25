"""Persist PyPad document font hints inside otherwise plain text files."""

from __future__ import annotations

import json
from typing import Any

RAW_FONT_BEGIN = "-----BEGIN PYPAD FONT-----"
RAW_FONT_END = "-----END PYPAD FONT-----"
RAW_FONT_REMINDER = "For the best experience, open this raw text file with PyPad."


def sanitize_font_metadata(raw: Any) -> dict[str, Any]:
    """Return a normalized font metadata payload suitable for storing in text."""
    if not isinstance(raw, dict):
        return {}
    family = str(raw.get("family", "") or "").strip()
    if not family:
        return {}
    out: dict[str, Any] = {"family": family[:120]}
    try:
        point_size = int(raw.get("point_size", 0) or 0)
    except Exception:
        point_size = 0
    if 6 <= point_size <= 96:
        out["point_size"] = point_size
    display = str(raw.get("display", "document") or "document").strip().lower()
    if display not in {"document", "editor"}:
        display = "document"
    out["display"] = display
    reminder = str(raw.get("reminder", "") or "").strip() or RAW_FONT_REMINDER
    out["reminder"] = reminder[:240]
    return out


def encode_raw_text_with_font(text: str, metadata: dict[str, Any] | None) -> str:
    """Prefix text with a PyPad font metadata block when metadata is present."""
    cleaned = sanitize_font_metadata(metadata)
    if not cleaned:
        return text
    payload = json.dumps(cleaned, ensure_ascii=False, sort_keys=True)
    body = text
    if body.startswith("\ufeff"):
        body = body.lstrip("\ufeff")
    return f"{RAW_FONT_BEGIN}\n{payload}\n{RAW_FONT_END}\n{body}"


def decode_raw_text_with_font(text: str) -> tuple[str, dict[str, Any] | None]:
    """Extract a leading PyPad font metadata block from raw text."""
    probe = text.lstrip("\ufeff")
    if not probe.startswith(RAW_FONT_BEGIN):
        return text, None
    lines = probe.splitlines(keepends=True)
    if len(lines) < 3:
        return text, None
    if lines[0].strip() != RAW_FONT_BEGIN:
        return text, None
    end_index = None
    for index, line in enumerate(lines[1:10], start=1):
        if line.strip() == RAW_FONT_END:
            end_index = index
            break
    if end_index is None:
        return text, None
    payload_text = "".join(lines[1:end_index]).strip()
    try:
        payload = json.loads(payload_text)
    except Exception:
        return text, None
    metadata = sanitize_font_metadata(payload)
    if not metadata:
        return text, None
    body = "".join(lines[end_index + 1 :])
    return body, metadata
