"""Safe-save helpers used by security-profile aware file operations."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile

from pypad.ui.security.security_profile import profile_setting


SCRIPT_LIKE_SUFFIXES = {".ps1", ".bat", ".cmd", ".py", ".exe"}


def build_effective_save_policy(window, tab) -> dict[str, object]:
    """Build the save policy used for one save operation."""
    resolved = window._resolved_security_policy()
    is_encrypted = bool(getattr(tab, "encryption_enabled", False))
    return {
        "save_policy": resolved.save_policy,
        "atomic_replace": bool(profile_setting(window.settings, "safe_save_atomic_replace", True)) and resolved.save_policy in {"safe_strict", "safe_default"},
        "backup_on_overwrite": (not is_encrypted) and bool(profile_setting(window.settings, "safe_save_backup_on_overwrite", True)) and resolved.save_policy in {"safe_strict", "safe_default"},
        "warn_script_extensions": bool(profile_setting(window.settings, "safe_save_warn_script_extensions", True)) and resolved.profile_id in {"beginner", "balanced"},
        "block_untrusted_overwrite": bool(profile_setting(window.settings, "safe_save_block_untrusted_overwrite", True)),
        "require_save_as_for_untrusted": bool(profile_setting(window.settings, "untrusted_note_require_save_as", True)),
        "is_untrusted": bool(getattr(window, "_is_tab_untrusted", lambda _tab: False)(tab)),
        "is_encrypted": is_encrypted,
    }


def safe_write_text(path: str, payload: str, encoding: str, *, atomic_replace: bool, backup_on_overwrite: bool) -> None:
    """Write text to disk, optionally using backup plus atomic replacement."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not atomic_replace:
        with open(target, "w", encoding=encoding, errors="replace") as handle:
            handle.write(payload)
        return
    if backup_on_overwrite and target.exists():
        backup_path = target.with_suffix(target.suffix + ".bak")
        shutil.copy2(target, backup_path)
    fd, tmp_path = tempfile.mkstemp(prefix=f"{target.name}.", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding, errors="replace") as handle:
            handle.write(payload)
        os.replace(tmp_path, target)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception:
            pass
