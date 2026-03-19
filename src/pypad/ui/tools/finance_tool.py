"""Percentage and finance calculator dialog."""

from __future__ import annotations

import math
from typing import Any

from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QMessageBox, QPushButton

from .base_dialog import ToolDialogBase


def calculate_finance_result(mode: str, a: float, b: float, c: float, d: float) -> str:
    """Compute a compact result string for the selected finance mode."""
    if mode == "percent_of":
        return f"{a}% of {b} = {(a / 100.0) * b:.4f}"
    if mode == "percentage_change":
        if a == 0:
            raise ValueError("Original value cannot be zero.")
        return f"Change from {a} to {b} = {((b - a) / a) * 100.0:.4f}%"
    if mode == "markup":
        if b == 0:
            raise ValueError("Cost cannot be zero.")
        margin = ((a - b) / a) * 100.0 if a else 0.0
        markup = ((a - b) / b) * 100.0
        return f"Selling price {a:.4f} on cost {b:.4f}: markup {markup:.4f}%, margin {margin:.4f}%"
    if mode == "simple_interest":
        total = a * (1.0 + (b / 100.0) * c)
        return f"Simple interest total = {total:.4f}"
    if mode == "compound_growth":
        total = a * math.pow(1.0 + (b / 100.0) / max(1.0, c), c * d)
        return f"Compound growth total = {total:.4f}"
    if mode == "loan_payment":
        monthly_rate = (b / 100.0) / 12.0
        months = max(1, int(round(c)))
        if monthly_rate == 0:
            return f"Estimated monthly payment = {a / months:.4f}"
        factor = math.pow(1.0 + monthly_rate, months)
        payment = a * (monthly_rate * factor) / (factor - 1.0)
        return f"Estimated monthly payment = {payment:.4f}"
    raise ValueError("Unknown calculator mode.")


class FinanceToolDialog(ToolDialogBase):
    """Local percentage and finance calculations."""

    MODE_LABELS = {
        "percent_of": "Percent of value",
        "percentage_change": "Percentage change",
        "markup": "Markup / margin",
        "simple_interest": "Simple interest",
        "compound_growth": "Compound growth",
        "loan_payment": "Loan payment",
    }
    FIELD_LABELS = {
        "percent_of": ("Percent", "Value", "Unused", "Unused"),
        "percentage_change": ("Original", "New", "Unused", "Unused"),
        "markup": ("Selling price", "Cost", "Unused", "Unused"),
        "simple_interest": ("Principal", "Rate %", "Years", "Unused"),
        "compound_growth": ("Principal", "Rate %", "Compounds/year", "Years"),
        "loan_payment": ("Principal", "Rate %", "Months", "Unused"),
    }

    def __init__(self, parent) -> None:
        super().__init__(
            parent,
            tool_id="finance_calculator",
            title="Percentage / Finance Calculator",
            help_text=(
                "Switch between percentage and finance formulas, enter values, then copy or insert "
                "the rendered result as plain text."
            ),
        )
        group = QGroupBox("Calculator", self)
        self.form = QFormLayout(group)
        self.mode_combo = QComboBox(group)
        self.mode_combo.addItems(list(self.MODE_LABELS.values()))
        self.a_spin = QDoubleSpinBox(group)
        self.b_spin = QDoubleSpinBox(group)
        self.c_spin = QDoubleSpinBox(group)
        self.d_spin = QDoubleSpinBox(group)
        for spin in (self.a_spin, self.b_spin, self.c_spin, self.d_spin):
            spin.setRange(-1_000_000_000, 1_000_000_000)
            spin.setDecimals(6)
        self.a_spin.setValue(10)
        self.b_spin.setValue(100)
        self.c_spin.setValue(1)
        self.d_spin.setValue(1)
        self.compute_btn = QPushButton("Calculate", group)
        self.compute_btn.clicked.connect(self.calculate)
        self.mode_combo.currentTextChanged.connect(self._sync_labels)

        self.form.addRow("Mode:", self.mode_combo)
        self.form.addRow("Value A:", self.a_spin)
        self.form.addRow("Value B:", self.b_spin)
        self.form.addRow("Value C:", self.c_spin)
        self.form.addRow("Value D:", self.d_spin)
        self.form.addRow("", self.compute_btn)
        self.add_section(group)
        self.load_persisted_state()
        self._sync_labels(self.mode_combo.currentText())

    def _mode_key(self) -> str:
        selected = self.mode_combo.currentText()
        for key, label in self.MODE_LABELS.items():
            if label == selected:
                return key
        return "percent_of"

    def _sync_labels(self, _label: str) -> None:
        labels = self.FIELD_LABELS[self._mode_key()]
        self.form.labelForField(self.a_spin).setText(f"{labels[0]}:")
        self.form.labelForField(self.b_spin).setText(f"{labels[1]}:")
        self.form.labelForField(self.c_spin).setText(f"{labels[2]}:")
        self.form.labelForField(self.d_spin).setText(f"{labels[3]}:")
        self.c_spin.setEnabled(labels[2] != "Unused")
        self.d_spin.setEnabled(labels[3] != "Unused")

    def calculate(self) -> None:
        try:
            text = calculate_finance_result(
                self._mode_key(),
                self.a_spin.value(),
                self.b_spin.value(),
                self.c_spin.value(),
                self.d_spin.value(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, self.windowTitle(), str(exc))
            return
        self.output.setPlainText(text)

    def state(self) -> dict[str, Any]:
        return {
            "mode": self._mode_key(),
            "a": self.a_spin.value(),
            "b": self.b_spin.value(),
            "c": self.c_spin.value(),
            "d": self.d_spin.value(),
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.mode_combo.setCurrentText(self.MODE_LABELS.get(str(state.get("mode", "percent_of")), self.MODE_LABELS["percent_of"]))
        self.a_spin.setValue(float(state.get("a", 10)))
        self.b_spin.setValue(float(state.get("b", 100)))
        self.c_spin.setValue(float(state.get("c", 1)))
        self.d_spin.setValue(float(state.get("d", 1)))
