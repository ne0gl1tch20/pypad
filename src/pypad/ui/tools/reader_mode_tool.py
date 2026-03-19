"""Reader mode dialog that builds on the existing focus mode."""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QCheckBox, QFormLayout, QGroupBox, QSpinBox

from .base_dialog import ToolDialogBase


class ReaderModeToolDialog(ToolDialogBase):
    """Apply a calmer reading presentation to the active editor."""

    def __init__(self, parent) -> None:
        super().__init__(
            parent,
            tool_id="reader_mode",
            title="Clean Reader Mode",
            help_text=(
                "Build a quieter reading view for the current note. This reuses PyPad's focus mode, "
                "can enlarge text, and can switch the editor to read-only until you restore it."
            ),
            output_label="Reader mode summary",
        )
        self.insert_btn.setVisible(False)
        self.copy_btn.setVisible(False)
        self.save_btn.setVisible(False)
        group = QGroupBox("Presentation", self)
        form = QFormLayout(group)
        self.enable_focus = QCheckBox("Use focus mode chrome", group)
        self.enable_focus.setChecked(True)
        self.read_only = QCheckBox("Read-only while reader mode is active", group)
        self.read_only.setChecked(True)
        self.wrap_text = QCheckBox("Enable soft wrap", group)
        self.wrap_text.setChecked(True)
        self.font_scale = QSpinBox(group)
        self.font_scale.setRange(90, 220)
        self.font_scale.setSuffix("%")
        self.font_scale.setValue(125)
        form.addRow(self.enable_focus)
        form.addRow(self.read_only)
        form.addRow(self.wrap_text)
        form.addRow("Text size:", self.font_scale)
        self.add_section(group)
        self.output.setPlainText("Use Apply to enable reader mode. Running it again restores the prior editor state.")
        self.close_btn.setText("Apply")
        self.close_btn.clicked.disconnect()
        self.close_btn.clicked.connect(self.apply_reader_mode)
        self.load_persisted_state()

    def apply_reader_mode(self) -> None:
        tab = self.window.active_tab() if hasattr(self.window, "active_tab") else None
        if tab is None:
            return
        editor = tab.text_edit
        enabled = not bool(getattr(tab, "_pypad_reader_mode_active", False))
        if enabled:
            tab._pypad_reader_mode_font = editor.current_font()
            tab._pypad_reader_mode_read_only = editor.is_read_only()
            font: QFont = QFont(editor.current_font())
            font.setPointSizeF(max(8.0, font.pointSizeF() * (self.font_scale.value() / 100.0)))
            editor.set_font(font)
            editor.set_read_only(bool(self.read_only.isChecked()))
            editor.set_wrap_enabled(bool(self.wrap_text.isChecked()))
            if self.enable_focus.isChecked() and hasattr(self.window, "toggle_focus_mode"):
                self.window.toggle_focus_mode(True)
            tab._pypad_reader_mode_active = True
            summary = f"Reader mode enabled at {self.font_scale.value()}%."
        else:
            original_font = getattr(tab, "_pypad_reader_mode_font", None)
            if isinstance(original_font, QFont):
                editor.set_font(original_font)
            editor.set_read_only(bool(getattr(tab, "_pypad_reader_mode_read_only", False)))
            if self.enable_focus.isChecked() and hasattr(self.window, "toggle_focus_mode"):
                self.window.toggle_focus_mode(False)
            tab._pypad_reader_mode_active = False
            summary = "Reader mode restored."
        self.window.settings["reader_mode_defaults"] = self.state()
        saver = getattr(self.window, "save_settings_to_disk", None)
        if callable(saver):
            saver()
        self.output.setPlainText(summary)
        self.accept()

    def state(self) -> dict[str, Any]:
        return {
            "focus": "true" if self.enable_focus.isChecked() else "false",
            "read_only": "true" if self.read_only.isChecked() else "false",
            "wrap": "true" if self.wrap_text.isChecked() else "false",
            "font_scale": str(self.font_scale.value()),
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.enable_focus.setChecked(str(state.get("focus", "true")).lower() not in {"false", "0"})
        self.read_only.setChecked(str(state.get("read_only", "true")).lower() not in {"false", "0"})
        self.wrap_text.setChecked(str(state.get("wrap", "true")).lower() not in {"false", "0"})
        try:
            self.font_scale.setValue(int(float(str(state.get("font_scale", "125")))))
        except Exception:
            pass
