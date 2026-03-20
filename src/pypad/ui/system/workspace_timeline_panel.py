"""Provide a reusable list-detail widget for folder and workspace timeline review.

This widget is designed for dock embedding so the timeline can live in the main
window shell like other serious editor panels, while still supporting keyboard-
first review and file-level follow-up actions.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from pypad.ui.system.workspace_timeline_models import WorkspaceTimelineEntry
from pypad.ui.theme.theme_tokens import build_timeline_panel_qss, build_tokens_from_settings


class WorkspaceTimelinePanel(QWidget):
    """Render scope timeline entries inside a dock-friendly panel widget."""

    open_requested = Signal(str)
    file_timeline_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        """Build the panel chrome and accessible list-detail layout."""

        super().__init__(parent)
        self.setObjectName("workspaceTimelinePanel")
        self._all_entries: list[WorkspaceTimelineEntry] = []
        self._scope_label = "Timeline"
        self.setAccessibleName("Workspace timeline panel")
        self.setAccessibleDescription(
            "Review folder or workspace activity from filesystem, autosave, recovery, and Git sources."
        )

        root = QVBoxLayout(self)
        self.intro_label = QLabel(
            "Review recent activity in this scope, filter entries, inspect details, and open the selected file or file timeline.",
            self,
        )
        self.intro_label.setWordWrap(True)
        root.addWidget(self.intro_label)

        controls = QHBoxLayout()
        self.filter_edit = QLineEdit(self)
        self.filter_edit.setPlaceholderText("Filter by file, source, summary, or commit text...")
        self.filter_edit.setAccessibleName("Workspace timeline filter")
        self.source_filter = QLineEdit(self)
        self.source_filter.setPlaceholderText("Optional source filter, for example git or autosave")
        self.source_filter.setAccessibleName("Workspace timeline source filter")
        controls.addWidget(self.filter_edit, 2)
        controls.addWidget(self.source_filter, 1)
        root.addLayout(controls)

        content = QHBoxLayout()
        left = QWidget(self)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.scope_label = QLabel("Timeline", left)
        left_layout.addWidget(self.scope_label)
        self.list_widget = QListWidget(left)
        self.list_widget.setAccessibleName("Workspace timeline entries")
        left_layout.addWidget(self.list_widget, 1)
        self.summary_label = QLabel("", left)
        self.summary_label.setWordWrap(True)
        left_layout.addWidget(self.summary_label)

        right = QWidget(self)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.details_label = QLabel("", right)
        self.details_label.setWordWrap(True)
        right_layout.addWidget(self.details_label)
        self.preview = QTextEdit(right)
        self.preview.setObjectName("workspaceTimelinePreviewView")
        self.preview.setReadOnly(True)
        self.preview.setAccessibleName("Workspace timeline details")
        right_layout.addWidget(self.preview, 1)
        content.addWidget(left, 2)
        content.addWidget(right, 3)
        root.addLayout(content, 1)

        buttons = QHBoxLayout()
        self.open_btn = QPushButton("Open Location", self)
        self.file_timeline_btn = QPushButton("Open File Timeline", self)
        self.copy_btn = QPushButton("Copy Summary", self)
        buttons.addWidget(self.open_btn)
        buttons.addWidget(self.file_timeline_btn)
        buttons.addWidget(self.copy_btn)
        buttons.addStretch(1)
        root.addLayout(buttons)

        self.filter_edit.textChanged.connect(self._populate)
        self.source_filter.textChanged.connect(self._populate)
        self.list_widget.currentRowChanged.connect(self._refresh_details)
        self.open_btn.clicked.connect(self._emit_open_requested)
        self.file_timeline_btn.clicked.connect(self._emit_file_timeline_requested)
        self.copy_btn.clicked.connect(self._copy_summary)

        self.apply_theme()
        self._populate()

    def set_scope_entries(self, scope_label: str, entries: list[WorkspaceTimelineEntry]) -> None:
        """Load a new scope into the panel and refresh the visible rows."""

        self.apply_theme()
        self._scope_label = scope_label
        self._all_entries = list(entries)
        self.scope_label.setText(scope_label)
        self._populate()

    def apply_theme(self) -> None:
        """Apply the current theme token policy from the owning window settings."""
        window = self.window()
        settings = getattr(window, "settings", {}) if window is not None else {}
        tokens = build_tokens_from_settings(settings if isinstance(settings, dict) else {})
        self.setStyleSheet(build_timeline_panel_qss(tokens, panel_object_name=self.objectName()))

    def current_entry(self) -> WorkspaceTimelineEntry | None:
        """Return the currently selected actionable entry."""

        item = self.list_widget.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _filtered_entries(self) -> list[WorkspaceTimelineEntry]:
        """Return visible entries after applying the current filters."""

        query = self.filter_edit.text().strip().lower()
        source_query = self.source_filter.text().strip().lower()
        rows: list[WorkspaceTimelineEntry] = []
        for entry in self._all_entries:
            if source_query and source_query not in entry.source_kind.lower() and source_query not in entry.badge_text.lower():
                continue
            haystack = " ".join(
                [
                    entry.title,
                    entry.timestamp,
                    entry.summary,
                    entry.file_path,
                    entry.preview_text[:400],
                    entry.author,
                ]
            ).lower()
            if query and query not in haystack:
                continue
            rows.append(entry)
        return rows

    def _populate(self) -> None:
        """Rebuild the timeline list using the current filters."""

        self.list_widget.clear()
        visible = self._filtered_entries()
        self.summary_label.setText(f"{len(visible)} timeline item(s) visible in {self._scope_label}.")
        last_group = None
        for entry in visible:
            if entry.group_label and entry.group_label != last_group:
                header = QListWidgetItem(entry.group_label)
                header.setFlags(Qt.NoItemFlags)
                header.setData(Qt.UserRole, None)
                self.list_widget.addItem(header)
                last_group = entry.group_label
            label = f"[{entry.badge_text or entry.source_kind.title()}] {entry.timestamp or '-'} | {entry.title}"
            item = QListWidgetItem(label)
            item.setToolTip(entry.summary)
            item.setData(Qt.UserRole, entry)
            self.list_widget.addItem(item)
        if self.list_widget.count() > 0:
            for index in range(self.list_widget.count()):
                if self.list_widget.item(index).data(Qt.UserRole) is not None:
                    self.list_widget.setCurrentRow(index)
                    break
        else:
            self.details_label.setText("No scope timeline entries matched the current filters.")
            self.preview.setPlainText("Try a broader filter or choose a scope with recent file activity.")
            self.open_btn.setEnabled(False)
            self.file_timeline_btn.setEnabled(False)
            self.copy_btn.setEnabled(False)

    def _refresh_details(self, row: int) -> None:
        """Refresh metadata and preview text for the selected timeline row."""

        entry = self.current_entry()
        if row < 0 or entry is None:
            self.details_label.setText("")
            self.preview.clear()
            self.open_btn.setEnabled(False)
            self.file_timeline_btn.setEnabled(False)
            self.copy_btn.setEnabled(False)
            return
        relative = entry.metadata.get("relative_path", "")
        self.details_label.setText(
            f"Source: {entry.source_kind.replace('_', ' ').title()} | "
            f"When: {entry.timestamp or '-'} | "
            f"Summary: {entry.summary}"
            + (f" | Path: {relative or entry.file_path}" if entry.file_path else "")
            + (f" | Author: {entry.author}" if entry.author else "")
        )
        self.preview.setPlainText(entry.preview_text)
        is_file = bool(entry.file_path and Path(entry.file_path).is_file())
        self.open_btn.setEnabled(is_file)
        self.file_timeline_btn.setEnabled(is_file)
        self.copy_btn.setEnabled(True)

    def _emit_open_requested(self) -> None:
        """Emit an open-location request for the current entry."""

        entry = self.current_entry()
        if entry is None or not entry.file_path:
            return
        self.open_requested.emit(entry.file_path)

    def _emit_file_timeline_requested(self) -> None:
        """Emit a file-timeline request for the current entry."""

        entry = self.current_entry()
        if entry is None or not entry.file_path:
            return
        self.file_timeline_requested.emit(entry.file_path)

    def _copy_summary(self) -> None:
        """Copy a concise summary of the selected entry to the clipboard."""

        entry = self.current_entry()
        if entry is None:
            return
        QApplication.clipboard().setText(
            f"{entry.title}\n{entry.timestamp}\n{entry.summary}\n{entry.file_path}".strip()
        )
