"""Reusable host widgets for non-document tool tabs."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


@dataclass(slots=True)
class ToolTabDescriptor:
    """Describe how a non-document tool surface should behave in an editor tab."""

    tool_id: str
    title: str
    icon_name: str
    closable: bool = True
    singleton: bool = True
    preferred_tab_reuse_key: str = ""


class ToolTabHost(QWidget):
    """Wrap a tool widget with lightweight shared tab chrome."""

    def __init__(self, descriptor: ToolTabDescriptor, content: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.descriptor = descriptor
        self.content = content

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel(descriptor.title, self)
        title.setObjectName("toolTabHostTitle")
        title.setVisible(False)
        layout.addWidget(title)
        layout.addWidget(content, 1)
