"""Resolve well-known filesystem paths for settings, logs, recovery data, and other application-managed files.

This module belongs to the application settings layer that resolves defaults, storage paths, and preference migrations. It helps explain how `pypad.app_settings` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def _app_roaming_dir() -> Path:
    """Internal helper for `_app_roaming_dir`."""
    appdata = os.environ.get("APPDATA")
    base_dir = Path(appdata) if appdata else (Path.home() / "AppData" / "Roaming")
    return base_dir / "notepadclone"

def _app_roaming_pypad_dir() -> Path:
    """Internal helper for `_app_roaming_pypad_dir`."""
    appdata = os.environ.get("APPDATA")
    base_dir = Path(appdata) if appdata else (Path.home() / "AppData" / "Roaming")
    return base_dir / "pypad"


def get_settings_file_path() -> Path:
    """Return the value produced by `get_settings_file_path`."""
    return _app_roaming_dir() / "settings.json"


def get_themes_file_path() -> Path:
    """Return the value produced by `get_themes_file_path`."""
    return _app_roaming_dir() / "themes.json"


def get_legacy_settings_file_path() -> Path:
    """Return the value produced by `get_legacy_settings_file_path`."""
    return _app_roaming_dir() / "save.bin"


def get_password_file_path() -> Path:
    """Return the value produced by `get_password_file_path`."""
    return _app_roaming_dir() / "password.bin"


def get_ai_chats_dir_path() -> Path:
    """Return the value produced by `get_ai_chats_dir_path`."""
    return _app_roaming_dir() / "ai_chats"


def get_reminders_file_path() -> Path:
    """Return the value produced by `get_reminders_file_path`."""
    return _app_roaming_dir() / "reminders.json"


def get_autosave_dir_path() -> Path:
    """Return the value produced by `get_autosave_dir_path`."""
    return _app_roaming_dir() / "autosave"


def get_translation_cache_path() -> Path:
    """Return the value produced by `get_translation_cache_path`."""
    return _app_roaming_dir() / "translation_cache.json"


def get_plugins_dir_path() -> Path:
    """Return the value produced by `get_plugins_dir_path`."""
    new_dir = _app_roaming_pypad_dir() / "plugins"
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
    """Return the value produced by `get_debug_logs_file_path`."""
    return _app_roaming_dir() / "debug_logs.log"


def get_crash_logs_file_path() -> Path:
    """Return the value produced by `get_crash_logs_file_path`."""
    return _app_roaming_dir() / "crash_tracebacks.log"
