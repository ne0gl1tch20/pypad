"""Provide a reusable panel widget for current-file timeline review.

This widget is the dock-friendly counterpart to the current-file timeline
dialog. It keeps the file timeline consistent with the scope timeline panel so
the editor shell can present one coherent history experience.
"""

from __future__ import annotations

import difflib

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from pypad.ui.system.timeline_models import TimelineEntry
from pypad.ui.theme.theme_tokens import build_timeline_panel_qss, build_tokens_from_settings


class TimelinePanel(QWidget):
    """Render current-file timeline entries inside a dock-friendly panel widget."""

    restore_current_requested = Signal(str)
    restore_new_tab_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        """Build the panel chrome and accessible review layout."""

        super().__init__(parent)
        self.setObjectName("fileTimelinePanel")
        self._entries: list[TimelineEntry] = []
        self._current_text = ""
        self._primary_compare_entry: TimelineEntry | None = None
        self._file_label = "Current File Timeline"
        self.setAccessibleName("File timeline panel")
        self.setAccessibleDescription(
            "Review current-file history from local snapshots, autosave, recovery, saved file state, and Git."
        )

        root = QVBoxLayout(self)
        self.intro_label = QLabel(
            "Review current-file history, filter by source, compare any entry against the current version, and restore safely.",
            self,
        )
        self.intro_label.setWordWrap(True)
        root.addWidget(self.intro_label)

        controls = QHBoxLayout()
        self.filter_edit = QLineEdit(self)
        self.filter_edit.setPlaceholderText("Filter timeline entries...")
        self.filter_edit.setAccessibleName("Timeline filter")
        self.source_combo = QComboBox(self)
        self.source_combo.addItems(["All Sources", "Current", "Saved File", "Autosave", "Recovery", "Local History", "Git"])
        self.source_combo.setAccessibleName("Timeline source filter")
        controls.addWidget(self.filter_edit, 2)
        controls.addWidget(self.source_combo, 1)
        root.addLayout(controls)

        split = QSplitter(Qt.Horizontal, self)
        split.setChildrenCollapsible(False)
        root.addWidget(split, 1)

        left_panel = QWidget(split)
        left_layout = QVBoxLayout(left_panel)
        self.scope_label = QLabel("Current File Timeline", left_panel)
        left_layout.addWidget(self.scope_label)
        self.list_widget = QListWidget(left_panel)
        self.list_widget.setAccessibleName("Timeline entries")
        left_layout.addWidget(self.list_widget, 1)
        self.summary_label = QLabel("", left_panel)
        self.summary_label.setWordWrap(True)
        left_layout.addWidget(self.summary_label)

        right_panel = QWidget(split)
        right_layout = QVBoxLayout(right_panel)
        self.details_label = QLabel("", right_panel)
        self.details_label.setWordWrap(True)
        right_layout.addWidget(self.details_label)
        self.compare_label = QLabel("", right_panel)
        self.compare_label.setWordWrap(True)
        right_layout.addWidget(self.compare_label)
        inner_split = QSplitter(Qt.Vertical, right_panel)
        self.diff_view = QTextEdit(inner_split)
        self.diff_view.setObjectName("timelineDiffView")
        self.diff_view.setReadOnly(True)
        self.diff_view.setAccessibleName("Timeline diff preview")
        self.preview = QTextEdit(inner_split)
        self.preview.setObjectName("timelinePreviewView")
        self.preview.setReadOnly(True)
        self.preview.setAccessibleName("Timeline content preview")
        inner_split.addWidget(self.diff_view)
        inner_split.addWidget(self.preview)
        inner_split.setSizes([340, 320])
        right_layout.addWidget(inner_split, 1)

        button_row = QHBoxLayout()
        self.compare_btn = QPushButton("Mark for Compare", self)
        self.compare_current_btn = QPushButton("Use Current as Baseline", self)
        self.restore_btn = QPushButton("Restore to Current Tab", self)
        self.restore_new_tab_btn = QPushButton("Restore to New Tab", self)
        self.copy_btn = QPushButton("Copy Snapshot Text", self)
        button_row.addWidget(self.compare_btn)
        button_row.addWidget(self.compare_current_btn)
        button_row.addWidget(self.restore_btn)
        button_row.addWidget(self.restore_new_tab_btn)
        button_row.addWidget(self.copy_btn)
        button_row.addStretch(1)
        right_layout.addLayout(button_row)
        split.setSizes([360, 760])

        self.filter_edit.textChanged.connect(self._populate)
        self.source_combo.currentTextChanged.connect(self._populate)
        self.list_widget.currentRowChanged.connect(self._update_views)
        self.compare_btn.clicked.connect(self._mark_compare_entry)
        self.compare_current_btn.clicked.connect(self._clear_compare_entry)
        self.restore_btn.clicked.connect(self._emit_restore_current)
        self.restore_new_tab_btn.clicked.connect(self._emit_restore_new_tab)
        self.copy_btn.clicked.connect(self._copy_selected_text)

        self.apply_theme()
        self._populate()

    def set_timeline(self, file_label: str, *, entries: list[TimelineEntry], current_text: str) -> None:
        """Load the current file timeline and refresh the visible rows."""

        self.apply_theme()
        self._file_label = file_label or "Current File Timeline"
        self._entries = list(entries)
        self._current_text = current_text
        self._primary_compare_entry = None
        self.scope_label.setText(self._file_label)
        self._populate()

    def apply_theme(self) -> None:
        """Apply the current theme token policy from the owning window settings."""
        window = self.window()
        settings = getattr(window, "settings", {}) if window is not None else {}
        tokens = build_tokens_from_settings(settings if isinstance(settings, dict) else {})
        self.setStyleSheet(build_timeline_panel_qss(tokens, panel_object_name=self.objectName()))

    def current_entry(self) -> TimelineEntry | None:
        """Return the currently selected actionable entry."""

        item = self.list_widget.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _visible_entries(self) -> list[TimelineEntry]:
        """Return entries that match the current source and text filters."""

        query = self.filter_edit.text().strip().lower()
        source_name = self.source_combo.currentText().strip().lower()
        source_map = {
            "current": "current",
            "saved file": "saved_file",
            "autosave": "autosave",
            "recovery": "recovery",
            "local history": "local_history",
            "git": "git_commit",
        }
        required_kind = source_map.get(source_name, "")
        visible: list[TimelineEntry] = []
        for entry in self._entries:
            if required_kind and entry.source_kind != required_kind:
                continue
            haystack = " ".join([entry.label, entry.timestamp, entry.summary, entry.author]).lower()
            if query and query not in haystack:
                continue
            visible.append(entry)
        return visible

    def _populate(self) -> None:
        """Refresh the list view using the current filters."""

        visible = self._visible_entries()
        self.list_widget.clear()
        self.summary_label.setText(f"{len(visible)} timeline item(s) visible.")
        last_group = None
        for entry in visible:
            if entry.group_label and entry.group_label != last_group:
                header = QListWidgetItem(entry.group_label)
                header.setFlags(Qt.NoItemFlags)
                header.setData(Qt.UserRole, None)
                self.list_widget.addItem(header)
                last_group = entry.group_label
            badge = entry.badge_text or {
                "current": "Current",
                "saved_file": "Saved",
                "autosave": "Autosave",
                "recovery": "Recovery",
                "local_history": "Local",
                "git_commit": "Git",
            }.get(entry.source_kind, entry.source_kind.title())
            item = QListWidgetItem(f"[{badge}] {entry.timestamp or '-'} | {entry.label}")
            item.setData(Qt.UserRole, entry)
            item.setToolTip(entry.summary)
            self.list_widget.addItem(item)
        if self.list_widget.count() > 0:
            for index in range(self.list_widget.count()):
                if self.list_widget.item(index).data(Qt.UserRole) is not None:
                    self.list_widget.setCurrentRow(index)
                    break
        else:
            self.preview.clear()
            self.diff_view.clear()
            self.details_label.setText("No timeline entries matched the current filters.")
            self.compare_label.setText("Mark a timeline item for compare to review two snapshots side by side in the diff view.")
            self.compare_btn.setEnabled(False)
            self.compare_current_btn.setEnabled(False)
            self.restore_btn.setEnabled(False)
            self.restore_new_tab_btn.setEnabled(False)
            self.copy_btn.setEnabled(False)

    def _update_views(self, row: int) -> None:
        """Show metadata, preview, and diff for the selected entry."""

        item = self.list_widget.item(row) if row >= 0 else None
        entry = item.data(Qt.UserRole) if item is not None else None
        if entry is None:
            self.preview.clear()
            self.diff_view.clear()
            self.details_label.clear()
            self.compare_label.setText("Mark a timeline item for compare to review two snapshots in the diff preview.")
            self.compare_btn.setEnabled(False)
            self.compare_current_btn.setEnabled(False)
            self.restore_btn.setEnabled(False)
            self.restore_new_tab_btn.setEnabled(False)
            self.copy_btn.setEnabled(False)
            return
        self.details_label.setText(
            f"Source: {entry.source_kind.replace('_', ' ').title()} | "
            f"When: {entry.timestamp or '-'} | "
            f"Summary: {entry.summary}"
            + (f" | Author: {entry.author}" if entry.author else "")
        )
        self.preview.setPlainText(entry.text)
        self.compare_btn.setEnabled(True)
        self.compare_current_btn.setEnabled(True)
        compare_base = self._primary_compare_entry
        compare_name = "Current"
        compare_text = self._current_text
        if compare_base is not None and compare_base.entry_id != entry.entry_id:
            compare_name = compare_base.label
            compare_text = compare_base.text
            self.compare_label.setText(
                f"Comparing selected entry against marked entry: {compare_base.label} ({compare_base.timestamp or 'undated'})."
            )
        else:
            self.compare_label.setText("Comparing selected entry against the current in-editor version.")
        diff_lines = difflib.unified_diff(
            compare_text.splitlines(),
            entry.text.splitlines(),
            fromfile=compare_name,
            tofile=entry.label,
            lineterm="",
        )
        self.diff_view.setPlainText("\n".join(diff_lines) or "(No visible diff)")
        can_restore = entry.source_kind != "current"
        self.restore_btn.setEnabled(can_restore)
        self.restore_new_tab_btn.setEnabled(can_restore)
        self.copy_btn.setEnabled(True)

    def _emit_restore_current(self) -> None:
        """Request restoring the selected entry into the current tab."""

        entry = self.current_entry()
        if entry is None or entry.source_kind == "current":
            return
        self.restore_current_requested.emit(entry.text)

    def _emit_restore_new_tab(self) -> None:
        """Request restoring the selected entry into a new tab."""

        entry = self.current_entry()
        if entry is None or entry.source_kind == "current":
            return
        self.restore_new_tab_requested.emit(entry.text)

    def _copy_selected_text(self) -> None:
        """Copy the currently previewed snapshot text to the clipboard."""

        entry = self.current_entry()
        if entry is None:
            return
        QApplication.clipboard().setText(entry.text)

    def _mark_compare_entry(self) -> None:
        """Remember the selected entry as the manual compare baseline."""

        entry = self.current_entry()
        if entry is None:
            return
        self._primary_compare_entry = entry
        self._update_views(self.list_widget.currentRow())

    def _clear_compare_entry(self) -> None:
        """Reset diff preview back to comparing against the current editor text."""

        self._primary_compare_entry = None
        self._update_views(self.list_widget.currentRow())
