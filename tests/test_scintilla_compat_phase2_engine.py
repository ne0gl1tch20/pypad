import os
import random
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QKeyEvent
from PySide6.QtCore import Qt, QEvent

from pypad.ui.editor.scintilla_compat import ScintillaCompatEditor


class ScintillaCompatPhase2EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_notifications_modified_updateui_and_charadded(self) -> None:
        ed = ScintillaCompatEditor()
        events: list[dict] = []
        ed.scnNotify.connect(events.append)
        ed.setText("abc")
        ed.SendScintilla(ed.SCI_GOTOPOS, 3)
        ed.insertPlainText("d")
        self.assertTrue(any(e.get("code") == ed.SCN_MODIFIED for e in events))
        self.assertTrue(any(e.get("code") == ed.SCN_UPDATEUI for e in events))
        ed.SendScintilla(ed.SCI_GOTOPOS, 4)
        event = QKeyEvent(QEvent.KeyPress, Qt.Key_X, Qt.NoModifier, "x")
        ed.keyPressEvent(event)
        self.assertTrue(any(e.get("code") == ed.SCN_CHARADDED for e in events))

    def test_modified_payload_contract_contains_ranges_reasons_and_seq(self) -> None:
        ed = ScintillaCompatEditor()
        events: list[dict] = []
        ed.scnNotify.connect(events.append)
        ed.setText("abc")
        ed.SendScintilla(ed.SCI_INSERTTEXT, 3, 1, "z")
        modified = [e for e in events if e.get("code") == ed.SCN_MODIFIED]
        self.assertTrue(modified)
        payload = modified[-1]
        meta = dict(payload.get("metadata", {}) or {})
        self.assertIn("seq", meta)
        self.assertIn("reason_flags", meta)
        self.assertIn("tokenized_reasons", meta)
        self.assertIn("range_before", meta)
        self.assertIn("range_after", meta)
        self.assertIn("before_length", meta)
        self.assertIn("after_length", meta)
        self.assertEqual(payload.get("value"), ed.SC_MODTYPE_INSERT)

    def test_notification_mask_filters_emission(self) -> None:
        ed = ScintillaCompatEditor()
        events: list[dict] = []
        ed.scnNotify.connect(events.append)
        ed.SendScintilla(ed.SCI_SETMODEVENTMASK, ed.SC_MOD_UPDATEUI)
        ed.setText("abc")
        self.assertFalse(any(e.get("code") == ed.SCN_MODIFIED for e in events))
        ed.SendScintilla(ed.SCI_GOTOPOS, 1)
        self.assertTrue(any(e.get("code") == ed.SCN_UPDATEUI for e in events))

    def test_engine_snapshot_import_and_diff_roundtrip(self) -> None:
        ed = ScintillaCompatEditor()
        ed.SendScintilla(ed.SCI_SETENGINEVAR, 10, 99)
        ed.SendScintilla(ed.SCI_SETENGINETOGGLE, 2, 1)
        holder: dict[str, str] = {}
        snap_len = ed.SendScintilla(ed.SCI_ENGINESTATESNAPSHOT, holder)
        self.assertGreater(snap_len, 10)
        snap = holder.get("text", "")
        ed.SendScintilla(ed.SCI_SETENGINEVAR, 10, 123)
        diff_holder: dict[str, str] = {}
        diff_len = ed.SendScintilla(ed.SCI_ENGINESTATEDIFF, snap_len, snap, diff_holder)
        self.assertGreater(diff_len, 2)
        self.assertIn("variables", diff_holder.get("text", ""))
        self.assertEqual(ed.SendScintilla(ed.SCI_ENGINESTATEIMPORT, snap_len, snap), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETENGINEVAR, 10), 99)

    def test_multi_selection_fidelity_selection_boundaries(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta gamma")
        ed.SendScintilla(ed.SCI_SETSELECTIONNSTART, 0, 0)
        ed.SendScintilla(ed.SCI_SETSELECTIONNEND, 0, 5)
        ed.SendScintilla(ed.SCI_ADDSELECTION, 10, 6)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONS), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONNSTART, 0), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONNEND, 0), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONNSTART, 1), 6)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONNEND, 1), 10)
        ed.SendScintilla(ed.SCI_DROPSELECTIONN, 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONS), 1)

    def test_extended_scintilla_coverage_calltip_autoc_marker_annotation_indicator_foldflags(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("one two")
        self.assertEqual(ed.SendScintilla(ed.SCI_CALLTIPSHOW, 3, "tip"), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_CALLTIPACTIVE), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_CALLTIPCANCEL), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_CALLTIPACTIVE), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_AUTOCSETSEPARATOR, ord("|")), ord("|"))
        self.assertEqual(ed.SendScintilla(ed.SCI_AUTOCGETSEPARATOR), ord("|"))
        self.assertEqual(ed.SendScintilla(ed.SCI_AUTOCSHOW, 0, "one|two"), 1)
        self.assertIn(ed.SendScintilla(ed.SCI_AUTOCACTIVE), (0, 1))
        self.assertEqual(ed.SendScintilla(ed.SCI_AUTOCCANCEL), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_ANNOTATIONSETTEXT, 0, "note"), 1)
        h: dict[str, str] = {}
        self.assertEqual(ed.SendScintilla(ed.SCI_ANNOTATIONGETTEXT, 0, h), 4)
        self.assertEqual(h.get("text"), "note")
        self.assertEqual(ed.SendScintilla(ed.SCI_ANNOTATIONCLEARALL), 1)
        marker_id = ed.SendScintilla(ed.SCI_MARKERDEFINE, ed.Circle)
        self.assertGreaterEqual(marker_id, 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_MARKERADD, 0, marker_id), marker_id)
        self.assertEqual(ed.SendScintilla(ed.SCI_MARKERSETBACK, marker_id, 0x112233), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETFOLDFLAGS, 5), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETFOLDFLAGS), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_INDICSETSTYLE, 4, ed.INDIC_SQUIGGLE), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_INDICSETFORE, 4, 0x223344), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_INDICGETSTYLE, 4), ed.INDIC_SQUIGGLE)
        self.assertEqual(ed.SendScintilla(ed.SCI_INDICGETFORE, 4), 0x223344)

    def test_calltip_and_autocomplete_cancellation_semantics(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta")
        ed.SendScintilla(ed.SCI_CALLTIPSHOW, 5, "tip")
        self.assertEqual(ed.SendScintilla(ed.SCI_CALLTIPACTIVE), 1)
        ed.SendScintilla(ed.SCI_GOTOPOS, 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_CALLTIPACTIVE), 0)
        ed.SendScintilla(ed.SCI_SETAUTOCANCELATSTART, 1)
        ed.SendScintilla(ed.SCI_GOTOPOS, 5)
        ed.SendScintilla(ed.SCI_AUTOCSHOW, 0, "alpha beta")
        self.assertIn(ed.SendScintilla(ed.SCI_AUTOCACTIVE), (0, 1))
        ed.SendScintilla(ed.SCI_GOTOPOS, 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_AUTOCACTIVE), 0)

    def test_selection_caret_anchor_virtual_space_and_notification_log(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("abcdef")
        ed.SendScintilla(ed.SCI_ADDSELECTION, 5, 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONNCARET, 1), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONNANCHOR, 1), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSELECTIONNCARETVIRTUALSPACE, 1, 3), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSELECTIONNANCHORVIRTUALSPACE, 1, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONNCARETVIRTUALSPACE, 1), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONNANCHORVIRTUALSPACE, 1), 1)
        holder: dict[str, str] = {}
        self.assertGreaterEqual(ed.SendScintilla(ed.SCI_GETLASTNOTIFICATION, holder), 0)
        self.assertIn("code", holder.get("text", "{}"))
        cleared = ed.SendScintilla(ed.SCI_CLEARNOTIFICATIONS)
        self.assertGreaterEqual(cleared, 0)

    def test_undo_grouping_and_change_history_path(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("abc")
        ed.SendScintilla(ed.SCI_BEGINUNDOACTION)
        ed.SendScintilla(ed.SCI_INSERTTEXT, 3, 1, "x")
        ed.SendScintilla(ed.SCI_INSERTTEXT, 4, 1, "y")
        ed.SendScintilla(ed.SCI_ENDUNDOACTION)
        self.assertEqual(ed.text(), "abcxy")
        self.assertEqual(ed.SendScintilla(ed.SCI_CANUNDO), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_UNDO), 1)
        self.assertEqual(ed.text(), "abc")
        self.assertEqual(ed.SendScintilla(ed.SCI_REDO), 1)
        self.assertEqual(ed.text(), "abcxy")

    def test_posix_search_word_constraints(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("aa_a aa")
        n = ed.SendScintilla(ed.SCI_GETLENGTH)
        ed.SendScintilla(ed.SCI_SETTARGETSTART, 0)
        ed.SendScintilla(ed.SCI_SETTARGETEND, n)
        ed.SendScintilla(ed.SCI_SETSEARCHFLAGS, ed.SCFIND_WHOLEWORD)
        self.assertEqual(ed.SendScintilla(ed.SCI_SEARCHINTARGET, 2, "aa"), 5)
        ed.SendScintilla(ed.SCI_SETTARGETSTART, 0)
        ed.SendScintilla(ed.SCI_SETTARGETEND, n)
        ed.SendScintilla(ed.SCI_SETSEARCHFLAGS, ed.SCFIND_WHOLEWORD | ed.SCFIND_POSIX)
        self.assertEqual(ed.SendScintilla(ed.SCI_SEARCHINTARGET, 2, "aa"), 0)

    def test_fold_display_text_and_autoc_fillups_apis(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("one\ntwo\n")
        self.assertEqual(ed.SendScintilla(ed.SCI_FOLDSETTEXT, 0, "..."), 3)
        h: dict[str, str] = {}
        self.assertEqual(ed.SendScintilla(ed.SCI_FOLDGETTEXT, 0, h), 3)
        self.assertEqual(h.get("text"), "...")
        self.assertEqual(ed.SendScintilla(ed.SCI_AUTOCSETFILLUPS, ";."), 2)
        h2: dict[str, str] = {}
        self.assertEqual(ed.SendScintilla(ed.SCI_AUTOCGETFILLUPS, h2), 2)
        self.assertEqual(h2.get("text"), ";.")

    def test_stress_fuzz_random_command_sequences_invariants(self) -> None:
        ed = ScintillaCompatEditor()
        rng = random.Random(1337)
        ed.setText("seed text")
        for _ in range(250):
            op = rng.randint(0, 9)
            if op == 0:
                pos = rng.randint(0, len(ed.text()))
                ed.SendScintilla(ed.SCI_GOTOPOS, pos)
            elif op == 1:
                s = rng.randint(0, len(ed.text()))
                e = rng.randint(0, len(ed.text()))
                ed.SendScintilla(ed.SCI_SETSEL, s, e)
            elif op == 2:
                ed.SendScintilla(ed.SCI_SETENGINEVAR, rng.randint(0, 511), rng.randint(0, 100000))
            elif op == 3:
                ed.SendScintilla(ed.SCI_SETENGINECHANNEL, rng.randint(0, 63), rng.randint(0, 100000))
            elif op == 4:
                ed.SendScintilla(ed.SCI_SETENGINETOGGLE, rng.randint(0, 127), rng.randint(0, 1))
            elif op == 5:
                ed.SendScintilla(ed.SCI_SETSTYLEBITS, rng.randint(0, 12))
            elif op == 6:
                ed.SendScintilla(ed.SCI_SETTARGETSTART, rng.randint(0, len(ed.text())))
                ed.SendScintilla(ed.SCI_SETTARGETEND, rng.randint(0, len(ed.text())))
                ed.SendScintilla(ed.SCI_SEARCHINTARGET, 4, "text")
            elif op == 7:
                ed.SendScintilla(ed.SCI_SETFIRSTVISIBLELINE, rng.randint(0, 50))
            elif op == 8:
                ed.SendScintilla(ed.SCI_SETXOFFSET, rng.randint(0, 200))
            else:
                ed.SendScintilla(ed.SCI_SETMOUSEDWELLTIME, rng.randint(0, 5000))
            self.assertGreaterEqual(ed.SendScintilla(ed.SCI_GETSTYLEBITS), 1)
            self.assertLessEqual(ed.SendScintilla(ed.SCI_GETSTYLEBITS), 8)
            self.assertGreaterEqual(ed.SendScintilla(ed.SCI_GETENGINEGENERATION), 0)

    def test_golden_known_sequence_expectations(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("abc def")
        ed.SendScintilla(ed.SCI_SETSEL, 0, 3)
        ed.SendScintilla(ed.SCI_REPLACESEL, 1, "X")
        ed.SendScintilla(ed.SCI_APPENDTEXT, 4, " END")
        ed.SendScintilla(ed.SCI_SETENGINEVAR, 1, 42)
        ed.SendScintilla(ed.SCI_SETENGINETOGGLE, 1, 1)
        ed.SendScintilla(ed.SCI_SETENGINECHANNEL, 1, 99)
        self.assertEqual(ed.text(), "X def END")
        self.assertEqual(ed.SendScintilla(ed.SCI_GETENGINEVAR, 1), 42)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETENGINETOGGLE, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETENGINECHANNEL, 1), 99)


if __name__ == "__main__":
    unittest.main()
