"""Provide a compact, accessible banner widget for inline editor notices.

This widget is used for high-signal editor states such as large-file mode where
the user needs a clear explanation and a few obvious actions without losing the
main editing context.
"""

from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class BannerWidget(QWidget):
    """Render a title, message, and action row for inline status workflows."""

    def __init__(self, parent=None) -> None:
        """Build the shared banner shell and default it to a hidden idle state."""
        super().__init__(parent)
        self.setObjectName("pypadBannerWidget")
        self.setAccessibleName("Inline message banner")
        self.setAccessibleDescription(
            "Shows important editor state information together with actions that can resolve or inspect the state."
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        self.title_label = QLabel(self)
        self.title_label.setObjectName("pypadBannerTitle")
        self.title_label.setWordWrap(True)
        self.title_label.setTextFormat(Qt.TextFormat.PlainText)
        self.title_label.setAccessibleName("Banner title")
        root.addWidget(self.title_label)

        self.message_label = QLabel(self)
        self.message_label.setObjectName("pypadBannerMessage")
        self.message_label.setWordWrap(True)
        self.message_label.setTextFormat(Qt.TextFormat.PlainText)
        self.message_label.setAccessibleName("Banner message")
        root.addWidget(self.message_label)

        self.actions_row = QHBoxLayout()
        self.actions_row.setContentsMargins(0, 0, 0, 0)
        self.actions_row.setSpacing(8)
        root.addLayout(self.actions_row)
        self.actions_row.addStretch(1)
        self.hide()

    def set_content(self, *, title: str, message: str) -> None:
        """Update the banner text while keeping the action row intact."""
        self.title_label.setText(str(title or "").strip())
        self.message_label.setText(str(message or "").strip())

    def set_actions(self, actions: Iterable[QPushButton]) -> None:
        """Replace the current banner buttons with the supplied action widgets."""
        while self.actions_row.count():
            item = self.actions_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        for button in actions:
            self.actions_row.addWidget(button)
        self.actions_row.addStretch(1)
