"""Color picker tool dialog."""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog, QFormLayout, QFrame, QGroupBox, QLabel, QPushButton

from .base_dialog import ToolDialogBase


def color_to_hsl_string(color: QColor) -> str:
    """Render a QColor as an hsl(...) string."""
    h, s, l, _ = color.getHsl()
    return f"hsl({max(0, h)}, {max(0, round((s / 255.0) * 100))}%, {max(0, round((l / 255.0) * 100))}%)"


class ColorPickerToolDialog(ToolDialogBase):
    """Choose a color and copy/insert its values."""

    def __init__(self, parent) -> None:
        super().__init__(
            parent,
            tool_id="color_picker",
            title="Color Picker",
            help_text="Choose a local color, then copy or insert its hex, RGB, or HSL representation.",
        )
        self._color = QColor("#4a90e2")
        group = QGroupBox("Color", self)
        form = QFormLayout(group)
        self.pick_btn = QPushButton("Choose Color...", group)
        self.pick_btn.clicked.connect(self.pick_color)
        self.hex_label = QLabel("", group)
        self.rgb_label = QLabel("", group)
        self.hsl_label = QLabel("", group)
        self.swatch = QFrame(group)
        self.swatch.setFrameShape(QFrame.Shape.StyledPanel)
        self.swatch.setMinimumHeight(32)
        form.addRow("Selected:", self.pick_btn)
        form.addRow("Hex:", self.hex_label)
        form.addRow("RGB:", self.rgb_label)
        form.addRow("HSL:", self.hsl_label)
        form.addRow("Preview:", self.swatch)
        self.add_section(group)
        self.load_persisted_state()
        self._refresh()

    def pick_color(self) -> None:
        color = QColorDialog.getColor(self._color, self, "Choose Color")
        if color.isValid():
            self._color = color
            self._refresh()

    def _refresh(self) -> None:
        rgb = self._color.getRgb()
        self.hex_label.setText(self._color.name().upper())
        self.rgb_label.setText(f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})")
        self.hsl_label.setText(color_to_hsl_string(self._color))
        self.swatch.setStyleSheet(f"background: {self._color.name()}; border: 1px solid palette(mid);")
        self.output.setPlainText(f"{self.hex_label.text()}\n{self.rgb_label.text()}\n{self.hsl_label.text()}")

    def state(self) -> dict[str, Any]:
        return {"color": self._color.name()}

    def restore_state(self, state: dict[str, Any]) -> None:
        color = QColor(str(state.get("color", "#4a90e2")))
        if color.isValid():
            self._color = color
