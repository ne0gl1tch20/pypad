import os
import sys
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PySide6.QtCore import QPointF, Qt, QEvent
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication

from pypad.ui.editor.scintilla_compat import ScintillaCompatEditor, load_command_metadata
from pypad.ui.editor.scintilla_compat.models import FoldRegion


class _IncrementalLexer:
    language = "python"

    def lex_incremental(self, text: str, start: int, end: int, prev_state: int = 0):
        seg = text[start:end]
        ranges = []
        idx = seg.find("def")
        if idx >= 0:
            ranges.append((start + idx, start + idx + 3, 1))
        fold = {0: FoldRegion(start=0, end=max(0, len(text) - 1), level=0)}
        return ranges, fold, prev_state + 1


class ScintillaCompatContractExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_command_metadata_registry_contains_contract_information(self) -> None:
        metadata = load_command_metadata()
        self.assertEqual(metadata["SCI_SETENGINEVAR"].status, "compat-only")
        self.assertEqual(metadata["SCN_MODIFIED"].category, "notification")
        self.assertIn("seq", metadata["SCN_MODIFIED"].notes)

    def test_capabilities_and_future_shims_are_exposed(self) -> None:
        ed = ScintillaCompatEditor()
        caps = ed.get_capabilities()
        self.assertTrue(caps["serialization"])
        self.assertTrue(caps["future_shims"]["inline_diagnostics"])
        ed.set_minimap_enabled(True)
        ed.set_code_actions([{"title": "Fix"}])
        self.assertEqual(ed._engine_state.channels[62], 1)
        self.assertEqual(ed._engine_state.channels[63], 1)

    def test_notification_contract_and_log_snapshot(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("abc")
        ed.SendScintilla(ed.SCI_GOTOPOS, 3)
        ed.insertPlainText("d")
        contract = ed.get_notification_contract()
        self.assertIn("metadata_keys", contract[ed.SCN_MODIFIED])
        snapshot = ed.get_notification_log_snapshot()
        self.assertTrue(snapshot)
        self.assertIn("metadata", snapshot[-1])

    def test_margin_click_notification_metadata_distinguishes_sensitive_vs_fold(self) -> None:
        ed = ScintillaCompatEditor()
        ed.resize(800, 300)
        ed.setText("{\n  a\n}\n")
        ed._rebuild_fold_regions()
        ed.setMarginSensitivity(1, True)
        fold_evt = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(20, 5), QPointF(20, 5), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        ed.handle_margin_click(fold_evt)
        sensitive_evt = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(24, 25), QPointF(24, 25), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        ed.handle_margin_click(sensitive_evt)
        payloads = [item for item in ed.get_notification_log_snapshot() if item["code"] == ed.SCN_MARGINCLICK]
        self.assertTrue(any(item["metadata"].get("folded") == 1 for item in payloads))
        self.assertTrue(any(item["metadata"].get("sensitive") == 1 for item in payloads))

    def test_lexer_contract_snapshot_and_semantic_ranges(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("def f():\n    return 1\n")
        ed.setLexer(_IncrementalLexer())
        contract = ed.get_lexer_contract()
        snap = ed.get_lexer_snapshot()
        self.assertTrue(contract["incremental"])
        self.assertEqual(snap["language"], "python")
        self.assertTrue(snap["ranges"])
        ed.set_semantic_ranges([{"start": 0, "end": 3, "style": 5}])
        snap2 = ed.get_lexer_snapshot()
        self.assertIn((0, 3, 5), snap2["ranges"])

    def test_serialization_roundtrip_restores_editor_state(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha\nbeta\ngamma")
        ed.SendScintilla(ed.SCI_SETSELECTIONNSTART, 0, 0)
        ed.SendScintilla(ed.SCI_SETSELECTIONNEND, 0, 5)
        ed.SendScintilla(ed.SCI_ADDSELECTION, 10, 6)
        marker = ed.SendScintilla(ed.SCI_MARKERDEFINE, ed.Plus)
        ed.SendScintilla(ed.SCI_MARKERADD, 1, marker)
        ed.SendScintilla(ed.SCI_ANNOTATIONSETTEXT, 1, "note")
        ed.set_background_overlays("search", [(0, 5, "#ffee88")])
        ed.addHotspotRange(6, 10, "beta")
        ed.setIndicatorCurrent(1)
        ed.setIndicatorValue(7)
        ed.indicatorFillRange(0, 5)
        state = ed.export_compat_state()
        ed2 = ScintillaCompatEditor()
        self.assertEqual(ed2.import_compat_state(state), 1)
        self.assertEqual(ed2.toPlainText(), ed.toPlainText())
        self.assertEqual(len(ed2._selection_ranges), len(ed._selection_ranges))
        self.assertEqual(ed2._annotations[1], "note")
        self.assertTrue(ed2._background_overlays["search"])
        self.assertTrue(ed2._hotspot_ranges)
        self.assertTrue(ed2._indicator_ranges[1])

    def test_golden_behavior_selection_fold_undo_style_marker_search(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("{\n  alpha beta\n}\n")
        ed.SendScintilla(ed.SCI_SETSEL, 4, 9)
        ed.SendScintilla(ed.SCI_REPLACESEL, 1, "ALPHA")
        ed.SendScintilla(ed.SCI_BEGINUNDOACTION)
        ed.SendScintilla(ed.SCI_APPENDTEXT, 2, "!!")
        ed.SendScintilla(ed.SCI_ENDUNDOACTION)
        ed.SendScintilla(ed.SCI_STYLESETFORE, 42, 0x112233)
        ed.SendScintilla(ed.SCI_STARTSTYLING, 0)
        ed.SendScintilla(ed.SCI_SETSTYLING, 3, 42)
        marker = ed.SendScintilla(ed.SCI_MARKERDEFINE, ed.Circle)
        ed.SendScintilla(ed.SCI_MARKERADD, 0, marker)
        ed.SendScintilla(ed.SCI_FOLDLINE, 0, ed.SC_FOLDACTION_CONTRACT)
        ed.SendScintilla(ed.SCI_SETTARGETSTART, 0)
        ed.SendScintilla(ed.SCI_SETTARGETEND, ed.SendScintilla(ed.SCI_GETLENGTH))
        hit = ed.SendScintilla(ed.SCI_SEARCHINTARGET, 4, "beta")
        self.assertGreaterEqual(hit, 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_UNDO), 1)
        self.assertIn("A beta", ed.text())
        self.assertIn(0, ed._markers[marker])
        self.assertTrue(any(style == 42 for _, _, style in ed._style_ranges))

    def test_inline_diagnostics_overlay_channel_is_available(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("problem")
        ed.set_inline_diagnostics([{"start": 0, "end": 7, "color": "#ffaaaa"}])
        self.assertIn("inline_diagnostics", ed._background_overlays)

    def test_large_file_operations_stay_within_reasonable_budget(self) -> None:
        ed = ScintillaCompatEditor()
        text = ("alpha beta gamma delta\n" * 4000).strip()
        started = time.perf_counter()
        ed.setText(text)
        ed.SendScintilla(ed.SCI_SETTARGETSTART, 0)
        ed.SendScintilla(ed.SCI_SETTARGETEND, ed.SendScintilla(ed.SCI_GETLENGTH))
        ed.SendScintilla(ed.SCI_SEARCHINTARGET, 5, "gamma")
        ed.set_background_overlays("perf", [(0, 100, "#ffee88"), (200, 400, "#88ddff")])
        ed._refresh_extra_selections()
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 3.0)
