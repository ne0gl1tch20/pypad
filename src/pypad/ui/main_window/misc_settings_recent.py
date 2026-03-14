"""Manage recent-settings behavior and helper functions for restoring or presenting recent choices.

This module belongs to the main-window orchestration layer that ties together menus, actions, state, and dialogs. It helps explain how `pypad.ui.main_window` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtGui import QAction

from ...app_settings import (
    get_ai_chats_dir_path,
    get_autosave_dir_path,
    get_crash_logs_file_path,
    get_debug_logs_file_path,
    get_legacy_settings_file_path,
    get_password_file_path,
    get_reminders_file_path,
    get_settings_file_path,
    get_themes_file_path,
    get_translation_cache_path,
)
from .notepadpp_pref_runtime import recent_file_max_entries, recent_file_menu_label


class MiscSettingsRecentMixin:
    """Mixin that provides the `MiscSettingsRecentMixin` behavior set."""
    if TYPE_CHECKING:
        def __getattr__(self, name: str) -> Any:
            """Satisfy static type checkers for runtime-resolved window attributes."""
            ...

    @staticmethod
    def _get_settings_file_path() -> Path:
        """Internal helper for `_get_settings_file_path`."""
        return get_settings_file_path()

    @staticmethod
    def _get_themes_file_path() -> Path:
        """Internal helper for `_get_themes_file_path`."""
        return get_themes_file_path()

    @staticmethod
    def _get_legacy_settings_file_path() -> Path:
        """Internal helper for `_get_legacy_settings_file_path`."""
        return get_legacy_settings_file_path()

    @staticmethod
    def _get_password_file_path() -> Path:
        """Internal helper for `_get_password_file_path`."""
        return get_password_file_path()

    @staticmethod
    def _get_reminders_file_path() -> Path:
        """Internal helper for `_get_reminders_file_path`."""
        return get_reminders_file_path()

    @staticmethod
    def _get_autosave_dir_path() -> Path:
        """Internal helper for `_get_autosave_dir_path`."""
        return get_autosave_dir_path()

    @staticmethod
    def _get_translation_cache_path() -> Path:
        """Internal helper for `_get_translation_cache_path`."""
        return get_translation_cache_path()

    @staticmethod
    def _get_ai_chats_dir_path() -> Path:
        """Internal helper for `_get_ai_chats_dir_path`."""
        return get_ai_chats_dir_path()

    @staticmethod
    def _get_debug_logs_file_path() -> Path:
        """Internal helper for `_get_debug_logs_file_path`."""
        return get_debug_logs_file_path()

    @staticmethod
    def _get_crash_logs_file_path() -> Path:
        """Internal helper for `_get_crash_logs_file_path`."""
        return get_crash_logs_file_path()

    def _add_recent_file(self, path: str | None) -> None:
        """Internal helper for `_add_recent_file`."""
        if not path:
            return
        recent = [p for p in self.settings.get("recent_files", []) if isinstance(p, str) and p]
        recent = [p for p in recent if p != path]
        recent.insert(0, path)
        self.settings["recent_files"] = recent[: recent_file_max_entries(self.settings)]
        self._refresh_recent_files_menu()
        self._refresh_favorite_files_menu()

    def _refresh_recent_files_menu(self) -> None:
        """Internal helper for `_refresh_recent_files_menu`."""
        menu = getattr(self, "recent_files_menu", None)
        if menu is None:
            return
        try:
            menu.clear()
        except RuntimeError:
            # Stale Qt wrapper; menus can be recreated during lifecycle/theme/apply cycles.
            self.recent_files_menu = None
            return
        files = [p for p in self.settings.get("recent_files", []) if isinstance(p, str) and p]
        pinned = set(p for p in self.settings.get("pinned_files", []) if isinstance(p, str))
        favorites = set(p for p in self.settings.get("favorite_files", []) if isinstance(p, str))
        if not files:
            action = QAction("(No recent files)", self)
            action.setEnabled(False)
            try:
                menu.addAction(action)
            except RuntimeError:
                self.recent_files_menu = None
            return
        for path in files:
            action = QAction(recent_file_menu_label(self.settings, path), self)
            action.setToolTip(path)
            if path in favorites:
                action.setIcon(self._svg_icon("tab-heart"))
            elif path in pinned:
                action.setIcon(self._svg_icon("tab-pin"))
            action.triggered.connect(lambda _checked=False, p=path: self._open_recent_file(p))
            try:
                menu.addAction(action)
            except RuntimeError:
                self.recent_files_menu = None
                return

    def _refresh_favorite_files_menu(self) -> None:
        """Internal helper for `_refresh_favorite_files_menu`."""
        menu = getattr(self, "favorite_files_menu", None)
        if menu is None:
            return
        try:
            menu.clear()
        except RuntimeError:
            self.favorite_files_menu = None
            return
        files = [p for p in self.settings.get("favorite_files", []) if isinstance(p, str) and p]
        pinned = set(p for p in self.settings.get("pinned_files", []) if isinstance(p, str))
        if not files:
            action = QAction("(No favorite files)", self)
            action.setEnabled(False)
            try:
                menu.addAction(action)
            except RuntimeError:
                self.favorite_files_menu = None
            return
        for path in files:
            action = QAction(path, self)
            if path in pinned:
                action.setIcon(self._svg_icon("tab-pin"))
            else:
                action.setIcon(self._svg_icon("tab-heart"))
            action.triggered.connect(lambda _checked=False, p=path: self._open_recent_file(p))
            try:
                menu.addAction(action)
            except RuntimeError:
                self.favorite_files_menu = None
                return
