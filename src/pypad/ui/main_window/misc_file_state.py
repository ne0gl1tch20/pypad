"""Manage per-file UI state such as dirty tracking, metadata, and restoration details.

This module belongs to the main-window orchestration layer that ties together menus, actions, state, and dialogs. It helps explain how `pypad.ui.main_window` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import QMessageBox

from pypad.ui.editor.editor_tab import EditorTab


class MiscFileStateMixin:
    """Mixin that provides the `MiscFileStateMixin` behavior set."""
    if TYPE_CHECKING:
        def __getattr__(self, name: str) -> Any:
            """Satisfy static type checkers for runtime-resolved window attributes."""
            ...

    def _notify_large_file_mode(self, tab: EditorTab) -> None:
        """Handle notify large file mode."""
        if not tab.large_file:
            tab.large_file_notice_shown = False
            return
        if tab.large_file_notice_shown:
            return
        tab.large_file_notice_shown = True
        if getattr(tab, "partial_large_preview", False):
            self.show_status_message(
                "Large File Preview mode: partial content loaded; use 'Load Full Large File' before editing/saving.",
                7000,
            )
        else:
            self.show_status_message(
                "Large File Mode enabled: syntax highlighting, markdown formatting, and snapshots are limited.",
                6000,
            )

    def reload_tab_from_disk(self, tab: EditorTab) -> None:
        """Handle reload tab from disk."""
        if not tab.current_file:
            return
        if tab.text_edit.is_modified():
            ret = QMessageBox.warning(
                self,
                "Reload Tab",
                "This tab has unsaved changes.\n\nReload from disk and discard changes?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                return
        try:
            encoding = tab.encoding or self._encoding_for_path(tab.current_file)
            text, encrypted, password = self._load_text_from_path(tab.current_file, encoding=encoding)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Reload Failed", f"Could not reload file:\n{e}")
            return
        tab.text_edit.set_text(text)
        tab.encoding = encoding if not encrypted else "utf-8"
        tab.eol_mode = self._detect_eol_mode(text)
        try:
            threshold_kb = int(self.settings.get("large_file_threshold_kb", 2048))
            tab.large_file = int(Path(tab.current_file).stat().st_size / 1024) >= threshold_kb
        except Exception:
            tab.large_file = False
        tab.encryption_enabled = encrypted
        tab.encryption_password = password
        tab.partial_large_preview = False
        tab.large_file_total_lines = max(1, text.count("\n") + 1)
        tab.large_file_total_chars = len(text)
        tab.markdown_mode_enabled = self._is_markdown_path(tab.current_file) and not tab.large_file
        if tab is self.active_tab() and hasattr(self, "_sync_markdown_preview_for_active_tab"):
            self._sync_markdown_preview_for_active_tab()
        self._notify_large_file_mode(tab)
        tab.text_edit.set_modified(False)
        self._apply_file_metadata_to_tab(tab)
        self._apply_syntax_highlighting(tab)
        self._refresh_tab_title(tab)
        self.update_window_title()

    def _set_file_read_only(self, path: str, read_only: bool) -> bool:
        """Set file read only."""
        try:
            mode = os.stat(path).st_mode
            if read_only:
                os.chmod(path, mode & ~0o222)
            else:
                os.chmod(path, mode | 0o222)
            return True
        except OSError:
            return False

    def toggle_tab_read_only(self, tab: EditorTab) -> None:
        """Enable or disable read-only mode for the active tab."""
        if not tab.current_file:
            return
        new_state = not self._is_path_read_only(tab.current_file)
        if not self._set_file_read_only(tab.current_file, new_state):
            QMessageBox.warning(self, "Read-Only", "Could not update read-only attribute.")
            return
        tab.read_only = new_state
        tab.text_edit.set_read_only(tab.read_only)
        self._refresh_tab_title(tab)
        self.show_status_message("Read-only enabled" if tab.read_only else "Read-only disabled", 3000)

    def set_tab_color(self, tab: EditorTab, color_hex: str | None) -> None:
        """Apply a new custom color to the active tab and refresh its visuals."""
        tab.tab_color = color_hex
        self._apply_tab_color(tab)
        self._persist_file_metadata_for_tab(tab)

    def _update_path_references(self, old: str, new: str) -> None:
        """Update path references."""
        if old == new:
            return
        def _replace_in_list(values: list[str]) -> list[str]:
            """Handle replace in list."""
            return [new if p == old else p for p in values]

        self.settings["recent_files"] = _replace_in_list(self.settings.get("recent_files", []))
        self.settings["pinned_files"] = _replace_in_list(self.settings.get("pinned_files", []))
        self.settings["favorite_files"] = _replace_in_list(self.settings.get("favorite_files", []))
        tags_map = self.settings.get("file_tags", {})
        if isinstance(tags_map, dict) and old in tags_map:
            tags_map[new] = tags_map.pop(old)
        colors_map = self.settings.get("file_colors", {})
        if isinstance(colors_map, dict) and old in colors_map:
            colors_map[new] = colors_map.pop(old)
        enc_map = self.settings.get("file_encodings", {})
        if isinstance(enc_map, dict) and old in enc_map:
            enc_map[new] = enc_map.pop(old)
        eol_map = self.settings.get("file_eol_modes", {})
        if isinstance(eol_map, dict) and old in eol_map:
            eol_map[new] = eol_map.pop(old)
        self.settings["file_tags"] = tags_map
        self.settings["file_colors"] = colors_map
        self.settings["file_encodings"] = enc_map
        self.settings["file_eol_modes"] = eol_map
        self._refresh_recent_files_menu()
        self._refresh_favorite_files_menu()
        if hasattr(self, "_refresh_file_watcher"):
            self._refresh_file_watcher()
