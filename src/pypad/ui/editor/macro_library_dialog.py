"""Provide a clearer manager for saved macros with preview, rename, and shortcut editing.

This dialog upgrades the older input-box-only flow into a list-detail editor so
users can inspect what a macro will do before running or modifying it.
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


class MacroLibraryDialog(QDialog):
    """Manage saved macros using a keyboard-friendly list-detail workflow."""

    def __init__(self, parent, macros: dict[str, dict[str, Any]]) -> None:
        """Build the dialog and display the supplied normalized saved macros."""
        super().__init__(parent)
        self._selected_name: str | None = None
        self.setWindowTitle("Macro Library")
        self.resize(920, 560)
        self.setAccessibleName("Macro library dialog")
        self.setAccessibleDescription(
            "Browse, inspect, run, rename, export, or delete saved macros."
        )
        tokens = build_tokens_from_settings(getattr(parent, "settings", {}))
        self.setStyleSheet(build_dialog_theme_qss_from_tokens(tokens))

        root = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(QLabel("Saved macros", self))
        self.list_widget = QListWidget(self)
        self.list_widget.setAccessibleName("Saved macros list")
        left.addWidget(self.list_widget, 1)
        root.addLayout(left, 1)

        right = QVBoxLayout()
        right.addWidget(QLabel("Macro details", self))
        self.details = QTextEdit(self)
        self.details.setReadOnly(True)
        self.details.setAccessibleName("Macro details preview")
        right.addWidget(self.details, 1)

        buttons = QHBoxLayout()
        self.run_btn = QPushButton("Run", self)
        self.rename_btn = QPushButton("Rename", self)
        self.shortcut_btn = QPushButton("Edit Shortcut", self)
        self.delete_btn = QPushButton("Delete", self)
        self.close_btn = QPushButton("Close", self)
        for button in (self.run_btn, self.rename_btn, self.shortcut_btn, self.delete_btn, self.close_btn):
            buttons.addWidget(button)
        right.addLayout(buttons)
        root.addLayout(right, 2)

        for name in sorted(macros.keys(), key=str.lower):
            item = QListWidgetItem(name, self.list_widget)
            item.setData(32, macros[name])
        self.list_widget.currentItemChanged.connect(self._refresh_details)
        self.run_btn.clicked.connect(self.accept)
        self.rename_btn.clicked.connect(lambda: self.done(2))
        self.shortcut_btn.clicked.connect(lambda: self.done(3))
        self.delete_btn.clicked.connect(lambda: self.done(4))
        self.close_btn.clicked.connect(self.reject)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)

    @property
    def selected_name(self) -> str | None:
        """Return the currently selected saved macro name."""
        return self._selected_name

    def _refresh_details(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        """Update the preview pane for the selected macro."""
        if current is None:
            self._selected_name = None
            self.details.clear()
            return
        self._selected_name = current.text()
        payload = current.data(32) or {}
        shortcut = str(payload.get("shortcut", "") or "") if isinstance(payload, dict) else ""
        events = payload.get("events", []) if isinstance(payload, dict) else []
        lines = [f"Name: {self._selected_name}", f"Shortcut: {shortcut or '(none)'}", "", "Steps:"]
        if isinstance(events, list):
            for index, row in enumerate(events, start=1):
                if isinstance(row, (list, tuple)) and len(row) == 2:
                    lines.append(f"{index}. {row[0]} {row[1]!r}")
        self.details.setPlainText("\n".join(lines))
