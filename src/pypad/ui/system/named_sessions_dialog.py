"""Provide a list-detail manager for named sessions stored inside PyPad settings.

The dialog is designed for keyboard-first browsing so users can inspect, open,
rename, duplicate, or delete session entries without treating sessions as raw files.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from pypad.ui.theme.theme_tokens import build_dialog_theme_qss_from_tokens, build_tokens_from_settings


class NamedSessionsDialog(QDialog):
    """Manage named session entries using a simple list-detail desktop layout."""

    def __init__(self, parent, sessions: dict[str, dict[str, Any]]) -> None:
        """Build the dialog and populate it with the supplied named-session entries."""
        super().__init__(parent)
        self._selected_name: str | None = None
        self.setWindowTitle("Named Sessions")
        self.resize(920, 560)
        self.setAccessibleName("Named sessions dialog")
        self.setAccessibleDescription(
            "Browse saved named sessions, review their summaries, and open or manage them."
        )
        tokens = build_tokens_from_settings(getattr(parent, "settings", {}))
        self.setStyleSheet(build_dialog_theme_qss_from_tokens(tokens))

        root = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(QLabel("Saved sessions", self))
        self.list_widget = QListWidget(self)
        self.list_widget.setAccessibleName("Named sessions list")
        left.addWidget(self.list_widget, 1)
        root.addLayout(left, 1)

        right = QVBoxLayout()
        right.addWidget(QLabel("Session details", self))
        self.details = QTextEdit(self)
        self.details.setReadOnly(True)
        self.details.setAccessibleName("Session details panel")
        right.addWidget(self.details, 1)

        buttons = QHBoxLayout()
        self.open_btn = QPushButton("Open", self)
        self.rename_btn = QPushButton("Rename", self)
        self.duplicate_btn = QPushButton("Duplicate", self)
        self.delete_btn = QPushButton("Delete", self)
        self.close_btn = QPushButton("Close", self)
        for button in (self.open_btn, self.rename_btn, self.duplicate_btn, self.delete_btn, self.close_btn):
            buttons.addWidget(button)
        right.addLayout(buttons)
        root.addLayout(right, 2)

        for name in sorted(sessions.keys(), key=str.lower):
            item = QListWidgetItem(name, self.list_widget)
            item.setData(32, sessions[name])
        self.list_widget.currentItemChanged.connect(self._refresh_details)
        self.open_btn.clicked.connect(self._accept_open)
        self.rename_btn.clicked.connect(lambda: self.done(2))
        self.duplicate_btn.clicked.connect(lambda: self.done(3))
        self.delete_btn.clicked.connect(lambda: self.done(4))
        self.close_btn.clicked.connect(self.reject)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)

    @property
    def selected_name(self) -> str | None:
        """Return the session name associated with the current selection."""
        return self._selected_name

    def _refresh_details(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        """Update the details pane for the selected session entry."""
        if current is None:
            self._selected_name = None
            self.details.clear()
            return
        self._selected_name = current.text()
        payload = current.data(32) or {}
        session = payload.get("payload", {}) if isinstance(payload, dict) else {}
        files = session.get("files", []) if isinstance(session, dict) else []
        unsaved = session.get("unsaved_tabs", []) if isinstance(session, dict) else []
        workspace = str(session.get("workspace_root", "") or "") if isinstance(session, dict) else ""
        created_at = str(payload.get("created_at", "") or "") if isinstance(payload, dict) else ""
        updated_at = str(payload.get("updated_at", "") or "") if isinstance(payload, dict) else ""
        summary = [
            f"Name: {self._selected_name}",
            f"Created: {created_at or 'Unknown'}",
            f"Updated: {updated_at or 'Unknown'}",
            f"Workspace: {workspace or '(none)'}",
            f"Saved files: {len(files) if isinstance(files, list) else 0}",
            f"Unsaved tabs: {len(unsaved) if isinstance(unsaved, list) else 0}",
        ]
        self.details.setPlainText("\n".join(summary))

    def _accept_open(self) -> None:
        """Accept the dialog using the current selection as the open target."""
        if self._selected_name:
            self.accept()
