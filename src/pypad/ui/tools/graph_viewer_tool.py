"""Offline graph viewer using Qt painting."""

from __future__ import annotations

import ast
import math
from typing import Any

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFormLayout, QGroupBox, QLineEdit, QPushButton, QWidget

from .base_dialog import ToolDialogBase
from .scientific_calculator_tool import SAFE_FUNCTIONS, SAFE_NAMES


def evaluate_expression_with_x(expr: str, x_value: float) -> float:
    """Safely evaluate a math expression with x in scope."""
    source = (expr or "").strip().replace("^", "**")
    tree = ast.parse(source, mode="eval")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id == "x":
                return float(x_value)
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
            raise ValueError("Unsupported operator.")
        if isinstance(node, ast.UnaryOp):
            value = _eval(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fn = SAFE_FUNCTIONS.get(node.func.id)
            if fn is None:
                raise ValueError(f"Unsupported function: {node.func.id}")
            return float(fn(*[_eval(arg) for arg in node.args]))
        raise ValueError("Unsupported expression.")

    return float(_eval(tree))


def sample_expression_points(expression: str, x_min: float, x_max: float, steps: int = 240) -> list[tuple[float, float]]:
    """Sample y = f(x) for a bounded 2D plot."""
    points: list[tuple[float, float]] = []
    for index in range(max(2, steps)):
        x = x_min + (x_max - x_min) * index / max(1, steps - 1)
        y = evaluate_expression_with_x(expression, x)
        if math.isfinite(y):
            points.append((x, y))
    return points


class GraphCanvas(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.points: list[tuple[float, float]] = []
        self.setMinimumHeight(260)

    def set_points(self, points: list[tuple[float, float]]) -> None:
        self.points = list(points)
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect().adjusted(28, 12, -12, -24)
        painter.setPen(QPen(QColor("#d0d7de"), 1))
        for frac in (0.25, 0.5, 0.75):
            painter.drawLine(rect.left(), rect.top() + rect.height() * frac, rect.right(), rect.top() + rect.height() * frac)
            painter.drawLine(rect.left() + rect.width() * frac, rect.top(), rect.left() + rect.width() * frac, rect.bottom())
        if not self.points:
            return
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        if abs(y_max - y_min) < 1e-9:
            y_min -= 1.0
            y_max += 1.0
        path: list[QPointF] = []
        for x, y in self.points:
            px = rect.left() + ((x - x_min) / max(1e-9, x_max - x_min)) * rect.width()
            py = rect.bottom() - ((y - y_min) / max(1e-9, y_max - y_min)) * rect.height()
            path.append(QPointF(px, py))
        painter.setPen(QPen(QColor("#1f6feb"), 2))
        for index in range(1, len(path)):
            painter.drawLine(path[index - 1], path[index])


class GraphViewerToolDialog(ToolDialogBase):
    """Plot local expressions or simple datasets."""

    def __init__(self, parent, initial_text: str = "") -> None:
        super().__init__(
            parent,
            tool_id="graph_viewer",
            title="Offline Graph Viewer",
            help_text=(
                "Plot y = f(x) locally without any external services. Use the same safe math expressions as the calculator, "
                "or paste a comma-separated list of y-values to inspect a quick trend line."
            ),
        )
        group = QGroupBox("Plot", self)
        form = QFormLayout(group)
        self.expr_edit = QLineEdit(group)
        self.expr_edit.setPlaceholderText("sin(x) or x^2 - 4*x + 3")
        self.range_edit = QLineEdit(group)
        self.range_edit.setPlaceholderText("-10,10")
        self.plot_btn = QPushButton("Plot", group)
        self.canvas = GraphCanvas(group)
        self.plot_btn.clicked.connect(self.plot)
        form.addRow("Expression or values:", self.expr_edit)
        form.addRow("x-range:", self.range_edit)
        form.addRow("", self.plot_btn)
        form.addRow(self.canvas)
        self.add_section(group)
        self.load_persisted_state()
        seed = str(initial_text or "").strip()
        if seed:
            self.expr_edit.setText(seed)

    def plot(self) -> None:
        source = self.expr_edit.text().strip()
        if "," in source and "x" not in source and not any(ch.isalpha() for ch in source):
            values = [float(part.strip()) for part in source.split(",") if part.strip()]
            points = [(float(index), value) for index, value in enumerate(values)]
        else:
            x_min, x_max = -10.0, 10.0
            if "," in self.range_edit.text():
                left, right = self.range_edit.text().split(",", 1)
                x_min, x_max = float(left.strip()), float(right.strip())
            points = sample_expression_points(source, x_min, x_max)
        self.canvas.set_points(points)
        self.output.setPlainText(f"Rendered {len(points)} points.")

    def state(self) -> dict[str, Any]:
        return {"expression": self.expr_edit.text(), "range": self.range_edit.text()}

    def restore_state(self, state: dict[str, Any]) -> None:
        self.expr_edit.setText(str(state.get("expression", "")))
        self.range_edit.setText(str(state.get("range", "-10,10")))
