"""Basic algebra and quadratic solving tools."""

from __future__ import annotations

import math
import re
from typing import Any

from PySide6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QLineEdit, QMessageBox, QPushButton

from .base_dialog import ToolDialogBase


def solve_linear_equation(equation: str) -> str:
    """Solve a simple linear equation like 2x + 3 = 11."""
    source = (equation or "").replace(" ", "")
    if "=" not in source:
        raise ValueError("Enter an equation with '='.")
    left, right = source.split("=", 1)
    match_left = re.fullmatch(r"([+-]?\d*\.?\d*)x([+-]\d*\.?\d+)?", left)
    match_right = re.fullmatch(r"([+-]?\d*\.?\d*)x([+-]\d*\.?\d+)?", right)
    if match_left:
        coeff_text = match_left.group(1)
        a = float(coeff_text in {"", "+", "-"} and f"{coeff_text}1" or coeff_text)
        b = float(match_left.group(2) or 0.0)
        c = 0.0
        d = float(right)
    elif match_right:
        coeff_text = match_right.group(1)
        a = 0.0
        b = float(left)
        c = float(coeff_text in {"", "+", "-"} and f"{coeff_text}1" or coeff_text)
        d = float(match_right.group(2) or 0.0)
    else:
        raise ValueError("Supported linear form: ax + b = c or c = ax + b.")
    coeff = a - c
    const = d - b
    if abs(coeff) < 1e-12:
        raise ValueError("Equation has no unique solution.")
    return f"x = {const / coeff:.12g}"


def solve_quadratic(a: float, b: float, c: float) -> str:
    """Solve ax^2 + bx + c = 0."""
    if abs(a) < 1e-12:
        raise ValueError("Coefficient 'a' must not be zero.")
    disc = b * b - 4 * a * c
    if disc < 0:
        real = -b / (2 * a)
        imag = math.sqrt(abs(disc)) / (2 * a)
        return f"x1 = {real:.12g} + {imag:.12g}i\nx2 = {real:.12g} - {imag:.12g}i"
    root = math.sqrt(disc)
    x1 = (-b + root) / (2 * a)
    x2 = (-b - root) / (2 * a)
    return f"x1 = {x1:.12g}\nx2 = {x2:.12g}"


class EquationSolverToolDialog(ToolDialogBase):
    """Friendly equation solving dialog for common algebra."""

    def __init__(self, parent) -> None:
        super().__init__(
            parent,
            tool_id="equation_solver",
            title="Equation Solver",
            help_text=(
                "Solve common algebra locally. Linear mode accepts forms like 2x + 3 = 11. "
                "Quadratic mode solves ax^2 + bx + c = 0 and returns real or complex roots."
            ),
        )
        group = QGroupBox("Equation", self)
        form = QFormLayout(group)
        self.mode_combo = QComboBox(group)
        self.mode_combo.addItems(["Linear", "Quadratic"])
        self.linear_input = QLineEdit(group)
        self.linear_input.setPlaceholderText("Example: 2x + 3 = 11")
        self.a_input = QLineEdit(group)
        self.b_input = QLineEdit(group)
        self.c_input = QLineEdit(group)
        self.a_input.setPlaceholderText("1")
        self.b_input.setPlaceholderText("0")
        self.c_input.setPlaceholderText("0")
        self.solve_btn = QPushButton("Solve", group)
        self.solve_btn.clicked.connect(self.solve)
        self.mode_combo.currentTextChanged.connect(self._sync_mode)
        form.addRow("Mode:", self.mode_combo)
        form.addRow("Linear equation:", self.linear_input)
        form.addRow("a:", self.a_input)
        form.addRow("b:", self.b_input)
        form.addRow("c:", self.c_input)
        form.addRow("", self.solve_btn)
        self.add_section(group)
        self._sync_mode(self.mode_combo.currentText())
        self.load_persisted_state()

    def _sync_mode(self, mode: str) -> None:
        quadratic = mode == "Quadratic"
        self.linear_input.setVisible(not quadratic)
        for widget in (self.a_input, self.b_input, self.c_input):
            widget.setVisible(quadratic)

    def solve(self) -> None:
        try:
            if self.mode_combo.currentText() == "Linear":
                result = solve_linear_equation(self.linear_input.text())
            else:
                result = solve_quadratic(float(self.a_input.text() or 0), float(self.b_input.text() or 0), float(self.c_input.text() or 0))
        except Exception as exc:
            QMessageBox.warning(self, self.windowTitle(), str(exc))
            return
        self.output.setPlainText(result)

    def state(self) -> dict[str, Any]:
        return {
            "mode": self.mode_combo.currentText(),
            "linear": self.linear_input.text(),
            "a": self.a_input.text(),
            "b": self.b_input.text(),
            "c": self.c_input.text(),
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        mode = str(state.get("mode", "Linear"))
        idx = self.mode_combo.findText(mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        self.linear_input.setText(str(state.get("linear", "")))
        self.a_input.setText(str(state.get("a", "1")))
        self.b_input.setText(str(state.get("b", "0")))
        self.c_input.setText(str(state.get("c", "0")))
