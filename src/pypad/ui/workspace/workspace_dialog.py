"""Implement dialogs used to browse, configure, or manage workspaces and project views.

This module belongs to the workspace browsing and project workflow UI layer. It helps explain how `pypad.ui.workspace` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
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
from pypad.ui.theme.theme_tokens import build_dialog_theme_qss_from_tokens, build_tokens_from_settings, build_workspace_dialog_qss


class WorkspaceFilesDialog(QDialog):
    """Dialog that lists indexed workspace files and lets the user open one."""
    def __init__(self, parent, workspace_root: str, files: list[str]) -> None:
        """Build the workspace file picker dialog from the current file list."""
        super().__init__(parent)
        self.setWindowTitle(f"Workspace Files - {workspace_root}")
        self.resize(760, 460)
        self._selected_path: str | None = None
        self.setAccessibleName("Workspace files dialog")
        self.setAccessibleDescription("Browse indexed workspace files and open the selected file.")

        layout = QVBoxLayout(self)
        header = QLabel("Files", self)
        header.setAccessibleName("Workspace files heading")
        layout.addWidget(header)

        self.list_widget = QListWidget(self)
        self.list_widget.setAccessibleName("Workspace files list")
        self.list_widget.setAccessibleDescription("Lists the files available in the current workspace.")
        for path in files:
            item = QListWidgetItem(path, self.list_widget)
            item.setData(Qt.UserRole, path)
        layout.addWidget(self.list_widget)

        button_row = QHBoxLayout()
        self.open_btn = QPushButton("Open Selected", self)
        self.close_btn = QPushButton("Close", self)
        self.open_btn.setAccessibleName("Open selected workspace file")
        self.close_btn.setAccessibleName("Close workspace files dialog")
        button_row.addWidget(self.open_btn)
        button_row.addWidget(self.close_btn)
        layout.addLayout(button_row)
        self.setTabOrder(self.list_widget, self.open_btn)
        self.setTabOrder(self.open_btn, self.close_btn)

        self.open_btn.clicked.connect(self._open_selected)
        self.close_btn.clicked.connect(self.reject)
        self._apply_theme_from_parent()

    def _apply_theme_from_parent(self) -> None:
        """Apply workspace dialog styling derived from the parent window's theme settings."""
        settings = getattr(self.parent(), "settings", {}) if self.parent() is not None else {}
        tokens = build_tokens_from_settings(settings if isinstance(settings, dict) else {})
        self.setStyleSheet(build_dialog_theme_qss_from_tokens(tokens) + "\n" + build_workspace_dialog_qss(tokens))

    def _open_selected(self) -> None:
        """Accept the dialog using the currently selected file path."""
        item = self.list_widget.currentItem()
        if item is None:
            return
        self._selected_path = item.data(Qt.UserRole)
        self.accept()

    @property
    def selected_path(self) -> str | None:
        """Return the file path chosen when the dialog was accepted."""
        return self._selected_path


@dataclass
class WorkspaceSearchResult:
    """Single workspace search hit containing file, line number, and preview text."""
    path: str
    line_no: int
    line_text: str


class WorkspaceSearchDialog(QDialog):
    """Dialog that presents workspace search results with a preview and open action."""
    def __init__(self, parent, query: str, results: list[WorkspaceSearchResult]) -> None:
        """Build the workspace search results dialog for one completed query."""
        super().__init__(parent)
        self.setWindowTitle(f'Workspace Search - "{query}"')
        self.resize(900, 520)
        self._selected_path: str | None = None
        self._selected_line: int = 1
        self.setAccessibleName("Workspace search results dialog")
        self.setAccessibleDescription("Review workspace search matches, preview a result, and open the selected file.")

        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        matches_label = QLabel("Matches", self)
        matches_label.setAccessibleName("Matches heading")
        left.addWidget(matches_label)
        self.list_widget = QListWidget(self)
        self.list_widget.setAccessibleName("Workspace search results list")
        self.list_widget.setAccessibleDescription("Lists search results for the current workspace query.")
        left.addWidget(self.list_widget)
        layout.addLayout(left, 2)

        right = QVBoxLayout()
        preview_label = QLabel("Preview", self)
        preview_label.setAccessibleName("Preview heading")
        right.addWidget(preview_label)
        self.preview = QTextEdit(self)
        self.preview.setReadOnly(True)
        self.preview.setAccessibleName("Workspace search preview")
        self.preview.setAccessibleDescription("Shows the text preview for the currently selected search result.")
        right.addWidget(self.preview)
        button_row = QHBoxLayout()
        self.open_btn = QPushButton("Open File", self)
        self.close_btn = QPushButton("Close", self)
        self.open_btn.setAccessibleName("Open selected search result")
        self.close_btn.setAccessibleName("Close workspace search dialog")
        button_row.addWidget(self.open_btn)
        button_row.addWidget(self.close_btn)
        right.addLayout(button_row)
        layout.addLayout(right, 3)
        self.setTabOrder(self.list_widget, self.preview)
        self.setTabOrder(self.preview, self.open_btn)
        self.setTabOrder(self.open_btn, self.close_btn)

        for result in results:
            label = f"{result.path}:{result.line_no} - {result.line_text.strip()}"
            item = QListWidgetItem(label, self.list_widget)
            item.setData(Qt.UserRole, result.path)
            item.setData(Qt.UserRole + 1, result.line_text)
            item.setData(Qt.UserRole + 2, int(result.line_no))

        self.list_widget.currentItemChanged.connect(self._update_preview)
        self.open_btn.clicked.connect(self._open_selected)
        self.close_btn.clicked.connect(self.reject)
        self._apply_theme_from_parent()

    def _apply_theme_from_parent(self) -> None:
        """Apply workspace dialog styling derived from the parent window's theme settings."""
        settings = getattr(self.parent(), "settings", {}) if self.parent() is not None else {}
        tokens = build_tokens_from_settings(settings if isinstance(settings, dict) else {})
        self.setStyleSheet(build_dialog_theme_qss_from_tokens(tokens) + "\n" + build_workspace_dialog_qss(tokens))

    def _update_preview(self, current: QListWidgetItem | None, _prev: QListWidgetItem | None) -> None:
        """Refresh the preview pane for the currently selected search result."""
        if current is None:
            self.preview.clear()
            return
        self.preview.setPlainText(current.data(Qt.UserRole + 1) or "")

    def _open_selected(self) -> None:
        """Accept the dialog using the currently selected search result."""
        item = self.list_widget.currentItem()
        if item is None:
            return
        self._selected_path = item.data(Qt.UserRole)
        self._selected_line = int(item.data(Qt.UserRole + 2) or 1)
        self.accept()

    @property
    def selected_path(self) -> str | None:
        """Return the file path chosen when the dialog was accepted."""
        return self._selected_path

    @property
    def selected_line(self) -> int:
        """Return the 1-based line number chosen when the dialog was accepted."""
        return max(1, int(self._selected_line))

