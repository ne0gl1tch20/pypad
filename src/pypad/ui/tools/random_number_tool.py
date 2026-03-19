"""Random number generator dialog."""

from __future__ import annotations

import random
from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QMessageBox,
    QPushButton,
    QSpinBox,
)

from .base_dialog import ToolDialogBase


def generate_random_numbers(
    *,
    mode: str,
    minimum: float,
    maximum: float,
    count: int,
    unique: bool,
    decimals: int,
    output_format: str,
) -> str:
    """Generate random numbers for the requested configuration."""
    if maximum < minimum:
        minimum, maximum = maximum, minimum
    if mode == "integer":
        lo = int(round(minimum))
        hi = int(round(maximum))
        if unique and count > (hi - lo + 1):
            raise ValueError("Count exceeds the available unique integer range.")
        values = random.sample(range(lo, hi + 1), count) if unique else [random.randint(lo, hi) for _ in range(count)]
        rendered = [str(value) for value in values]
    else:
        rendered = [f"{random.uniform(minimum, maximum):.{decimals}f}" for _ in range(count)]
    if output_format == "comma":
        return ", ".join(rendered)
    if output_format == "single":
        return rendered[0] if rendered else ""
    return "\n".join(rendered)


class RandomNumberToolDialog(ToolDialogBase):
    """Interactive generator for random numbers."""

    def __init__(self, parent) -> None:
        super().__init__(
            parent,
            tool_id="random_number",
            title="Random Number Generator",
            help_text=(
                "Choose integer or decimal mode, set the range and output format, then "
                "generate values to insert into the active note or copy to the clipboard."
            ),
        )
        group = QGroupBox("Generator", self)
        form = QFormLayout(group)
        self.mode_combo = QComboBox(group)
        self.mode_combo.addItems(["integer", "decimal"])
        self.min_spin = QDoubleSpinBox(group)
        self.min_spin.setRange(-1_000_000_000, 1_000_000_000)
        self.min_spin.setValue(1)
        self.max_spin = QDoubleSpinBox(group)
        self.max_spin.setRange(-1_000_000_000, 1_000_000_000)
        self.max_spin.setValue(100)
        self.count_spin = QSpinBox(group)
        self.count_spin.setRange(1, 1000)
        self.count_spin.setValue(1)
        self.unique_check = QCheckBox("Unique values", group)
        self.decimals_spin = QSpinBox(group)
        self.decimals_spin.setRange(0, 8)
        self.decimals_spin.setValue(2)
        self.format_combo = QComboBox(group)
        self.format_combo.addItems(["lines", "comma", "single"])
        self.generate_btn = QPushButton("Generate", group)
        self.generate_btn.clicked.connect(self.generate_output)
        self.mode_combo.currentTextChanged.connect(self._sync_mode)

        form.addRow("Mode:", self.mode_combo)
        form.addRow("Minimum:", self.min_spin)
        form.addRow("Maximum:", self.max_spin)
        form.addRow("Count:", self.count_spin)
        form.addRow("", self.unique_check)
        form.addRow("Decimals:", self.decimals_spin)
        form.addRow("Format:", self.format_combo)
        form.addRow("", self.generate_btn)
        self.add_section(group)
        self.load_persisted_state()
        self._sync_mode(self.mode_combo.currentText())

    def _sync_mode(self, mode: str) -> None:
        decimal_mode = mode == "decimal"
        self.unique_check.setEnabled(not decimal_mode)
        self.decimals_spin.setEnabled(decimal_mode)
        if decimal_mode:
            self.unique_check.setChecked(False)

    def generate_output(self) -> None:
        try:
            text = generate_random_numbers(
                mode=self.mode_combo.currentText(),
                minimum=float(self.min_spin.value()),
                maximum=float(self.max_spin.value()),
                count=int(self.count_spin.value()),
                unique=self.unique_check.isChecked(),
                decimals=int(self.decimals_spin.value()),
                output_format=self.format_combo.currentText(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, self.windowTitle(), str(exc))
            return
        self.output.setPlainText(text)

    def state(self) -> dict[str, Any]:
        return {
            "mode": self.mode_combo.currentText(),
            "minimum": self.min_spin.value(),
            "maximum": self.max_spin.value(),
            "count": self.count_spin.value(),
            "unique": self.unique_check.isChecked(),
            "decimals": self.decimals_spin.value(),
            "format": self.format_combo.currentText(),
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.mode_combo.setCurrentText(str(state.get("mode", "integer")))
        self.min_spin.setValue(float(state.get("minimum", 1)))
        self.max_spin.setValue(float(state.get("maximum", 100)))
        self.count_spin.setValue(max(1, int(state.get("count", 1))))
        self.unique_check.setChecked(bool(state.get("unique", False)))
        self.decimals_spin.setValue(max(0, min(8, int(state.get("decimals", 2)))))
        self.format_combo.setCurrentText(str(state.get("format", "lines")))
