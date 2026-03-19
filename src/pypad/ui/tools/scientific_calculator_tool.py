"""Scientific calculator dialog with a restricted expression evaluator."""

from __future__ import annotations

import ast
import math
from typing import Any

from PySide6.QtWidgets import QFormLayout, QGroupBox, QLineEdit, QListWidget, QMessageBox, QPushButton

from .base_dialog import ToolDialogBase

SAFE_FUNCTIONS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "floor": math.floor,
    "ceil": math.ceil,
    "round": round,
}
SAFE_NAMES = {"pi": math.pi, "e": math.e}


def evaluate_expression(expr: str) -> float:
    """Safely evaluate a math expression without using eval()."""
    source = (expr or "").strip().replace("^", "**")
    if not source:
        raise ValueError("Enter an expression.")
    tree = ast.parse(source, mode="eval")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id in SAFE_NAMES:
                return float(SAFE_NAMES[node.id])
            raise ValueError(f"Unknown name: {node.id}")
        if isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Pow):
                return left**right
            if isinstance(node.op, ast.Mod):
                return left % right
            raise ValueError("Unsupported operator.")
        if isinstance(node, ast.UnaryOp):
            value = _eval(node.operand)
            if isinstance(node.op, ast.UAdd):
                return value
            if isinstance(node.op, ast.USub):
                return -value
            raise ValueError("Unsupported unary operator.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fn = SAFE_FUNCTIONS.get(node.func.id)
            if fn is None:
                raise ValueError(f"Unsupported function: {node.func.id}")
            args = [_eval(arg) for arg in node.args]
            return float(fn(*args))
        raise ValueError("Unsupported expression.")

    return float(_eval(tree))


class ScientificCalculatorToolDialog(ToolDialogBase):
    """Evaluate scientific calculator expressions locally."""

    def __init__(self, parent) -> None:
        super().__init__(
            parent,
            tool_id="scientific_calculator",
            title="Scientific Calculator",
            help_text=(
                "Enter a math expression using operators and built-in functions such as "
                "sin, cos, tan, sqrt, log, exp, abs, round, pi, and e."
            ),
        )
        group = QGroupBox("Expression", self)
        form = QFormLayout(group)
        self.expr_edit = QLineEdit(group)
        self.expr_edit.setPlaceholderText("Example: sin(pi / 2) + sqrt(9)")
        self.history = QListWidget(group)
        self.history.setAccessibleName("Scientific calculator history")
        self.compute_btn = QPushButton("Calculate", group)
        self.compute_btn.clicked.connect(self.calculate)
        self.history.itemActivated.connect(lambda item: self.expr_edit.setText(item.text().split(" = ", 1)[0]))
        self.expr_edit.returnPressed.connect(self.calculate)
        form.addRow("Expression:", self.expr_edit)
        form.addRow("", self.compute_btn)
        form.addRow("History:", self.history)
        self.add_section(group)
        self.load_persisted_state()

    def calculate(self) -> None:
        try:
            result = evaluate_expression(self.expr_edit.text())
        except Exception as exc:
            QMessageBox.warning(self, self.windowTitle(), str(exc))
            return
        rendered = f"{self.expr_edit.text().strip()} = {result:.12g}"
        self.output.setPlainText(rendered)
        self.history.insertItem(0, rendered)
        while self.history.count() > 20:
            self.history.takeItem(self.history.count() - 1)

    def state(self) -> dict[str, Any]:
        return {
            "expression": self.expr_edit.text(),
            "history": [self.history.item(i).text() for i in range(self.history.count())][:20],
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.expr_edit.setText(str(state.get("expression", "")))
        history = state.get("history", [])
        if isinstance(history, list):
            for row in history[:20]:
                text = str(row).strip()
                if text:
                    self.history.addItem(text)
