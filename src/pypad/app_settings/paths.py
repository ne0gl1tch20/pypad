"""Resolve well-known filesystem paths for settings, logs, recovery data, and other application-managed files.

This module belongs to the application settings layer that resolves defaults, storage paths, and preference migrations. It helps explain how `pypad.app_settings` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from .portable_mode import get_portable_mode_state


def _storage_root() -> Path:
    """Return the active application-data root, honoring portable mode when enabled."""

    portable = get_portable_mode_state()
    if portable.enabled and portable.root is not None:
        return portable.root / "pypad"
    return _app_roaming_dir()


def _pypad_storage_root() -> Path:
    """Return the Pypad-specific storage root for newer paths and migrations."""

    portable = get_portable_mode_state()
    if portable.enabled and portable.root is not None:
        return portable.root / "pypad"
    return _app_roaming_pypad_dir()


def _app_roaming_dir() -> Path:
    """Return the roaming application-data directory."""
    appdata = os.environ.get("APPDATA")
    base_dir = Path(appdata) if appdata else (Path.home() / "AppData" / "Roaming")
    return base_dir / "notepadclone"

def _app_roaming_pypad_dir() -> Path:
    """Return the Pypad roaming application-data directory."""
    appdata = os.environ.get("APPDATA")
    base_dir = Path(appdata) if appdata else (Path.home() / "AppData" / "Roaming")
    return base_dir / "pypad"


def get_settings_file_path() -> Path:
    """Return the path to the main settings file."""
    return _storage_root() / "settings.json"


def get_themes_file_path() -> Path:
    """Return the path to the saved themes file."""
    return _storage_root() / "themes.json"


def get_legacy_settings_file_path() -> Path:
    """Return the path to the legacy settings file."""
    return _storage_root() / "save.bin"


def get_password_file_path() -> Path:
    """Return the path to the encrypted password store."""
    return _storage_root() / "password.bin"


def get_ai_chats_dir_path() -> Path:
    """Return the directory used to store AI chat sessions."""
    return _storage_root() / "ai_chats"


def get_reminders_file_path() -> Path:
    """Return the path to the reminders data file."""
    return _storage_root() / "reminders.json"


def get_autosave_dir_path() -> Path:
    """Return the directory used for autosave snapshots."""
    return _storage_root() / "autosave"


def get_translation_cache_path() -> Path:
    """Return the path to the translation cache file."""
    return _storage_root() / "translation_cache.json"


def get_spellcheck_dictionaries_dir_path() -> Path:
    """Return the directory used to store Hunspell dictionaries for spellcheck."""
    return _storage_root() / "hunspell"


def get_plugins_dir_path() -> Path:
    """Return the plugins directory path."""
    new_dir = _pypad_storage_root() / "plugins"
    legacy_dir = _app_roaming_dir() / "plugins"
    if not new_dir.exists() and legacy_dir.exists():
        try:
            new_dir.mkdir(parents=True, exist_ok=True)
            for child in legacy_dir.iterdir():
                target = new_dir / child.name
                if target.exists():
                    continue
                if child.is_dir():
                    shutil.copytree(child, target)
                else:
                    shutil.copy2(child, target)
        except Exception:
            # If migration fails, still prefer returning the new location.
            pass
    return new_dir


def get_debug_logs_file_path() -> Path:
    """Return the path to the debug logs file."""
    return _storage_root() / "debug_logs.log"


def get_crash_logs_file_path() -> Path:
    """Return the path to the crash logs file."""
    return _storage_root() / "crash_tracebacks.log"
