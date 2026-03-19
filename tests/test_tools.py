import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PySide6.QtWidgets import QApplication, QMainWindow

from pypad.app_settings.defaults import build_default_settings
from pypad.ui.system.reminders import ReminderStore
from pypad.ui.tools.annotations_tool import AnnotationsToolDialog
from pypad.ui.tools.color_picker_tool import ColorPickerToolDialog, color_to_hsl_string
from pypad.ui.tools.currency_tool import CurrencyToolDialog, convert_currency
from pypad.ui.tools.equation_solver_tool import EquationSolverToolDialog, solve_linear_equation, solve_quadratic
from pypad.ui.tools.finance_tool import FinanceToolDialog, calculate_finance_result
from pypad.ui.tools.graph_viewer_tool import GraphViewerToolDialog, sample_expression_points
from pypad.ui.tools.password_tool import PasswordToolDialog, build_password, password_strength
from pypad.ui.tools.qr_tool import decode_any_qr_image, decode_matrix_payload, encode_matrix_payload, matrix_to_image, qimage_to_zxing_buffer
from pypad.ui.tools.random_number_tool import RandomNumberToolDialog, generate_random_numbers
from pypad.ui.tools.reader_mode_tool import ReaderModeToolDialog
from pypad.ui.tools.reminders_tool import RemindersToolDialog, summarize_reminders
from pypad.ui.tools.registry import BuiltInToolsController
from pypad.ui.tools.scientific_calculator_tool import ScientificCalculatorToolDialog, evaluate_expression
from pypad.ui.tools.taskers_tool import TaskersToolDialog, task_scope_from_window
from pypad.ui.tools.timer_tool import TimerToolDialog, format_seconds
from pypad.ui.tools.unit_converter_tool import UnitConverterToolDialog, convert_unit
from pypad.ui.tools.world_clock_tool import WorldClockToolDialog, format_world_clock_rows


class _ParentWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = build_default_settings(default_style="Windows", font_family="Segoe UI", font_size=11)
        self._saved = 0
        self.reminders_store = ReminderStore(ROOT / "tests_tmp_reminders.json")

    def active_tab(self):
        return None

    def show_status_message(self, _message: str, _timeout: int = 0) -> None:
        return

    def save_settings_to_disk(self, *, synchronous: bool = False) -> None:
        self._saved += 1


class BuiltInToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_random_number_generator_supports_unique_integers(self) -> None:
        out = generate_random_numbers(
            mode="integer",
            minimum=1,
            maximum=5,
            count=5,
            unique=True,
            decimals=0,
            output_format="lines",
        )
        values = [int(part) for part in out.splitlines()]
        self.assertEqual(sorted(values), [1, 2, 3, 4, 5])

    def test_password_generator_respects_policy(self) -> None:
        password = build_password(
            length=24,
            use_upper=True,
            use_lower=True,
            use_digits=True,
            use_symbols=True,
            exclude_ambiguous=True,
        )
        self.assertEqual(len(password), 24)
        self.assertEqual(password_strength(password), "Strong")
        self.assertFalse(any(ch in "0O1lI|" for ch in password))

    def test_finance_helper_calculates_percentage_change(self) -> None:
        out = calculate_finance_result("percentage_change", 100, 150, 0, 0)
        self.assertIn("50.0000%", out)

    def test_world_clock_rows_render_requested_zones(self) -> None:
        rows = format_world_clock_rows(["UTC", "Asia/Tokyo"])
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0].startswith("UTC | "))

    def test_scientific_calculator_evaluates_safe_expression(self) -> None:
        result = evaluate_expression("sin(pi / 2) + sqrt(9)")
        self.assertAlmostEqual(result, 4.0, places=6)

    def test_unit_converter_supports_temperature(self) -> None:
        self.assertAlmostEqual(convert_unit("temperature", 0.0, "C", "F"), 32.0, places=6)

    def test_timer_formatter_renders_hms(self) -> None:
        self.assertEqual(format_seconds(3661), "01:01:01")

    def test_color_hsl_string_is_rendered(self) -> None:
        from PySide6.QtGui import QColor

        self.assertTrue(color_to_hsl_string(QColor("#4a90e2")).startswith("hsl("))

    def test_equation_solver_helpers_cover_linear_and_quadratic(self) -> None:
        self.assertEqual(solve_linear_equation("2x + 3 = 11"), "x = 4")
        self.assertIn("x1 = 3", solve_quadratic(1, -5, 6))

    def test_currency_converter_uses_cached_rates(self) -> None:
        self.assertAlmostEqual(convert_currency(10.0, "USD", "EUR", {"USD": 1.0, "EUR": 0.5}), 5.0, places=6)

    def test_graph_sampler_produces_points(self) -> None:
        points = sample_expression_points("x^2", -2.0, 2.0, steps=5)
        self.assertEqual(len(points), 5)
        self.assertEqual(points[0][1], 4.0)

    def test_qr_payload_round_trip(self) -> None:
        payload = "https://example.test/pypad"
        self.assertEqual(decode_matrix_payload(encode_matrix_payload(payload)), payload)

    def test_qr_decoder_falls_back_to_pypad_matrix_images(self) -> None:
        payload = "offline-fallback"
        image = matrix_to_image(encode_matrix_payload(payload))
        self.assertEqual(decode_any_qr_image(image), payload)

    def test_qimage_to_zxing_buffer_matches_general_decoder_contract(self) -> None:
        try:
            import zxingcpp
        except Exception:
            self.skipTest("zxing-cpp not installed")
        barcode = zxingcpp.create_barcode("general-qr", zxingcpp.BarcodeFormat.QRCode)
        source = zxingcpp.write_barcode_to_image(barcode, 8)
        source_bytes = memoryview(source).tobytes()
        image = __import__("PySide6.QtGui", fromlist=["QImage"]).QImage(source_bytes, source.shape[1], source.shape[0], source.shape[1], __import__("PySide6.QtGui", fromlist=["QImage"]).QImage.Format_Grayscale8).copy().scaled(232, 232)
        result = zxingcpp.read_barcode(qimage_to_zxing_buffer(image), formats=zxingcpp.BarcodeFormat.QRCode)
        self.assertEqual(getattr(result, "text", ""), "general-qr")

    def test_task_scope_falls_back_to_general(self) -> None:
        parent = _ParentWindow()
        key, label = task_scope_from_window(parent)
        self.assertEqual(key, "__general__")
        self.assertEqual(label, "General")

    def test_reminder_summary_reports_counts(self) -> None:
        parent = _ParentWindow()
        parent.reminders_store.add("Test", "note", datetime.now(), "", "daily")
        summary = summarize_reminders(parent.reminders_store)
        self.assertIn("1 reminders", summary)

    def test_tool_dialogs_expose_accessible_names(self) -> None:
        parent = _ParentWindow()
        dialogs = [
            RandomNumberToolDialog(parent),
            PasswordToolDialog(parent),
            FinanceToolDialog(parent),
            ScientificCalculatorToolDialog(parent),
            UnitConverterToolDialog(parent),
            TimerToolDialog(parent),
            ColorPickerToolDialog(parent),
            WorldClockToolDialog(parent),
            EquationSolverToolDialog(parent),
            CurrencyToolDialog(parent),
            GraphViewerToolDialog(parent),
            RemindersToolDialog(parent),
            TaskersToolDialog(parent),
            ReaderModeToolDialog(parent),
            AnnotationsToolDialog(parent),
        ]
        for dialog in dialogs:
            self.assertTrue(dialog.accessibleName().endswith("dialog"))
            self.assertTrue(dialog.output.accessibleName())

    def test_built_in_tool_controller_creates_actions(self) -> None:
        parent = _ParentWindow()
        controller = BuiltInToolsController(parent)
        controller.create_actions()
        self.assertIn("random_number", controller.actions)
        self.assertEqual(controller.actions["random_number"].objectName(), "toolRandomNumberAction")
        self.assertIn("scientific_calculator", controller.actions)
        self.assertIn("unit_converter", controller.actions)
        self.assertIn("timer_stopwatch", controller.actions)
        self.assertIn("equation_solver", controller.actions)
        self.assertIn("graph_viewer", controller.actions)
        self.assertIn("currency_converter", controller.actions)
        self.assertIn("reminders_hub", controller.actions)
        self.assertIn("taskers", controller.actions)
        self.assertIn("reader_mode", controller.actions)
        self.assertIn("annotations_manager", controller.actions)
        self.assertIn("qr_tools", controller.actions)


if __name__ == "__main__":
    unittest.main()
