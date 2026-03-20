"""Registration helpers for built-in offline tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtGui import QAction

from .annotations_tool import AnnotationsToolDialog
from .color_picker_tool import ColorPickerToolDialog
from .currency_tool import CurrencyToolDialog
from .equation_solver_tool import EquationSolverToolDialog
from .finance_tool import FinanceToolDialog
from .graph_viewer_tool import GraphViewerToolDialog
from .password_tool import PasswordToolDialog
from .qr_tool import QRToolDialog
from .random_number_tool import RandomNumberToolDialog
from .reader_mode_tool import ReaderModeToolDialog
from .reminders_tool import RemindersToolDialog
from .scientific_calculator_tool import ScientificCalculatorToolDialog
from .taskers_tool import TaskersToolDialog
from .timer_tool import TimerToolDialog
from .unit_converter_tool import UnitConverterToolDialog
from .world_clock_tool import WorldClockToolDialog


@dataclass(frozen=True)
class ToolDescriptor:
    tool_id: str
    title: str
    object_name: str
    launcher_name: str


class BuiltInToolsController:
    DESCRIPTORS = (
        ToolDescriptor("random_number", "Random Number Generator...", "toolRandomNumberAction", "open_random_number_tool"),
        ToolDescriptor("password_generator", "Password Generator...", "toolPasswordGeneratorAction", "open_password_generator_tool"),
        ToolDescriptor("finance_calculator", "Percentage / Finance Calculator...", "toolFinanceCalculatorAction", "open_finance_calculator_tool"),
        ToolDescriptor("scientific_calculator", "Scientific Calculator...", "toolScientificCalculatorAction", "open_scientific_calculator_tool"),
        ToolDescriptor("unit_converter", "Unit Converter...", "toolUnitConverterAction", "open_unit_converter_tool"),
        ToolDescriptor("equation_solver", "Equation Solver...", "toolEquationSolverAction", "open_equation_solver_tool"),
        ToolDescriptor("graph_viewer", "Offline Graph Viewer...", "toolGraphViewerAction", "open_graph_viewer_tool"),
        ToolDescriptor("currency_converter", "Currency Converter...", "toolCurrencyConverterAction", "open_currency_converter_tool"),
        ToolDescriptor("timer_stopwatch", "Timer / Stopwatch...", "toolTimerStopwatchAction", "open_timer_stopwatch_tool"),
        ToolDescriptor("color_picker", "Color Picker...", "toolColorPickerAction", "open_color_picker_tool"),
        ToolDescriptor("world_clock", "World Clock...", "toolWorldClockAction", "open_world_clock_tool"),
        ToolDescriptor("reminders_hub", "Reminders...", "toolRemindersHubAction", "open_reminders_tool"),
        ToolDescriptor("taskers", "Taskers...", "toolTaskersAction", "open_taskers_tool"),
        ToolDescriptor("reader_mode", "Clean Reader Mode...", "toolReaderModeAction", "open_reader_mode_tool"),
        ToolDescriptor("annotations_manager", "Highlights + Notes...", "toolHighlightsNotesAction", "open_annotations_tool"),
        ToolDescriptor("qr_tools", "QR Generator / Scanner...", "toolQrToolsAction", "open_qr_tool"),
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
        self._exec(lambda: RandomNumberToolDialog(self.window))

    def open_password_generator_tool(self) -> None:
        self._exec(lambda: PasswordToolDialog(self.window))

    def open_finance_calculator_tool(self) -> None:
        self._exec(lambda: FinanceToolDialog(self.window, initial_text=self._current_selection_text()))

    def open_color_picker_tool(self) -> None:
        self._exec(lambda: ColorPickerToolDialog(self.window))

    def open_world_clock_tool(self) -> None:
        self._exec(lambda: WorldClockToolDialog(self.window))

    def open_scientific_calculator_tool(self) -> None:
        self._exec(lambda: ScientificCalculatorToolDialog(self.window, initial_text=self._current_selection_text()))

    def open_unit_converter_tool(self) -> None:
        self._exec(lambda: UnitConverterToolDialog(self.window, initial_text=self._current_selection_text()))

    def open_equation_solver_tool(self) -> None:
        self._exec(lambda: EquationSolverToolDialog(self.window, initial_text=self._current_selection_text()))

    def open_graph_viewer_tool(self) -> None:
        self._exec(lambda: GraphViewerToolDialog(self.window, initial_text=self._current_selection_text()))

    def open_currency_converter_tool(self) -> None:
        self._exec(lambda: CurrencyToolDialog(self.window, initial_text=self._current_selection_text()))

    def open_timer_stopwatch_tool(self) -> None:
        self._exec(lambda: TimerToolDialog(self.window))

    def open_reminders_tool(self) -> None:
        self._exec(lambda: RemindersToolDialog(self.window))

    def open_taskers_tool(self) -> None:
        self._exec(lambda: TaskersToolDialog(self.window, initial_text=self._current_selection_text()))

    def open_reader_mode_tool(self) -> None:
        self._exec(lambda: ReaderModeToolDialog(self.window))

    def open_annotations_tool(self) -> None:
        self._exec(lambda: AnnotationsToolDialog(self.window, initial_text=self._current_selection_text()))

    def open_qr_tool(self) -> None:
        self._exec(lambda: QRToolDialog(self.window, initial_text=self._current_selection_text()))
