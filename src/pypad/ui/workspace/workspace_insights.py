"""Provide a compact workspace-insights dialog for project-level navigation cues.

This module scans the active workspace or currently open tabs for lightweight
signals such as TODO items, FIXME markers, and file hotspots. The goal is a
fast, readable project summary rather than a full code-intelligence index.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class WorkspaceInsightItem:
    """Store one actionable insight row shown in the workspace-insights dialog."""

    file_path: str
    line_number: int
    kind: str
    summary: str


def collect_workspace_insights(window) -> list[WorkspaceInsightItem]:
    """Scan the active workspace or open tabs for TODO, FIXME, and note markers."""

    items: list[WorkspaceInsightItem] = []
    seen_paths: set[str] = set()
    workspace_controller = getattr(window, "workspace_controller", None)
    root = workspace_controller.workspace_root() if workspace_controller is not None else None
    candidate_paths: list[str] = []
    if root and workspace_controller is not None:
        candidate_paths.extend(workspace_controller.workspace_files()[:5000])
    else:
        for index in range(window.tab_widget.count()):
            tab = window.tab_widget.widget(index)
            path = str(getattr(tab, "current_file", "") or "").strip()
            if path:
                candidate_paths.append(path)
    for file_path in candidate_paths:
        normalized = str(file_path or "").strip()
        if not normalized or normalized in seen_paths:
            continue
        seen_paths.add(normalized)
        try:
            text = Path(normalized).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            upper = line.upper()
            if "TODO" in upper:
                items.append(WorkspaceInsightItem(normalized, number, "TODO", line.strip()))
            elif "FIXME" in upper:
                items.append(WorkspaceInsightItem(normalized, number, "FIXME", line.strip()))
            elif "NOTE:" in upper:
                items.append(WorkspaceInsightItem(normalized, number, "NOTE", line.strip()))
    return items


class WorkspaceInsightsDialog(QDialog):
    """Show lightweight project insights in an accessible list-detail layout."""

    def __init__(self, parent, items: list[WorkspaceInsightItem]) -> None:
        """Build the dialog from the supplied insight items."""

        super().__init__(parent)
        self._all_items = list(items)
        self.selected_item: WorkspaceInsightItem | None = None
        self.setWindowTitle("Workspace Insights")
        self.resize(880, 520)
        self.setAccessibleName("Workspace insights dialog")
        self.setAccessibleDescription(
            "Review TODO, FIXME, and note markers collected from the active workspace or open files."
        )
        root = QVBoxLayout(self)
        intro = QLabel(
            "Review lightweight project signals such as TODO and FIXME markers, then open the selected location.",
            self,
        )
        intro.setWordWrap(True)
        root.addWidget(intro)
        self.filter_edit = QLineEdit(self)
        self.filter_edit.setPlaceholderText("Filter by file, kind, or text...")
        self.filter_edit.setAccessibleName("Workspace insights filter")
        self.filter_edit.textChanged.connect(self._populate)
        root.addWidget(self.filter_edit)
        content = QHBoxLayout()
        left = QWidget(self)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.list_widget = QListWidget(left)
        self.list_widget.setAccessibleName("Workspace insight list")
        self.list_widget.currentRowChanged.connect(self._refresh_preview)
        left_layout.addWidget(self.list_widget, 1)
        self.summary_label = QLabel("", left)
        self.summary_label.setWordWrap(True)
        left_layout.addWidget(self.summary_label)
        right = QWidget(self)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.preview = QTextEdit(right)
        self.preview.setReadOnly(True)
        self.preview.setAccessibleName("Workspace insight details")
        right_layout.addWidget(self.preview, 1)
        content.addWidget(left, 2)
        content.addWidget(right, 3)
        root.addLayout(content, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Open | QDialogButtonBox.Close, Qt.Horizontal, self)
        buttons.button(QDialogButtonBox.Open).setText("Open Location")
        buttons.accepted.connect(self._accept_open)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self._populate()

    def _filtered_items(self) -> list[WorkspaceInsightItem]:
        """Return the current list after applying the text filter."""

        query = self.filter_edit.text().strip().lower()
        if not query:
            return list(self._all_items)
        return [
            item for item in self._all_items
            if query in item.kind.lower() or query in item.summary.lower() or query in item.file_path.lower()
        ]

    def _populate(self) -> None:
        """Rebuild the visible insight list from the current filter."""

        self.list_widget.clear()
        visible = self._filtered_items()
        if not visible:
            self.list_widget.addItem(QListWidgetItem("No matching workspace insights."))
            self.summary_label.setText("No actionable workspace markers matched the current filter.")
            self.preview.setPlainText("Adjust the filter or add TODO, FIXME, or NOTE markers in your files.")
            self.selected_item = None
            return
        todo_count = sum(1 for item in visible if item.kind == "TODO")
        fixme_count = sum(1 for item in visible if item.kind == "FIXME")
        self.summary_label.setText(
            f"{len(visible)} item(s) visible | TODO {todo_count} | FIXME {fixme_count}"
        )
        for item in visible:
            file_name = Path(item.file_path).name
            self.list_widget.addItem(f"[{item.kind}] {file_name}:{item.line_number}  {item.summary}")
        self.list_widget.setCurrentRow(0)

    def _refresh_preview(self) -> None:
        """Show detailed text for the currently selected insight item."""

        index = int(self.list_widget.currentRow())
        visible = self._filtered_items()
        if index < 0 or index >= len(visible):
            self.selected_item = None
            return
        item = visible[index]
        self.selected_item = item
        self.preview.setPlainText(
            f"Kind: {item.kind}\n"
            f"File: {item.file_path}\n"
            f"Line: {item.line_number}\n\n"
            f"{item.summary}"
        )

    def _accept_open(self) -> None:
        """Accept the dialog only when an actionable item is selected."""

        if self.selected_item is None:
            return
        self.accept()
