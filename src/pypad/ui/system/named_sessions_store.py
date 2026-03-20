"""Persist named session entries that wrap the existing PyPad session payload format.

This store keeps the current ad hoc session save/load workflow intact while adding
an always-available library of named sessions inside application settings.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def load_named_sessions(settings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return normalized named-session entries from the settings payload."""
    raw = settings.get("named_sessions_store", {})
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(raw, dict):
        return out
    for key, value in raw.items():
        name = str(key or "").strip()
        if not name or not isinstance(value, dict):
            continue
        payload = value.get("payload", {})
        if not isinstance(payload, dict):
            continue
        out[name] = {
            "payload": payload,
            "created_at": str(value.get("created_at", "") or ""),
            "updated_at": str(value.get("updated_at", "") or ""),
        }
    return out


def save_named_session(
    settings: dict[str, Any],
    *,
    name: str,
    payload: dict[str, Any],
    existing: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Insert or update one named session entry and return the new store mapping."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    store = dict(existing or load_named_sessions(settings))
    created_at = str(store.get(name, {}).get("created_at", "") or now)
    store[name] = {
        "payload": dict(payload),
        "created_at": created_at,
        "updated_at": now,
    }
    settings["named_sessions_store"] = store
    return store
