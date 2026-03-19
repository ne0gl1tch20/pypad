"""Offline unit converter dialog."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QPushButton

from .base_dialog import ToolDialogBase

LENGTH_FACTORS = {"mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0, "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344}
WEIGHT_FACTORS = {"mg": 0.000001, "g": 0.001, "kg": 1.0, "lb": 0.45359237, "oz": 0.028349523125}


def convert_unit(category: str, value: float, from_unit: str, to_unit: str) -> float:
    """Convert a numeric value between supported units."""
    if category == "length":
        return value * LENGTH_FACTORS[from_unit] / LENGTH_FACTORS[to_unit]
    if category == "weight":
        return value * WEIGHT_FACTORS[from_unit] / WEIGHT_FACTORS[to_unit]
    if category == "temperature":
        celsius = value
        if from_unit == "F":
            celsius = (value - 32.0) * 5.0 / 9.0
        elif from_unit == "K":
            celsius = value - 273.15
        if to_unit == "C":
            return celsius
        if to_unit == "F":
            return (celsius * 9.0 / 5.0) + 32.0
        return celsius + 273.15
    raise ValueError("Unsupported conversion category.")


class UnitConverterToolDialog(ToolDialogBase):
    """Convert common offline units."""

    CATEGORY_UNITS = {
        "length": list(LENGTH_FACTORS.keys()),
        "weight": list(WEIGHT_FACTORS.keys()),
        "temperature": ["C", "F", "K"],
    }

    def __init__(self, parent) -> None:
        super().__init__(
            parent,
            tool_id="unit_converter",
            title="Unit Converter",
            help_text="Convert common length, weight, and temperature units locally and insert or copy the result.",
        )
        group = QGroupBox("Conversion", self)
        form = QFormLayout(group)
        self.category_combo = QComboBox(group)
        self.category_combo.addItems(list(self.CATEGORY_UNITS.keys()))
        self.value_spin = QDoubleSpinBox(group)
        self.value_spin.setRange(-1_000_000_000, 1_000_000_000)
        self.value_spin.setDecimals(8)
        self.value_spin.setValue(1.0)
        self.from_combo = QComboBox(group)
        self.to_combo = QComboBox(group)
        self.convert_btn = QPushButton("Convert", group)
        self.convert_btn.clicked.connect(self.convert)
        self.category_combo.currentTextChanged.connect(self._sync_units)
        form.addRow("Category:", self.category_combo)
        form.addRow("Value:", self.value_spin)
        form.addRow("From:", self.from_combo)
        form.addRow("To:", self.to_combo)
        form.addRow("", self.convert_btn)
        self.add_section(group)
        self.load_persisted_state()
        self._sync_units(self.category_combo.currentText())

    def _sync_units(self, category: str) -> None:
        units = self.CATEGORY_UNITS.get(category, [])
        current_from = self.from_combo.currentText()
        current_to = self.to_combo.currentText()
        self.from_combo.clear()
        self.to_combo.clear()
        self.from_combo.addItems(units)
        self.to_combo.addItems(units)
        if current_from in units:
            self.from_combo.setCurrentText(current_from)
        if current_to in units:
            self.to_combo.setCurrentText(current_to)
        elif len(units) > 1:
            self.to_combo.setCurrentIndex(1)

    def convert(self) -> None:
        category = self.category_combo.currentText()
        from_unit = self.from_combo.currentText()
        to_unit = self.to_combo.currentText()
        result = convert_unit(category, self.value_spin.value(), from_unit, to_unit)
        self.output.setPlainText(f"{self.value_spin.value():.8g} {from_unit} = {result:.8g} {to_unit}")

    def state(self) -> dict[str, Any]:
        return {
            "category": self.category_combo.currentText(),
            "value": self.value_spin.value(),
            "from": self.from_combo.currentText(),
            "to": self.to_combo.currentText(),
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.category_combo.setCurrentText(str(state.get("category", "length")))
        self._sync_units(self.category_combo.currentText())
        self.value_spin.setValue(float(state.get("value", 1.0)))
        self.from_combo.setCurrentText(str(state.get("from", self.from_combo.currentText())))
        self.to_combo.setCurrentText(str(state.get("to", self.to_combo.currentText())))
