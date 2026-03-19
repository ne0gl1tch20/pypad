"""Shared dialog helpers for built-in offline tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ToolDialogBase(QDialog):
    """Provide consistent insert/copy/save/help behavior for built-in tools."""

    def __init__(
        self,
        parent,
        *,
        tool_id: str,
        title: str,
        help_text: str,
        output_label: str = "Output",
    ) -> None:
        super().__init__(parent)
        self.window = parent
        self.tool_id = tool_id
        self.help_text = help_text
        self.setWindowTitle(title)
        self.resize(620, 420)
        self.setAccessibleName(f"{title} dialog")
        self.setAccessibleDescription(help_text)

        self.content_layout = QVBoxLayout()
        self.output = QPlainTextEdit(self)
        self.output.setAccessibleName(f"{title} output")
        self.output.setPlaceholderText(output_label)
        self.output.setMinimumHeight(96)

        root = QVBoxLayout(self)
        chrome = QHBoxLayout()
        chrome.addStretch(1)
        self.help_btn = QPushButton("?", self)
        self.help_btn.setFixedWidth(32)
        self.help_btn.setAccessibleName(f"{title} help")
        self.help_btn.setToolTip("How to use this tool")
        self.help_btn.clicked.connect(self.show_help)
        chrome.addWidget(self.help_btn)
        root.addLayout(chrome)
        root.addLayout(self.content_layout, 1)
        root.addWidget(self.output, 1)

        buttons = QHBoxLayout()
        self.insert_btn = QPushButton("Insert", self)
        self.copy_btn = QPushButton("Copy", self)
        self.save_btn = QPushButton("Save...", self)
        self.close_btn = QPushButton("Close", self)
        self.insert_btn.clicked.connect(self.insert_output)
        self.copy_btn.clicked.connect(self.copy_output)
        self.save_btn.clicked.connect(self.save_output)
        self.close_btn.clicked.connect(self.accept)
        buttons.addWidget(self.insert_btn)
        buttons.addWidget(self.copy_btn)
        buttons.addWidget(self.save_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.close_btn)
        root.addLayout(buttons)

    def state(self) -> dict[str, Any]:
        return {}

    def restore_state(self, state: dict[str, Any]) -> None:
        return

    def load_persisted_state(self) -> None:
        settings = getattr(self.window, "settings", {}) or {}
        raw_state = settings.get("tool_state", {})
        if isinstance(raw_state, dict):
            raw = raw_state.get(self.tool_id, {})
            if isinstance(raw, dict):
                self.restore_state(raw)

    def persist_state(self) -> None:
        settings = getattr(self.window, "settings", None)
        if not isinstance(settings, dict):
            return
        tool_state = settings.get("tool_state", {})
        if not isinstance(tool_state, dict):
            tool_state = {}
        updated = dict(tool_state)
        updated[self.tool_id] = self.state()
        settings["tool_state"] = updated
        saver = getattr(self.window, "save_settings_to_disk", None)
        if callable(saver):
            saver()

    def show_help(self) -> None:
        help_seen = getattr(self.window, "settings", {}).get("tool_help_dismissed", {})
        if not isinstance(help_seen, dict):
            help_seen = {}
        if isinstance(getattr(self.window, "settings", None), dict):
            self.window.settings["tool_help_dismissed"] = dict(help_seen, **{self.tool_id: True})
        QMessageBox.information(self, self.windowTitle(), self.help_text)

    def current_output(self) -> str:
        return self.output.toPlainText().strip()

    def insert_output(self) -> None:
        text = self.current_output()
        if not text:
            QMessageBox.information(self, self.windowTitle(), "Generate or choose output first.")
            return
        tab = self.window.active_tab() if hasattr(self.window, "active_tab") else None
        if tab is None:
            QMessageBox.information(self, self.windowTitle(), "Open a tab first.")
            return
        tab.text_edit.insert_text(text)
        if hasattr(self.window, "show_status_message"):
            self.window.show_status_message(f"Inserted from {self.windowTitle()}.", 2500)

    def copy_output(self) -> None:
        text = self.current_output()
        if not text:
            QMessageBox.information(self, self.windowTitle(), "Generate or choose output first.")
            return
        QApplication.clipboard().setText(text)
        if hasattr(self.window, "show_status_message"):
            self.window.show_status_message(f"Copied from {self.windowTitle()}.", 2500)

    def save_output(self) -> None:
        text = self.current_output()
        if not text:
            QMessageBox.information(self, self.windowTitle(), "Generate or choose output first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            f"Save {self.windowTitle()} Output",
            str(Path.cwd() / f"{self.tool_id}.txt"),
            "Text Files (*.txt);;All Files (*)",
        )
        if not path:
            return
        Path(path).write_text(text, encoding="utf-8")
        if hasattr(self.window, "show_status_message"):
            self.window.show_status_message(f"Saved {self.windowTitle()} output: {path}", 3000)

    def add_section(self, widget: QWidget) -> None:
        self.content_layout.addWidget(widget)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.persist_state()
        super().closeEvent(event)
