"""Shared application settings helpers."""

from .coercion import coerce_bool, migrate_settings, normalize_ui_visibility_settings
from .defaults import build_default_settings
from .scintilla_profile import ScintillaProfile
from .paths import (
    get_ai_chats_dir_path,
    get_autosave_dir_path,
    get_crash_logs_file_path,
    get_debug_logs_file_path,
    get_legacy_settings_file_path,
    get_password_file_path,
    get_plugins_dir_path,
    get_reminders_file_path,
    get_settings_file_path,
    get_spellcheck_dictionaries_dir_path,
    get_themes_file_path,
    get_translation_cache_path,
)

__all__ = [
    "build_default_settings",
    "ScintillaProfile",
    "coerce_bool",
    "migrate_settings",
    "normalize_ui_visibility_settings",
    "get_ai_chats_dir_path",
    "get_autosave_dir_path",
    "get_crash_logs_file_path",
    "get_debug_logs_file_path",
    "get_legacy_settings_file_path",
    "get_password_file_path",
    "get_plugins_dir_path",
    "get_reminders_file_path",
    "get_settings_file_path",
    "get_spellcheck_dictionaries_dir_path",
    "get_themes_file_path",
    "get_translation_cache_path",
]
