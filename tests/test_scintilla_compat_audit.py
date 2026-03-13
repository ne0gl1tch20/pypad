import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypad.ui.editor.scintilla_compat.audit import (
    build_audit_report,
    load_contract_baseline,
    load_native_baseline,
)


class ScintillaCompatAuditTests(unittest.TestCase):
    def test_repo_symbol_surface_is_fully_covered(self) -> None:
        report = build_audit_report(ROOT)
        self.assertEqual(report.repo_missing, ())

    def test_app_exclusive_engine_commands_are_tracked(self) -> None:
        report = build_audit_report(ROOT)
        self.assertIn("SCI_SETENGINEVAR", report.app_exclusive_symbols)
        self.assertIn("SCI_ENGINESTATESNAPSHOT", report.app_exclusive_symbols)
        self.assertIn("SCI_ENGINESTATEDIFF", report.app_exclusive_symbols)

    def test_native_gap_list_is_empty_when_native_qsci_is_unavailable(self) -> None:
        report = build_audit_report(ROOT)
        if not report.native_symbols:
            self.assertEqual(report.native_missing, ())

    def test_contract_baseline_matches_when_present(self) -> None:
        baseline = load_contract_baseline(ROOT)
        if baseline is None:
            self.skipTest("Compat contract baseline file is not present.")
        report = build_audit_report(ROOT)
        self.assertEqual(tuple(sorted(report.compat_symbols)), baseline.compat_symbols)
        self.assertEqual(tuple(sorted(report.app_exclusive_symbols)), tuple(sorted(baseline.app_exclusive_symbols)))

    def test_native_baseline_matches_when_present(self) -> None:
        baseline = load_native_baseline(ROOT)
        if baseline is None:
            self.skipTest("Native Qsci baseline file is not present.")
        report = build_audit_report(ROOT)
        if not report.native_symbols:
            self.skipTest("PySide6.Qsci is not available in this environment.")
        self.assertEqual(tuple(sorted(report.native_symbols)), baseline.symbols)


if __name__ == "__main__":
    unittest.main()
