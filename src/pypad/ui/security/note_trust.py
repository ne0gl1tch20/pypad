"""Helpers for classifying, persisting, and enforcing note trust state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path

from pypad.ui.security.security_profile import ResolvedSecurityPolicy


TRUSTED = "trusted"
UNTRUSTED = "untrusted"
SESSION_TRUSTED = "session_trusted"


@dataclass(frozen=True)
class NoteTrustDecision:
    state: str
    source: str
    persisted: bool
    reason: str | None = None


def normalize_trust_path(path: str) -> str:
    """Normalize a path for trust-store keying."""
    return os.path.normcase(os.path.abspath(str(path)))


def stat_fingerprint(path: str) -> tuple[int | None, int | None]:
    """Return size and mtime for trust invalidation checks."""
    try:
        st = Path(path).stat()
        return int(st.st_size), int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)))
    except Exception:
        return None, None


def build_persisted_trust_record(path: str, *, state: str, source: str, profile_id: str) -> dict[str, object]:
    """Build a trust-store record for a trusted note."""
    size, mtime_ns = stat_fingerprint(path)
    return {
        "state": state,
        "source": source,
        "persisted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "profile_id": profile_id,
        "last_seen_mtime_ns": mtime_ns,
        "last_seen_size": size,
    }


def persisted_trust_is_valid(record: dict[str, object], path: str, policy: ResolvedSecurityPolicy) -> bool:
    """Validate a persisted trust decision against current file state."""
    if str(record.get("state", "")).strip() != TRUSTED:
        return False
    if policy.profile_id != "beginner":
        return True
    size, mtime_ns = stat_fingerprint(path)
    return (
        record.get("last_seen_size") == size
        and record.get("last_seen_mtime_ns") == mtime_ns
    )


def is_under_workspace(path: str, workspace_root: str) -> bool:
    """Return whether path is inside the workspace root."""
    root = str(workspace_root or "").strip()
    if not root:
        return False
    try:
        root_path = Path(root).resolve()
        file_path = Path(path).resolve()
        return root_path == file_path or root_path in file_path.parents
    except Exception:
        return False


def classify_note_trust(
    *,
    path: str | None,
    open_origin: str,
    workspace_root: str,
    trust_known_workspace_files: bool,
    persisted_record: dict[str, object] | None,
    policy: ResolvedSecurityPolicy,
) -> NoteTrustDecision:
    """Classify the initial trust state for a note."""
    normalized_origin = str(open_origin or "unknown").strip().lower() or "unknown"
    if path and persisted_record and persisted_trust_is_valid(persisted_record, path, policy):
        return NoteTrustDecision(TRUSTED, str(persisted_record.get("source", normalized_origin) or normalized_origin), True)
    if normalized_origin in {"internal_template", "new_document", "template", "app_generated"}:
        return NoteTrustDecision(TRUSTED, "template", False, "Created inside the app.")
    if path and trust_known_workspace_files and is_under_workspace(path, workspace_root):
        return NoteTrustDecision(TRUSTED, "workspace", False, "File is inside the active workspace.")
    if normalized_origin in {"startup_arg", "file_dialog", "recovery", "plugin", "external_open", "local_open"}:
        return NoteTrustDecision(UNTRUSTED, normalized_origin, False, "External content opens read-only until trusted.")
    return NoteTrustDecision(TRUSTED, normalized_origin, False)
