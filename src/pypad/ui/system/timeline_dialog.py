"""Provide a compatibility dialog wrapper for the reusable file timeline panel."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QVBoxLayout

from pypad.ui.system.timeline_models import TimelineEntry
from pypad.ui.system.timeline_panel import TimelinePanel


class TimelineDialog(QDialog):
    """Wrap the file timeline panel in a dialog for compatibility paths."""

    def __init__(self, parent, *, entries: list[TimelineEntry], current_text: str, file_label: str = "Timeline") -> None:
        """Build the dialog from normalized entries."""

        super().__init__(parent)
        self._selected_text: str | None = None
        self.setWindowTitle(file_label)
        self.resize(1160, 720)
        self.setAccessibleName("Timeline dialog")
        self.setAccessibleDescription(
            "Review current-file history from local snapshots, saved file state, and Git history when available."
        )

        root = QVBoxLayout(self)
        self.panel = TimelinePanel(self)
        self.panel.set_timeline(file_label, entries=entries, current_text=current_text)
        self.panel.restore_current_requested.connect(self._capture_restore_current)
        self.panel.restore_new_tab_requested.connect(self._capture_restore_new_tab)
        root.addWidget(self.panel, 1)

        buttons = QHBoxLayout()
        self.close_btn = QPushButton("Close", self)
        buttons.addStretch(1)
        buttons.addWidget(self.close_btn)
        root.addLayout(buttons)
        self.close_btn.clicked.connect(self.reject)

    @property
    def selected_text(self) -> str | None:
        """Return the text selected for restore operations."""

        return self._selected_text

    def _capture_restore_current(self, text: str) -> None:
        """Accept the dialog for in-place restore."""

        self._selected_text = text
        self.accept()

    def _capture_restore_new_tab(self, text: str) -> None:
        """Accept the dialog and request restore into a new tab."""

        self._selected_text = text
        self.setProperty("restore_to_new_tab", True)
        self.accept()
