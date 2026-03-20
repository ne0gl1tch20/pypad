"""Render a review-oriented folder and workspace timeline dialog."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QVBoxLayout

from pypad.ui.system.workspace_timeline_models import WorkspaceTimelineEntry
from pypad.ui.system.workspace_timeline_panel import WorkspaceTimelinePanel


class WorkspaceTimelineDialog(QDialog):
    """Browse folder or workspace activity and jump into file-level history safely."""

    def __init__(self, parent, *, scope_label: str, entries: list[WorkspaceTimelineEntry]) -> None:
        """Build the dialog from normalized scope-level timeline entries."""

        super().__init__(parent)
        self.selected_path: str = ""
        self.selected_open_file_timeline = False
        self.setWindowTitle(scope_label)
        self.resize(1120, 700)
        self.setAccessibleName("Workspace timeline dialog")
        self.setAccessibleDescription(
            "Review folder or workspace activity from filesystem, autosave, recovery, and Git sources."
        )

        root = QVBoxLayout(self)
        self.panel = WorkspaceTimelinePanel(self)
        self.panel.set_scope_entries(scope_label, entries)
        self.panel.open_requested.connect(self._capture_open)
        self.panel.file_timeline_requested.connect(self._capture_file_timeline)
        root.addWidget(self.panel, 1)

        buttons = QHBoxLayout()
        self.close_btn = QPushButton("Close", self)
        buttons.addStretch(1)
        buttons.addWidget(self.close_btn)
        root.addLayout(buttons)
        self.close_btn.clicked.connect(self.reject)

    def _capture_open(self, path: str) -> None:
        """Accept the dialog and request opening the selected file."""

        self.selected_path = path
        self.selected_open_file_timeline = False
        self.accept()

    def _capture_file_timeline(self, path: str) -> None:
        """Accept the dialog and request opening the selected file timeline."""

        self.selected_path = path
        self.selected_open_file_timeline = True
        self.accept()
