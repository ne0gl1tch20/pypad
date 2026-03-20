"""Registration helpers for built-in offline tools."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Callable

from PySide6.QtGui import QAction

@dataclass(frozen=True)
class ToolDescriptor:
    tool_id: str
    title: str
    object_name: str
    launcher_name: str
    module_name: str
    class_name: str


class BuiltInToolsController:
    DESCRIPTORS = (
        ToolDescriptor("random_number", "Random Number Generator...", "toolRandomNumberAction", "open_random_number_tool", "random_number_tool", "RandomNumberToolDialog"),
        ToolDescriptor("password_generator", "Password Generator...", "toolPasswordGeneratorAction", "open_password_generator_tool", "password_tool", "PasswordToolDialog"),
        ToolDescriptor("finance_calculator", "Percentage / Finance Calculator...", "toolFinanceCalculatorAction", "open_finance_calculator_tool", "finance_tool", "FinanceToolDialog"),
        ToolDescriptor("scientific_calculator", "Scientific Calculator...", "toolScientificCalculatorAction", "open_scientific_calculator_tool", "scientific_calculator_tool", "ScientificCalculatorToolDialog"),
        ToolDescriptor("unit_converter", "Unit Converter...", "toolUnitConverterAction", "open_unit_converter_tool", "unit_converter_tool", "UnitConverterToolDialog"),
        ToolDescriptor("equation_solver", "Equation Solver...", "toolEquationSolverAction", "open_equation_solver_tool", "equation_solver_tool", "EquationSolverToolDialog"),
        ToolDescriptor("graph_viewer", "Offline Graph Viewer...", "toolGraphViewerAction", "open_graph_viewer_tool", "graph_viewer_tool", "GraphViewerToolDialog"),
        ToolDescriptor("currency_converter", "Currency Converter...", "toolCurrencyConverterAction", "open_currency_converter_tool", "currency_tool", "CurrencyToolDialog"),
        ToolDescriptor("timer_stopwatch", "Timer / Stopwatch...", "toolTimerStopwatchAction", "open_timer_stopwatch_tool", "timer_tool", "TimerToolDialog"),
        ToolDescriptor("color_picker", "Color Picker...", "toolColorPickerAction", "open_color_picker_tool", "color_picker_tool", "ColorPickerToolDialog"),
        ToolDescriptor("world_clock", "World Clock...", "toolWorldClockAction", "open_world_clock_tool", "world_clock_tool", "WorldClockToolDialog"),
        ToolDescriptor("reminders_hub", "Reminders...", "toolRemindersHubAction", "open_reminders_tool", "reminders_tool", "RemindersToolDialog"),
        ToolDescriptor("taskers", "Taskers...", "toolTaskersAction", "open_taskers_tool", "taskers_tool", "TaskersToolDialog"),
        ToolDescriptor("reader_mode", "Clean Reader Mode...", "toolReaderModeAction", "open_reader_mode_tool", "reader_mode_tool", "ReaderModeToolDialog"),
        ToolDescriptor("annotations_manager", "Highlights + Notes...", "toolHighlightsNotesAction", "open_annotations_tool", "annotations_tool", "AnnotationsToolDialog"),
        ToolDescriptor("qr_tools", "QR Generator / Scanner...", "toolQrToolsAction", "open_qr_tool", "qr_tool", "QRToolDialog"),
    )

    def __init__(self, window) -> None:
        self.window = window
        self.actions: dict[str, QAction] = {}

    def create_actions(self) -> None:
        for descriptor in self.DESCRIPTORS:
            launcher = getattr(self, descriptor.launcher_name)
            action = QAction(descriptor.title, self.window)
            action.setObjectName(descriptor.object_name)
            action.triggered.connect(launcher)
            setattr(self.window, f"{descriptor.tool_id}_action", action)
            self.actions[descriptor.tool_id] = action

    def add_to_menu(self, menu) -> None:
        for descriptor in self.DESCRIPTORS:
            action = self.actions.get(descriptor.tool_id)
            if action is not None:
                menu.addAction(action)

    def _resolve_dialog_class(self, tool_id: str):
        descriptor = next(item for item in self.DESCRIPTORS if item.tool_id == tool_id)
        module = importlib.import_module(f"{__package__}.{descriptor.module_name}")
        return getattr(module, descriptor.class_name)

    def _exec(self, dialog_factory: Callable[[], object]) -> None:
        dialog = dialog_factory()
        if hasattr(dialog, "exec"):
            dialog.exec()

    def _current_selection_text(self) -> str:
        tab = self.window.active_tab() if hasattr(self.window, "active_tab") else None
        if tab is None or not hasattr(tab, "text_edit"):
            return ""
        try:
            return str(tab.text_edit.selected_text() or "").strip()
        except Exception:
            return ""

    def open_random_number_tool(self) -> None:
        dialog_class = self._resolve_dialog_class("random_number")
        self._exec(lambda: dialog_class(self.window))

    def open_password_generator_tool(self) -> None:
        dialog_class = self._resolve_dialog_class("password_generator")
        self._exec(lambda: dialog_class(self.window))

    def open_finance_calculator_tool(self) -> None:
        dialog_class = self._resolve_dialog_class("finance_calculator")
        self._exec(lambda: dialog_class(self.window, initial_text=self._current_selection_text()))

    def open_color_picker_tool(self) -> None:
        dialog_class = self._resolve_dialog_class("color_picker")
        self._exec(lambda: dialog_class(self.window))

    def open_world_clock_tool(self) -> None:
        dialog_class = self._resolve_dialog_class("world_clock")
        self._exec(lambda: dialog_class(self.window))

    def open_scientific_calculator_tool(self) -> None:
        dialog_class = self._resolve_dialog_class("scientific_calculator")
        self._exec(lambda: dialog_class(self.window, initial_text=self._current_selection_text()))

    def open_unit_converter_tool(self) -> None:
        dialog_class = self._resolve_dialog_class("unit_converter")
        self._exec(lambda: dialog_class(self.window, initial_text=self._current_selection_text()))

    def open_equation_solver_tool(self) -> None:
        dialog_class = self._resolve_dialog_class("equation_solver")
        self._exec(lambda: dialog_class(self.window, initial_text=self._current_selection_text()))

    def open_graph_viewer_tool(self) -> None:
        dialog_class = self._resolve_dialog_class("graph_viewer")
        self._exec(lambda: dialog_class(self.window, initial_text=self._current_selection_text()))

    def open_currency_converter_tool(self) -> None:
        dialog_class = self._resolve_dialog_class("currency_converter")
        self._exec(lambda: dialog_class(self.window, initial_text=self._current_selection_text()))

    def open_timer_stopwatch_tool(self) -> None:
        dialog_class = self._resolve_dialog_class("timer_stopwatch")
        self._exec(lambda: dialog_class(self.window))

    def open_reminders_tool(self) -> None:
        dialog_class = self._resolve_dialog_class("reminders_hub")
        self._exec(lambda: dialog_class(self.window))

    def open_taskers_tool(self) -> None:
        dialog_class = self._resolve_dialog_class("taskers")
        self._exec(lambda: dialog_class(self.window, initial_text=self._current_selection_text()))

    def open_reader_mode_tool(self) -> None:
        dialog_class = self._resolve_dialog_class("reader_mode")
        self._exec(lambda: dialog_class(self.window))

    def open_annotations_tool(self) -> None:
        dialog_class = self._resolve_dialog_class("annotations_manager")
        self._exec(lambda: dialog_class(self.window, initial_text=self._current_selection_text()))

    def open_qr_tool(self) -> None:
        dialog_class = self._resolve_dialog_class("qr_tools")
        self._exec(lambda: dialog_class(self.window, initial_text=self._current_selection_text()))
