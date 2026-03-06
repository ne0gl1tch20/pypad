import os
import sys
import unittest
from pathlib import Path
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from pypad.ui.editor.scintilla_compat import ScintillaCompatEditor


class ScintillaCompatPhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _rgb_int(hex_color: str) -> int:
        c = QColor(hex_color)
        return int(c.red()) | (int(c.green()) << 8) | (int(c.blue()) << 16)

    @staticmethod
    def _compat_command_args_map(ed: ScintillaCompatEditor) -> dict[str, tuple[int, ...]]:
        color = int(ScintillaCompatPhase1Tests._rgb_int("#223344"))
        return {
            "SCI_SETMARGINLEFT": (8,),
            "SCI_SETMARGINRIGHT": (4,),
            "SCI_SETCARETWIDTH": (2,),
            "SCI_SETCARETLINEVISIBLE": (1,),
            "SCI_SETCARETLINEBACK": (color,),
            "SCI_STYLESETFORE": (32, color),
            "SCI_STYLESETBACK": (32, color),
            "SCI_STYLECLEARALL": (),
            "SCI_SETSELBACK": (1, color),
            "SCI_SETSELFORE": (1, color),
            "SCI_SETSELECTIONMODE": (ed.SC_SEL_RECTANGLE,),
            "SCI_SETMULTIPLESELECTION": (1,),
            "SCI_SETADDITIONALSELECTIONTYPING": (1,),
            "SCI_SETMULTIPASTE": (1,),
            "SCI_SETVIEWWS": (1,),
            "SCI_SETVIEWEOL": (1,),
            "SCI_SETCONTROLCHARSYMBOL": (183,),
            "SCI_SETINDENTATIONGUIDES": (1,),
            "SCI_SETWRAPVISUALFLAGS": (1,),
            "SCI_FOLDALL": (1,),
            "SCI_FOLDLINE": (0, 1),
            "SCI_HIDELINES": (1, 2),
            "SCI_SHOWLINES": (1, 2),
        }

    def test_showlines_only_unhides_requested_range(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("a\nb\nc\nd\ne\n")
        self.assertTrue(ed.send_scintilla_named("SCI_HIDELINES", 1, 3))
        self.assertIn(1, ed._hidden_lines)
        self.assertIn(2, ed._hidden_lines)
        self.assertIn(3, ed._hidden_lines)
        self.assertTrue(ed.send_scintilla_named("SCI_SHOWLINES", 2, 2))
        self.assertIn(1, ed._hidden_lines)
        self.assertNotIn(2, ed._hidden_lines)
        self.assertIn(3, ed._hidden_lines)

    def test_stylesetback_and_styleclearall_commands(self) -> None:
        ed = ScintillaCompatEditor()
        style_id = 33
        self.assertTrue(ed.send_scintilla_named("SCI_STYLESETBACK", style_id, self._rgb_int("#112233")))
        self.assertIn(style_id, ed._style_formats)
        back = ed._style_formats[style_id].background().color()
        self.assertEqual(back.name(), QColor("#112233").name())
        ed.startStyling(0)
        ed.setStyling(3, style_id)
        self.assertTrue(ed._style_ranges)
        self.assertTrue(ed.send_scintilla_named("SCI_STYLECLEARALL"))
        self.assertEqual(ed._style_formats, {})
        self.assertEqual(ed._style_ranges, [])

    def test_sel_and_caret_line_color_commands(self) -> None:
        ed = ScintillaCompatEditor()
        self.assertTrue(ed.send_scintilla_named("SCI_SETSELBACK", 1, self._rgb_int("#224466")))
        self.assertTrue(ed.send_scintilla_named("SCI_SETSELFORE", 1, self._rgb_int("#ddeeff")))
        self.assertTrue(ed.send_scintilla_named("SCI_SETCARETLINEBACK", self._rgb_int("#102030")))
        pal = ed.palette()
        self.assertEqual(pal.color(QPalette.Highlight).name(), QColor("#224466").name())
        self.assertEqual(pal.color(QPalette.HighlightedText).name(), QColor("#ddeeff").name())
        self.assertEqual(ed._caret_line_color.name(), QColor("#102030").name())

    def test_background_overlay_channels_coexist_and_clear(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta gamma")
        ed.set_background_overlays("search", [(0, 5, QColor("#f7e36d"))])
        ed.set_background_overlays("line_styles", [(6, 10, QColor("#99ccff"))])
        self.assertEqual(len(ed._background_overlays.get("search", [])), 1)
        self.assertEqual(len(ed._background_overlays.get("line_styles", [])), 1)
        ed.clear_background_overlays("search")
        self.assertEqual(len(ed._background_overlays.get("search", [])), 0)
        self.assertEqual(len(ed._background_overlays.get("line_styles", [])), 1)

    def test_send_scintilla_numeric_bridge_core_messages(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("a\n{\n  b\n}\nc\n")
        self.assertGreaterEqual(ed.SendScintilla(ed.SCI_GETLINECOUNT), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_LINEFROMPOSITION, 0), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_LINEFROMPOSITION, 2), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETLINEVISIBLE, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_HIDELINES, 1, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETLINEVISIBLE, 1), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_SHOWLINES, 1, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETLINEVISIBLE, 1), 1)
        fold_level = int(ed.SendScintilla(ed.SCI_GETFOLDLEVEL, 1))
        self.assertGreaterEqual(fold_level & int(ed.SC_FOLDLEVELNUMBERMASK), 0)

    def test_send_scintilla_numeric_bridge_style_indicator_and_selection(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta")
        color = self._rgb_int("#224466")
        self.assertEqual(ed.SendScintilla(ed.SCI_STYLESETFORE, 32, color), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_STYLESETBACK, 32, color), 1)
        self.assertIn(32, ed._style_formats)
        self.assertEqual(ed.SendScintilla(ed.SCI_STARTSTYLING, 0), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSTYLING, 5, 32), 1)
        self.assertTrue(ed._style_ranges)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETINDICATORCURRENT, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETINDICATORVALUE, 7), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_INDICSETSTYLE, 1, ed.INDIC_SQUIGGLE), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_INDICSETFORE, 1, color), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_INDICATORFILLRANGE, 0, 5), 1)
        self.assertTrue(ed._indicator_ranges.get(1))
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSELBACK, 1, color), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSELFORE, 1, color), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSELECTIONMODE, ed.SC_SEL_RECTANGLE), 1)
        self.assertTrue(ed._column_mode)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETMULTIPLESELECTION, 1), 1)
        self.assertTrue(ed._multiple_selection_enabled)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETADDITIONALSELECTIONTYPING, 1), 1)
        self.assertTrue(ed._additional_selection_typing)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETMULTIPASTE, 1), 1)
        self.assertTrue(ed._multi_paste)
        self.assertEqual(ed.SendScintilla(ed.SCI_STYLECLEARALL), 1)
        self.assertEqual(ed._style_formats, {})

    def test_send_scintilla_numeric_getters_selection_cursor_text_range(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta\ngamma")
        ed.setSelection(0, 2, 0, 7)
        cur = ed.textCursor()
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCURRENTPOS), int(cur.position()))
        self.assertEqual(ed.SendScintilla(ed.SCI_GETANCHOR), int(cur.anchor()))
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONSTART), min(cur.selectionStart(), cur.selectionEnd()))
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONEND), max(cur.selectionStart(), cur.selectionEnd()))
        self.assertEqual(ed.SendScintilla(ed.SCI_GETTEXTRANGE, 0, 5), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETTEXTRANGE, 3, 3), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETLENGTH), len("alpha beta\ngamma"))

    def test_send_scintilla_text_buffer_emulation(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta\ngamma")
        holder: dict[str, str] = {}
        self.assertEqual(ed.SendScintilla(ed.SCI_GETTEXTRANGE, 0, 5, holder), 5)
        self.assertEqual(holder.get("text"), "alpha")
        lst: list[str] = []
        self.assertEqual(ed.SendScintilla(ed.SCI_GETTEXTRANGE, 6, 10, lst), 4)
        self.assertEqual(lst, ["beta"])
        buf = bytearray(6)
        copied = ed.SendScintilla(ed.SCI_GETTEXT, 6, buf)
        self.assertEqual(copied, 5)
        self.assertEqual(bytes(buf[:5]).decode("utf-8"), "alpha")
        self.assertEqual(buf[5], 0)

    def test_send_scintilla_target_search_and_replace(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("zero alpha beta alpha end")
        self.assertEqual(ed.SendScintilla(ed.SCI_SETTARGETSTART, 0), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETTARGETEND, ed.SendScintilla(ed.SCI_GETLENGTH)), ed.SendScintilla(ed.SCI_GETLENGTH))
        hit = ed.SendScintilla(ed.SCI_SEARCHINTARGET, 5, "alpha")
        self.assertGreaterEqual(hit, 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETTARGETSTART), hit)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETTARGETEND), hit + 5)
        replaced = ed.SendScintilla(ed.SCI_REPLACETARGET, 1, "A")
        self.assertEqual(replaced, 1)
        self.assertIn("A beta alpha", ed.text())
        self.assertEqual(ed.SendScintilla(ed.SCI_SETTARGETSTART, ed.SendScintilla(ed.SCI_GETTARGETEND)), ed.SendScintilla(ed.SCI_GETTARGETEND))
        self.assertEqual(ed.SendScintilla(ed.SCI_SETTARGETEND, ed.SendScintilla(ed.SCI_GETLENGTH)), ed.SendScintilla(ed.SCI_GETLENGTH))
        hit2 = ed.SendScintilla(ed.SCI_SEARCHINTARGET, 5, {"text": "alpha"})
        self.assertGreaterEqual(hit2, 0)

    def test_send_scintilla_search_flags_case_and_whole_word(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("Alpha ALPHABET ALPHA alpha")
        text_len = ed.SendScintilla(ed.SCI_GETLENGTH)
        ed.SendScintilla(ed.SCI_SETTARGETSTART, 0)
        ed.SendScintilla(ed.SCI_SETTARGETEND, text_len)
        ed.SendScintilla(ed.SCI_SETSEARCHFLAGS, 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSEARCHFLAGS), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_SEARCHINTARGET, 5, "alpha"), 0)
        ed.SendScintilla(ed.SCI_SETTARGETSTART, 0)
        ed.SendScintilla(ed.SCI_SETTARGETEND, text_len)
        ed.SendScintilla(ed.SCI_SETSEARCHFLAGS, ed.SCFIND_MATCHCASE)
        self.assertEqual(ed.SendScintilla(ed.SCI_SEARCHINTARGET, 5, "alpha"), 21)
        ed.SendScintilla(ed.SCI_SETTARGETSTART, 0)
        ed.SendScintilla(ed.SCI_SETTARGETEND, text_len)
        ed.SendScintilla(ed.SCI_SETSEARCHFLAGS, ed.SCFIND_WHOLEWORD)
        self.assertEqual(ed.SendScintilla(ed.SCI_SEARCHINTARGET, 5, "alpha"), 0)
        ed.SendScintilla(ed.SCI_SETTARGETSTART, 0)
        ed.SendScintilla(ed.SCI_SETTARGETEND, text_len)
        ed.SendScintilla(ed.SCI_SETSEARCHFLAGS, ed.SCFIND_MATCHCASE | ed.SCFIND_WHOLEWORD)
        self.assertEqual(ed.SendScintilla(ed.SCI_SEARCHINTARGET, 5, "alpha"), 21)

    def test_send_scintilla_search_in_target_reverse_direction(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("aa bb aa cc aa")
        text_len = ed.SendScintilla(ed.SCI_GETLENGTH)
        ed.SendScintilla(ed.SCI_SETSEARCHFLAGS, 0)
        ed.SendScintilla(ed.SCI_SETTARGETSTART, text_len)
        ed.SendScintilla(ed.SCI_SETTARGETEND, 0)
        hit = ed.SendScintilla(ed.SCI_SEARCHINTARGET, 2, "aa")
        self.assertEqual(hit, 12)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETTARGETSTART), 12)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETTARGETEND), 14)
        ed.SendScintilla(ed.SCI_SETTARGETSTART, hit)
        ed.SendScintilla(ed.SCI_SETTARGETEND, 0)
        hit2 = ed.SendScintilla(ed.SCI_SEARCHINTARGET, 2, "aa")
        self.assertEqual(hit2, 6)

    def test_send_scintilla_regex_search_and_replace_target_re(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("name=alice; name=bob;")
        text_len = ed.SendScintilla(ed.SCI_GETLENGTH)
        ed.SendScintilla(ed.SCI_SETTARGETSTART, 0)
        ed.SendScintilla(ed.SCI_SETTARGETEND, text_len)
        ed.SendScintilla(ed.SCI_SETSEARCHFLAGS, ed.SCFIND_REGEXP)
        hit = ed.SendScintilla(ed.SCI_SEARCHINTARGET, len(r"name=(\w+)"), r"name=(\w+)")
        self.assertEqual(hit, 0)
        replaced = ed.SendScintilla(ed.SCI_REPLACETARGETRE, len(r"user=\1"), r"user=\1")
        self.assertEqual(replaced, len("user=alice"))
        self.assertTrue(ed.text().startswith("user=alice;"))

    def test_send_scintilla_search_flags_word_start_plain_and_regex(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("xalpha alpha _alpha alpha2")
        n = ed.SendScintilla(ed.SCI_GETLENGTH)
        ed.SendScintilla(ed.SCI_SETTARGETSTART, 0)
        ed.SendScintilla(ed.SCI_SETTARGETEND, n)
        ed.SendScintilla(ed.SCI_SETSEARCHFLAGS, ed.SCFIND_WORDSTART)
        self.assertEqual(ed.SendScintilla(ed.SCI_SEARCHINTARGET, 5, "alpha"), 7)
        ed.SendScintilla(ed.SCI_SETTARGETSTART, 0)
        ed.SendScintilla(ed.SCI_SETTARGETEND, n)
        ed.SendScintilla(ed.SCI_SETSEARCHFLAGS, ed.SCFIND_WORDSTART | ed.SCFIND_REGEXP)
        self.assertEqual(ed.SendScintilla(ed.SCI_SEARCHINTARGET, len(r"alpha\d?"), r"alpha\d?"), 7)

    def test_send_scintilla_get_target_text(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("zero alpha beta")
        ed.SendScintilla(ed.SCI_SETTARGETSTART, 5)
        ed.SendScintilla(ed.SCI_SETTARGETEND, 10)
        holder: dict[str, str] = {}
        self.assertEqual(ed.SendScintilla(ed.SCI_GETTARGETTEXT, holder), 5)
        self.assertEqual(holder.get("text"), "alpha")
        lst: list[str] = []
        self.assertEqual(ed.SendScintilla(ed.SCI_GETTARGETTEXT, lst), 5)
        self.assertEqual(lst, ["alpha"])
        buf = bytearray(8)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETTARGETTEXT, buf), 5)
        self.assertEqual(bytes(buf[:5]).decode("utf-8"), "alpha")

    def test_send_scintilla_replace_target_minimal(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("prefix alpha suffix")
        start = ed.text().index("alpha")
        end = start + len("alpha")
        ed.SendScintilla(ed.SCI_SETTARGETSTART, start)
        ed.SendScintilla(ed.SCI_SETTARGETEND, end)
        replaced = ed.SendScintilla(ed.SCI_REPLACETARGETMINIMAL, len("alpXa"), "alpXa")
        self.assertEqual(replaced, 1)
        self.assertEqual(ed.text(), "prefix alpXa suffix")
        ed.SendScintilla(ed.SCI_SETTARGETSTART, start)
        ed.SendScintilla(ed.SCI_SETTARGETEND, start + len("alpXa"))
        replaced2 = ed.SendScintilla(ed.SCI_REPLACETARGETMINIMAL, len("alpXa"), "alpXa")
        self.assertEqual(replaced2, 0)
        self.assertEqual(ed.text(), "prefix alpXa suffix")

    def test_send_scintilla_style_bits_set_get(self) -> None:
        ed = ScintillaCompatEditor()
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSTYLEBITS), 8)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSTYLEBITS, 5), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSTYLEBITS), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSTYLEBITS, 99), 8)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSTYLEBITS, 0), 1)

    def test_send_scintilla_line_position_apis(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("one\ntwo\nthree")
        self.assertEqual(ed.SendScintilla(ed.SCI_POSITIONFROMLINE, 0), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_POSITIONFROMLINE, 1), 4)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETLINEENDPOSITION, 0), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETLINEENDPOSITION, 1), 7)

    def test_send_scintilla_line_length_char_and_style_at(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("abc\ndef")
        self.assertEqual(ed.SendScintilla(ed.SCI_LINELENGTH, 0), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_LINELENGTH, 1), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCHARAT, 0), ord("a"))
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCHARAT, 3), ord("\n"))
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSTYLEAT, 1), 0)
        ed.SendScintilla(ed.SCI_STYLESETFORE, 42, self._rgb_int("#123456"))
        ed.SendScintilla(ed.SCI_STARTSTYLING, 0)
        ed.SendScintilla(ed.SCI_SETSTYLING, 2, 42)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSTYLEAT, 0), 42)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSTYLEAT, 1), 42)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSTYLEAT, 2), 0)

    def test_send_scintilla_selection_mode_and_multiselect_getters(self) -> None:
        ed = ScintillaCompatEditor()
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONMODE), ed.SC_SEL_STREAM)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMULTIPLESELECTION), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETADDITIONALSELECTIONTYPING), 0)
        ed.SendScintilla(ed.SCI_SETSELECTIONMODE, ed.SC_SEL_RECTANGLE)
        ed.SendScintilla(ed.SCI_SETMULTIPLESELECTION, 1)
        ed.SendScintilla(ed.SCI_SETADDITIONALSELECTIONTYPING, 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONMODE), ed.SC_SEL_RECTANGLE)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMULTIPLESELECTION), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETADDITIONALSELECTIONTYPING), 1)

    def test_send_scintilla_fold_parent_and_last_child_getters(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("{\n  {\n    x\n  }\n}\n")
        parent_line_2 = ed.SendScintilla(ed.SCI_GETFOLDPARENT, 2)
        self.assertEqual(parent_line_2, 1)
        parent_line_4 = ed.SendScintilla(ed.SCI_GETFOLDPARENT, 4)
        self.assertEqual(parent_line_4, 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETFOLDPARENT, 0), -1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETLASTCHILD, 0, 0), 4)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETLASTCHILD, 1, 1), 3)

    def test_send_scintilla_brace_match_and_readback(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("a(b[c]d)e")
        self.assertEqual(ed.SendScintilla(ed.SCI_BRACEMATCH, 1), 7)
        self.assertEqual(ed.SendScintilla(ed.SCI_BRACEMATCH, 3), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_BRACEMATCH, 0), -1)
        ed.send_scintilla_named("SCI_BRACEHIGHLIGHT", 1, 7)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETBRACEHIGHLIGHT, 0), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETBRACEHIGHLIGHT, 1), 7)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETBRACEBADLIGHT), -1)
        ed.send_scintilla_named("SCI_BRACEBADLIGHT", 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETBRACEBADLIGHT), 3)

    def test_send_scintilla_get_column_and_curline(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("one\ntwo\nthree")
        ed.setCursorPosition(1, 2)
        pos = ed.textCursor().position()
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCOLUMN, pos), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCURLINE), len("two\n"))
        buf = bytearray(8)
        copied = ed.SendScintilla(ed.SCI_GETCURLINE, 8, buf)
        self.assertEqual(copied, 4)
        self.assertEqual(bytes(buf[:4]).decode("utf-8"), "two\n")

    def test_send_scintilla_main_selection_and_count_getters(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta gamma")
        ed.setSelection(0, 6, 0, 10)  # beta
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMAINSELECTION), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMAINSELSTART), 6)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMAINSELEND), 10)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONS), 1)
        ed.setMultipleSelectionEnabled(True)
        ed._additional_carets = [1, 3]
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONS), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONNSTART, 0), 6)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONNEND, 0), 10)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONNSTART, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONNEND, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONNSTART, 2), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONNEND, 2), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETMAINSELECTION, 2), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMAINSELECTION), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMAINSELSTART), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMAINSELEND), 3)

    def test_send_scintilla_selection_n_setters(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta gamma")
        ed.setSelection(0, 6, 0, 10)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSELECTIONNSTART, 0, 5), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSELECTIONNEND, 0, 9), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMAINSELSTART), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMAINSELEND), 9)
        ed.setMultipleSelectionEnabled(True)
        ed._additional_carets = [1]
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSELECTIONNSTART, 1, 4), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONNSTART, 1), 4)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSELECTIONNEND, 1, 7), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONNEND, 1), 7)

    def test_send_scintilla_add_selection(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta gamma")
        ed.setSelection(0, 0, 0, 5)
        before = ed.SendScintilla(ed.SCI_GETSELECTIONS)
        self.assertEqual(ed.SendScintilla(ed.SCI_ADDSELECTION, 9, 9), 1)
        after = ed.SendScintilla(ed.SCI_GETSELECTIONS)
        self.assertEqual(after, before + 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONNSTART, 1), 9)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONNEND, 1), 9)

    def test_send_scintilla_drop_and_clear_selections(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta gamma")
        ed.setSelection(0, 0, 0, 5)
        ed.SendScintilla(ed.SCI_ADDSELECTION, 7, 7)
        ed.SendScintilla(ed.SCI_ADDSELECTION, 12, 12)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONS), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_DROPSELECTIONN, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONS), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_CLEARSELECTIONS), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONS), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMULTIPLESELECTION), 0)

    def test_send_scintilla_rotate_selection(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta gamma")
        ed.setSelection(0, 0, 0, 5)
        ed.setMultipleSelectionEnabled(True)
        ed._additional_carets = [7, 12]
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMAINSELECTION), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_ROTATESELECTION), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMAINSELECTION), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_ROTATESELECTION), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMAINSELECTION), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_ROTATESELECTION), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMAINSELECTION), 0)

    def test_send_scintilla_swap_main_anchor_caret(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta gamma")
        ed.setSelection(0, 6, 0, 10)
        pos_before = ed.SendScintilla(ed.SCI_GETCURRENTPOS)
        anc_before = ed.SendScintilla(ed.SCI_GETANCHOR)
        self.assertNotEqual(pos_before, anc_before)
        self.assertEqual(ed.SendScintilla(ed.SCI_SWAPMAINANCHORCARET), 1)
        pos_after = ed.SendScintilla(ed.SCI_GETCURRENTPOS)
        anc_after = ed.SendScintilla(ed.SCI_GETANCHOR)
        self.assertEqual(pos_after, anc_before)
        self.assertEqual(anc_after, pos_before)

    def test_send_scintilla_marker_get_next_previous(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("a\nb\nc\nd\ne\n")
        ed.markerAdd(1, 2)
        ed.markerAdd(3, 4)
        self.assertEqual(ed.SendScintilla(ed.SCI_MARKERGET, 1), 1 << 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_MARKERGET, 2), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_MARKERNEXT, 0, (1 << 2)), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_MARKERNEXT, 2, (1 << 2)), -1)
        self.assertEqual(ed.SendScintilla(ed.SCI_MARKERPREVIOUS, 4, (1 << 4)), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_MARKERPREVIOUS, 2, (1 << 4)), -1)

    def test_send_scintilla_target_selection_convenience_apis(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta gamma")
        ed.SendScintilla(ed.SCI_SETSEL, 6, 10)
        span = ed.SendScintilla(ed.SCI_TARGETFROMSELECTION)
        self.assertEqual(span, 4)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETTARGETSTART), 6)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETTARGETEND), 10)
        doc_end = ed.SendScintilla(ed.SCI_TARGETWHOLEDOCUMENT)
        self.assertEqual(doc_end, len("alpha beta gamma"))
        self.assertEqual(ed.SendScintilla(ed.SCI_GETTARGETSTART), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETTARGETEND), len("alpha beta gamma"))

    def test_send_scintilla_goto_setsel_and_empty_selection(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta gamma")
        self.assertEqual(ed.SendScintilla(ed.SCI_GOTOPOS, 5), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCURRENTPOS), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSEL, 2, 7), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONSTART), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONEND), 7)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETEMPTYSELECTION, 3), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONSTART), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONEND), 3)

    def test_send_scintilla_getline_buffer_emulation(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("one\ntwo\nthree")
        self.assertEqual(ed.SendScintilla(ed.SCI_GETLINE, 1), len("two\n"))
        buf = bytearray(8)
        copied = ed.SendScintilla(ed.SCI_GETLINE, 1, 8, buf)
        self.assertEqual(copied, 4)
        self.assertEqual(bytes(buf[:4]).decode("utf-8"), "two\n")

    def test_send_scintilla_replace_sel_and_append_text(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta")
        ed.SendScintilla(ed.SCI_SETSEL, 6, 10)
        replaced = ed.SendScintilla(ed.SCI_REPLACESEL, len("BETA"), "BETA")
        self.assertEqual(replaced, 4)
        self.assertEqual(ed.text(), "alpha BETA")
        appended = ed.SendScintilla(ed.SCI_APPENDTEXT, len("!"), "!")
        self.assertEqual(appended, 1)
        self.assertEqual(ed.text(), "alpha BETA!")

    def test_send_scintilla_undo_redo_and_capabilities(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha")
        ed.SendScintilla(ed.SCI_APPENDTEXT, len(" beta"), " beta")
        self.assertEqual(ed.SendScintilla(ed.SCI_CANUNDO), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_UNDO), 1)
        self.assertEqual(ed.text(), "alpha")
        self.assertEqual(ed.SendScintilla(ed.SCI_CANREDO), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_REDO), 1)
        self.assertEqual(ed.text(), "alpha beta")

    def test_send_scintilla_clear_and_select_all(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta")
        self.assertEqual(ed.SendScintilla(ed.SCI_SELECTALL), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_CLEAR), 1)
        self.assertEqual(ed.text(), "")
        self.assertEqual(ed.SendScintilla(ed.SCI_CLEAR), 0)

    def test_send_scintilla_readonly_set_get(self) -> None:
        ed = ScintillaCompatEditor()
        self.assertEqual(ed.SendScintilla(ed.SCI_GETREADONLY), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETREADONLY, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETREADONLY), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETREADONLY, 0), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETREADONLY), 0)

    def test_send_scintilla_inserttext_and_deleterange(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha gamma")
        inserted = ed.SendScintilla(ed.SCI_INSERTTEXT, 6, len("beta "), "beta ")
        self.assertEqual(inserted, 5)
        self.assertEqual(ed.text(), "alpha beta gamma")
        deleted = ed.SendScintilla(ed.SCI_DELETERANGE, 6, 5)
        self.assertEqual(deleted, 5)
        self.assertEqual(ed.text(), "alpha gamma")

    def test_send_scintilla_tab_and_indent_numeric_apis(self) -> None:
        ed = ScintillaCompatEditor()
        self.assertEqual(ed.SendScintilla(ed.SCI_SETTABWIDTH, 6), 6)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETTABWIDTH), 6)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETINDENT, 3), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETINDENT), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETUSETABS, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETUSETABS), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETUSETABS, 0), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETUSETABS), 0)

    def test_send_scintilla_line_visibility_round_trip(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("a\nb\nc\nd\n")
        self.assertEqual(ed.SendScintilla(ed.SCI_GETLINEVISIBLE, 2), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_HIDELINES, 1, 2), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETLINEVISIBLE, 1), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETLINEVISIBLE, 2), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_SHOWLINES, 2, 2), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETLINEVISIBLE, 2), 1)

    def test_send_scintilla_wrap_mode_set_get(self) -> None:
        ed = ScintillaCompatEditor()
        self.assertEqual(ed.SendScintilla(ed.SCI_SETWRAPMODE, ed.WrapNone), ed.WrapNone)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETWRAPMODE), ed.WrapNone)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETWRAPMODE, ed.WrapWord), ed.WrapWord)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETWRAPMODE), ed.WrapWord)

    def test_send_scintilla_caret_line_visibility_and_back_getters(self) -> None:
        ed = ScintillaCompatEditor()
        color = self._rgb_int("#123456")
        ed.SendScintilla(ed.SCI_SETCARETLINEVISIBLE, 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCARETLINEVISIBLE), 0)
        ed.SendScintilla(ed.SCI_SETCARETLINEVISIBLE, 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCARETLINEVISIBLE), 1)
        ed.SendScintilla(ed.SCI_SETCARETLINEBACK, color)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCARETLINEBACK), color)

    def test_send_scintilla_margin_and_caret_width_getters(self) -> None:
        ed = ScintillaCompatEditor()
        ed.SendScintilla(ed.SCI_SETMARGINLEFT, 9)
        ed.SendScintilla(ed.SCI_SETMARGINRIGHT, 5)
        ed.SendScintilla(ed.SCI_SETCARETWIDTH, 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMARGINLEFT), 9)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMARGINRIGHT), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCARETWIDTH), 3)

    def test_send_scintilla_readonly_blocks_mutating_commands(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta")
        ed.SendScintilla(ed.SCI_SETREADONLY, 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSEL, 0, 5), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_CLEAR), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_REPLACESEL, len("A"), "A"), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_APPENDTEXT, len("!"), "!"), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_INSERTTEXT, 0, len("X"), "X"), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_DELETERANGE, 0, 2), 0)
        self.assertEqual(ed.text(), "alpha beta")

    def test_send_scintilla_eol_mode_set_get(self) -> None:
        ed = ScintillaCompatEditor()
        self.assertEqual(ed.SendScintilla(ed.SCI_SETEOLMODE, 2), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETEOLMODE), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETEOLMODE, -1), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETEOLMODE), 0)

    def test_send_scintilla_first_visible_and_lines_on_screen(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("a\nb\nc\nd\ne\nf\n")
        self.assertGreaterEqual(ed.SendScintilla(ed.SCI_LINESONSCREEN), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETFIRSTVISIBLELINE), 0)

    def test_send_scintilla_gotoline(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("a\nbb\nccc\n")
        pos = ed.SendScintilla(ed.SCI_GOTOLINE, 2)
        self.assertEqual(pos, 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCURRENTPOS), 5)

    def test_send_scintilla_word_start_position(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta")
        self.assertEqual(ed.SendScintilla(ed.SCI_WORDSTARTPOSITION, 8, 1), 6)
        self.assertEqual(ed.SendScintilla(ed.SCI_WORDSTARTPOSITION, 8, 0), 6)

    def test_send_scintilla_word_end_position(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta")
        self.assertEqual(ed.SendScintilla(ed.SCI_WORDENDPOSITION, 6, 1), 10)
        self.assertEqual(ed.SendScintilla(ed.SCI_WORDENDPOSITION, 6, 0), 10)

    def test_send_scintilla_undo_collection_set_get(self) -> None:
        ed = ScintillaCompatEditor()
        self.assertEqual(ed.SendScintilla(ed.SCI_GETUNDOCOLLECTION), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETUNDOCOLLECTION, 0), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETUNDOCOLLECTION), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETUNDOCOLLECTION, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETUNDOCOLLECTION), 1)

    def test_send_scintilla_begin_end_undo_action_noop(self) -> None:
        ed = ScintillaCompatEditor()
        self.assertEqual(ed.SendScintilla(ed.SCI_BEGINUNDOACTION), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_ENDUNDOACTION), 1)

    def test_send_scintilla_empty_undo_buffer(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha")
        ed.SendScintilla(ed.SCI_APPENDTEXT, len(" beta"), " beta")
        self.assertEqual(ed.SendScintilla(ed.SCI_CANUNDO), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_EMPTYUNDOBUFFER), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_CANUNDO), 0)

    def test_send_scintilla_get_modify(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha")
        ed.setModified(False)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMODIFY), 0)
        ed.SendScintilla(ed.SCI_APPENDTEXT, len(" beta"), " beta")
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMODIFY), 1)
        ed.setModified(False)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMODIFY), 0)

    def test_send_scintilla_line_state_and_max(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("a\nb\nc\n")
        self.assertEqual(ed.SendScintilla(ed.SCI_GETLINESTATE, 1), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETLINESTATE, 1, 7), 7)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETLINESTATE, 2, 3), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETLINESTATE, 1), 7)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMAXLINESTATE), 7)

    def test_send_scintilla_setsavepoint(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha")
        ed.SendScintilla(ed.SCI_APPENDTEXT, len(" beta"), " beta")
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMODIFY), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSAVEPOINT), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMODIFY), 0)

    def test_send_scintilla_document_start_end(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha\nbeta")
        end = ed.SendScintilla(ed.SCI_DOCUMENTEND)
        self.assertEqual(end, len("alpha\nbeta"))
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCURRENTPOS), len("alpha\nbeta"))
        self.assertEqual(ed.SendScintilla(ed.SCI_DOCUMENTSTART), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCURRENTPOS), 0)

    def test_send_scintilla_home_and_lineend(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("aa\nbbbb\ncc")
        ed.setCursorPosition(1, 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_HOME), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCURRENTPOS), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_LINEEND), 7)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCURRENTPOS), 7)

    def test_send_scintilla_cursor_motion_commands(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("ab\ncd\nef")
        ed.SendScintilla(ed.SCI_DOCUMENTSTART)
        self.assertEqual(ed.SendScintilla(ed.SCI_CHARRIGHT), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_CHARRIGHT), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_LINEDOWN), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_LINEUP), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_CHARLEFT), 1)

    def test_send_scintilla_cancel_clears_selection(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta")
        ed.SendScintilla(ed.SCI_SETSEL, 0, 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONEND) - ed.SendScintilla(ed.SCI_GETSELECTIONSTART), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_CANCEL), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONEND), ed.SendScintilla(ed.SCI_GETSELECTIONSTART))

    def test_send_scintilla_extend_cursor_commands(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("ab\ncd\nef")
        ed.SendScintilla(ed.SCI_DOCUMENTSTART)
        ed.SendScintilla(ed.SCI_CHARRIGHT)
        self.assertEqual(ed.SendScintilla(ed.SCI_CHARRIGHTEXTEND), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONSTART), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONEND), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_CHARLEFTEXTEND), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONSTART), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONEND), 1)
        ed.setCursorPosition(1, 1)
        ed.SendScintilla(ed.SCI_LINEDOWNEXTEND)
        self.assertNotEqual(ed.SendScintilla(ed.SCI_GETSELECTIONSTART), ed.SendScintilla(ed.SCI_GETSELECTIONEND))
        ed.SendScintilla(ed.SCI_LINEUPEXTEND)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONSTART), ed.SendScintilla(ed.SCI_GETSELECTIONEND))
        ed.setCursorPosition(1, 1)
        ed.SendScintilla(ed.SCI_HOMEEXTEND)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONSTART), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONEND), 4)

    def test_send_scintilla_end_document_extend_and_vchome(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("  aa\n  bbbb\ncc")
        ed.setCursorPosition(1, 1)
        end_pos = ed.SendScintilla(ed.SCI_END)
        self.assertEqual(end_pos, 11)
        ed.setCursorPosition(1, 1)
        end_ext = ed.SendScintilla(ed.SCI_ENDEXTEND)
        self.assertEqual(end_ext, 11)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONSTART), 6)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONEND), 11)
        ed.SendScintilla(ed.SCI_DOCUMENTSTART)
        self.assertEqual(ed.SendScintilla(ed.SCI_DOCUMENTENDEXTEND), len("  aa\n  bbbb\ncc"))
        self.assertEqual(ed.SendScintilla(ed.SCI_DOCUMENTSTARTEXTEND), 0)
        ed.setCursorPosition(1, 4)
        self.assertEqual(ed.SendScintilla(ed.SCI_VCHOME), 7)

    def test_send_scintilla_view_and_guide_getters(self) -> None:
        ed = ScintillaCompatEditor()
        ed.SendScintilla(ed.SCI_SETVIEWWS, 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETVIEWWS), 1)
        ed.SendScintilla(ed.SCI_SETVIEWEOL, 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETVIEWEOL), 1)
        ed.SendScintilla(ed.SCI_SETINDENTATIONGUIDES, 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETINDENTATIONGUIDES), 1)
        ed.SendScintilla(ed.SCI_SETWRAPVISUALFLAGS, 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETWRAPVISUALFLAGS), 1)
        ed.SendScintilla(ed.SCI_SETCONTROLCHARSYMBOL, 183)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCONTROLCHARSYMBOL), 183)

    def test_send_scintilla_position_and_scroll_state_apis_batch(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha\nbeta\ngamma")
        self.assertEqual(ed.SendScintilla(ed.SCI_GETTEXTLENGTH), len("alpha\nbeta\ngamma"))
        self.assertEqual(ed.SendScintilla(ed.SCI_POSITIONBEFORE, 5), 4)
        self.assertEqual(ed.SendScintilla(ed.SCI_POSITIONAFTER, 5), 6)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETFIRSTVISIBLELINE, 3), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_LINESCROLL, 2, 4), 7)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETFIRSTVISIBLELINE), 7)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETXOFFSET, 11), 11)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETXOFFSET), 11)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSCROLLWIDTH, 250), 250)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSCROLLWIDTH), 250)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSCROLLWIDTHTRACKING, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSCROLLWIDTHTRACKING), 1)

    def test_send_scintilla_word_motion_and_extend_batch(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("alpha beta gamma")
        ed.SendScintilla(ed.SCI_GOTOPOS, 8)
        self.assertEqual(ed.SendScintilla(ed.SCI_WORDLEFT), 6)
        self.assertEqual(ed.SendScintilla(ed.SCI_WORDRIGHT), 10)
        ed.SendScintilla(ed.SCI_GOTOPOS, 8)
        self.assertEqual(ed.SendScintilla(ed.SCI_WORDLEFTEXTEND), 6)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONSTART), 6)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONEND), 8)
        self.assertEqual(ed.SendScintilla(ed.SCI_WORDRIGHTEXTEND), 10)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONSTART), 8)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONEND), 10)

    def test_send_scintilla_line_editing_batch(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("abc\ndef\nghi")
        ed.SendScintilla(ed.SCI_GOTOPOS, 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_DELETEBACK), 1)
        self.assertEqual(ed.text(), "ac\ndef\nghi")
        ed.setCursorPosition(0, 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_DELLINERIGHT), 1)
        self.assertEqual(ed.text(), "a\ndef\nghi")
        ed.setCursorPosition(1, 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_DELLINELEFT), 1)
        self.assertEqual(ed.text(), "a\nef\nghi")
        ed.setCursorPosition(1, 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_LINETRANSPOSE), 1)
        self.assertEqual(ed.text(), "ef\na\nghi")
        ed.setCursorPosition(1, 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_LINECUT), 1)
        self.assertEqual(ed.text(), "ef\nghi")
        ed.setCursorPosition(0, 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_LINEDELETE), 1)
        self.assertEqual(ed.text(), "ghi")

    def test_send_scintilla_wrap_home_end_aliases_batch(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("  aa\n  bbbb\ncc")
        ed.setCursorPosition(1, 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_HOMEWRAP), 5)
        ed.setCursorPosition(1, 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_HOMEWRAPEXTEND), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONSTART), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELECTIONEND), 6)
        ed.setCursorPosition(1, 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_LINEENDWRAP), 11)
        ed.setCursorPosition(1, 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_LINEENDWRAPEXTEND), 11)
        self.assertEqual(ed.SendScintilla(ed.SCI_VCHOMEWRAP), 7)
        ed.setCursorPosition(1, 4)
        self.assertEqual(ed.SendScintilla(ed.SCI_VCHOMEWRAPEXTEND), 7)

    def test_send_scintilla_page_up_down_batch(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("\n".join(str(i) for i in range(200)))
        ed.resize(800, 200)
        ed.SendScintilla(ed.SCI_DOCUMENTSTART)
        down = ed.SendScintilla(ed.SCI_PAGEDOWN)
        self.assertGreater(down, 0)
        up = ed.SendScintilla(ed.SCI_PAGEUP)
        self.assertLessEqual(up, down)
        ed.SendScintilla(ed.SCI_DOCUMENTSTART)
        d_ext = ed.SendScintilla(ed.SCI_PAGEDOWNEXTEND)
        self.assertGreater(d_ext, 0)
        self.assertNotEqual(ed.SendScintilla(ed.SCI_GETSELECTIONSTART), ed.SendScintilla(ed.SCI_GETSELECTIONEND))
        u_ext = ed.SendScintilla(ed.SCI_PAGEUPEXTEND)
        self.assertLessEqual(u_ext, d_ext)

    def test_send_scintilla_policy_and_timing_set_get_batch(self) -> None:
        ed = ScintillaCompatEditor()
        self.assertEqual(ed.SendScintilla(ed.SCI_SETXCARETPOLICY, 3, 7), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETXCARETPOLICY), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETYCARETPOLICY, 5, 9), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETYCARETPOLICY), 5)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETVISIBLEPOLICY, 2, 4), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETVISIBLEPOLICY), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETCARETPERIOD, 750), 750)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCARETPERIOD), 750)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETMOUSEDWELLTIME, 1234), 1234)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMOUSEDWELLTIME), 1234)

    def test_send_scintilla_zoom_edge_and_print_wrap_batch(self) -> None:
        ed = ScintillaCompatEditor()
        edge = self._rgb_int("#123456")
        self.assertEqual(ed.SendScintilla(ed.SCI_SETZOOM, 2), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETZOOM), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETEDGEMODE, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETEDGEMODE), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETEDGECOLUMN, 120), 120)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETEDGECOLUMN), 120)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETEDGECOLOUR, edge), edge)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETEDGECOLOUR), edge)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETPRINTWRAPMODE, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETPRINTWRAPMODE), 1)

    def test_send_scintilla_extra_caret_paste_virtual_space_batch(self) -> None:
        ed = ScintillaCompatEditor()
        self.assertEqual(ed.SendScintilla(ed.SCI_SETEXTRAASCENT, 3), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETEXTRAASCENT), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETEXTRADESCENT, 4), 4)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETEXTRADESCENT), 4)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETCARETSTICKY, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCARETSTICKY), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETPASTECONVERTENDINGS, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETPASTECONVERTENDINGS), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETVIRTUALSPACEOPTIONS, 3), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETVIRTUALSPACEOPTIONS), 3)

    def test_send_scintilla_caret_and_additional_selection_visual_batch(self) -> None:
        ed = ScintillaCompatEditor()
        c1 = self._rgb_int("#112233")
        c2 = self._rgb_int("#445566")
        c3 = self._rgb_int("#778899")
        c4 = self._rgb_int("#aabbcc")
        self.assertEqual(ed.SendScintilla(ed.SCI_SETCARETFORE, c1), c1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCARETFORE), c1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETCARETSTYLE, 2), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCARETSTYLE), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETADDITIONALCARETFORE, c2), c2)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETADDITIONALCARETFORE), c2)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETADDITIONALSELFORE, c3), c3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETADDITIONALSELFORE), c3)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETADDITIONALSELBACK, c4), c4)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETADDITIONALSELBACK), c4)

    def test_send_scintilla_additional_caret_and_hotspot_state_batch(self) -> None:
        ed = ScintillaCompatEditor()
        back = self._rgb_int("#334455")
        self.assertEqual(ed.SendScintilla(ed.SCI_SETADDITIONALCARETSBLINK, 0), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETADDITIONALCARETSBLINK), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETADDITIONALCARETSVISIBLE, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETADDITIONALCARETSVISIBLE), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETHOTSPOTACTIVEBACK, back), back)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETHOTSPOTACTIVEBACK), back)
        ed.send_scintilla_named("SCI_SETHOTSPOTACTIVEUNDERLINE", 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETHOTSPOTACTIVEUNDERLINE), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETHOTSPOTSINGLELINE, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETHOTSPOTSINGLELINE), 1)

    def test_send_scintilla_status_mod_buffer_layout_batch(self) -> None:
        ed = ScintillaCompatEditor()
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSTATUS, 2), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSTATUS), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETMODEVENTMASK, 255), 255)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETMODEVENTMASK), 255)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETBUFFEREDDRAW, 0), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETBUFFEREDDRAW), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETTWOPHASEDRAW, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETTWOPHASEDRAW), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETLAYOUTCACHE, 2), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETLAYOUTCACHE), 2)

    def test_send_scintilla_whitespace_font_and_endline_batch(self) -> None:
        ed = ScintillaCompatEditor()
        fore = self._rgb_int("#112233")
        back = self._rgb_int("#334455")
        self.assertEqual(ed.SendScintilla(ed.SCI_SETWHITESPACEFORE, fore), fore)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETWHITESPACEFORE), fore)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETWHITESPACEBACK, back), back)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETWHITESPACEBACK), back)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETWHITESPACESIZE, 3), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETWHITESPACESIZE), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETEXTRAFONTFLAG, 17), 17)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETEXTRAFONTFLAG), 17)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETENDATLASTLINE, 0), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETENDATLASTLINE), 0)

    def test_send_scintilla_charset_and_mode_state_batch(self) -> None:
        ed = ScintillaCompatEditor()
        punct = ".,:;!?()[]{}"
        words = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
        self.assertEqual(ed.SendScintilla(ed.SCI_SETPUNCTUATIONCHARS, len(punct), punct), len(punct))
        h1: dict[str, str] = {}
        self.assertEqual(ed.SendScintilla(ed.SCI_GETPUNCTUATIONCHARS, h1), len(punct))
        self.assertEqual(h1.get("text"), punct)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETWORDCHARS, len(words), words), len(words))
        h2: dict[str, str] = {}
        self.assertEqual(ed.SendScintilla(ed.SCI_GETWORDCHARS, h2), len(words))
        self.assertEqual(h2.get("text"), words)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETLINEENDTYPESALLOWED, 3), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETLINEENDTYPESALLOWED), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETACCESSIBILITY, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETACCESSIBILITY), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETBIDIRECTIONAL, 2), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETBIDIRECTIONAL), 2)

    def test_send_scintilla_large_state_batch_35(self) -> None:
        ed = ScintillaCompatEditor()
        loc = "en-US"
        self.assertEqual(ed.SendScintilla(ed.SCI_SETIDLESTYLING, 2), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETIDLESTYLING), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSELALPHA, 120), 120)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELALPHA), 120)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETADDITIONALSELALPHA, 90), 90)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETADDITIONALSELALPHA), 90)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETSELEOLFILLED, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETSELEOLFILLED), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETFONTLOCALE, len(loc), loc), len(loc))
        h: dict[str, str] = {}
        self.assertEqual(ed.SendScintilla(ed.SCI_GETFONTLOCALE, h), len(loc))
        self.assertEqual(h.get("text"), loc)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETKEYSUNICODE, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETKEYSUNICODE), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETAUTOCASESENSITIVE, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETAUTOCASESENSITIVE), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETAUTOMAXHEIGHT, 12), 12)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETAUTOMAXHEIGHT), 12)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETAUTOMAXWIDTH, 80), 80)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETAUTOMAXWIDTH), 80)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETAUTODROPRESTOFWORD, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETAUTODROPRESTOFWORD), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETAUTOHIDE, 0), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETAUTOHIDE), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETAUTOCANCELATSTART, 0), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETAUTOCANCELATSTART), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETAUTOCURRENT, 3), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETAUTOCURRENT), 3)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETCARETLINEFRAME, 2), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCARETLINEFRAME), 2)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETCARETLINEVISIBLEALWAYS, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETCARETLINEVISIBLEALWAYS), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETHSCROLLBAR, 1), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETHSCROLLBAR), 1)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETVSCROLLBAR, 0), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_GETVSCROLLBAR), 0)
        self.assertEqual(ed.SendScintilla(ed.SCI_SETFOCUS, 1), 1)

    def test_editor_widget_scintilla_command_coverage_returns_true(self) -> None:
        ed = ScintillaCompatEditor()
        ed.setText("a\nb\nc\nd\n")
        command_calls = self._compat_command_args_map(ed)
        for command, args in command_calls.items():
            with self.subTest(command=command):
                self.assertTrue(ed.send_scintilla_named(command, *args), msg=f"{command} should return True")

    def test_editor_widget_scintilla_command_set_guard(self) -> None:
        editor_widget_path = ROOT / "src" / "pypad" / "ui" / "editor" / "editor_widget.py"
        source = editor_widget_path.read_text(encoding="utf-8")
        used = set(re.findall(r'_send_scintilla\("((?:SCI_[A-Z0-9_]+))"', source))
        ed = ScintillaCompatEditor()
        covered = set(self._compat_command_args_map(ed).keys())
        missing = sorted(used - covered)
        self.assertEqual(
            missing,
            [],
            msg=f"Add compat coverage entries for new SCI commands: {missing}",
        )


if __name__ == "__main__":
    unittest.main()
