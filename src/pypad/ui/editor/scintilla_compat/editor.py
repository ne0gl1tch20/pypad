from __future__ import annotations

import re

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal, QTimer
from PySide6.QtGui import QColor, QKeySequence, QMouseEvent, QPainter, QPolygon, QTextCharFormat, QTextCursor
from PySide6.QtCore import QStringListModel
from PySide6.QtWidgets import QCompleter, QPlainTextEdit, QTextEdit, QWidget
from PySide6.QtWidgets import QToolTip
from PySide6.QtGui import QPalette
from .models import ColumnBlock, FoldRegion, HotspotRange, IndicatorRange
from .extra_state_handlers import handle_extra_state_command
from .movement_edit_handlers import handle_movement_edit_command
from .selection_undo_handlers import handle_selection_undo_command

# Advanced but minified scintilla engine, tailored for PySide6
# Scintilla Recreated from scratch using QPlainTextEdit, inspired by https://doc.qt.io/qt-6/qtwidgets-widgets-codeeditor-example.html and https://github.com/pyqtgraph/pyqtgraph

class _MarginArea(QWidget):
    def __init__(self, editor: "ScintillaCompatEditor") -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.margin_width(), 0)

    def paintEvent(self, event) -> None:
        self._editor.paint_margin(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._editor.handle_margin_click(event)

# Lots of variables!
class ScintillaCompatEditor(QPlainTextEdit):
    hotspotClicked = Signal(int, str)
    hotspotHovered = Signal(int, str)
    marginClicked = Signal(int, int)
    indicatorClicked = Signal(int, int, str)
    indicatorHovered = Signal(int, int, str)

    WrapNone = 0
    WrapWord = 1
    # Stable aliases for QPlainTextEdit wrap modes across Qt/PySide enum bindings.
    WidgetWidth = getattr(QPlainTextEdit, "WidgetWidth", QPlainTextEdit.LineWrapMode.WidgetWidth)
    NoWrap = getattr(QPlainTextEdit, "NoWrap", QPlainTextEdit.LineWrapMode.NoWrap)
    RightArrow = 2
    NoFoldStyle = 0
    BoxedTreeFoldStyle = 1
    AcsNone = 0
    AcsAll = 1
    AcsDocument = 2
    AcsAPIs = 3
    SCMOD_ALT = int(Qt.KeyboardModifier.AltModifier.value)
    SC_SEL_STREAM = 0
    SC_SEL_RECTANGLE = 1
    SC_FOLDACTION_CONTRACT = 0
    SC_FOLDACTION_EXPAND = 1
    INDIC_PLAIN = 0
    INDIC_SQUIGGLE = 1
    INDIC_TT = 2
    INDIC_DIAGONAL = 3
    INDIC_STRIKE = 4
    INDIC_HIDDEN = 5
    INDIC_BOX = 6
    INDIC_ROUNDBOX = 7
    SC_MARGIN_SYMBOL = 0
    SC_MARGIN_NUMBER = 1
    SC_MARGIN_BACK = 2
    SC_MARGIN_FORE = 3
    SC_MARGIN_TEXT = 4
    SC_MARGIN_RTEXT = 5
    SC_MARGIN_COLOUR = 6
    Circle = 0
    RoundRect = 1
    RightArrow = 2
    SmallRect = 3
    ShortArrow = 4
    Empty = 5
    Arrow = 6
    Plus = 7
    Minus = 8
    # Subset of Scintilla message ids used by compatibility callers.
    SCI_GETLINECOUNT = 2154
    SCI_GETTEXTLENGTH = 2183
    SCI_GETLINE = 2153
    SCI_SETLINESTATE = 2092
    SCI_GETLINESTATE = 2093
    SCI_GETMAXLINESTATE = 2094
    SCI_POSITIONFROMLINE = 2167
    SCI_GETLINEENDPOSITION = 2136
    SCI_LINELENGTH = 2350
    SCI_GETCHARAT = 2007
    SCI_GETSTYLEAT = 2010
    SCI_SETSAVEPOINT = 2014
    SCI_CANCEL = 2325
    SCI_CHARLEFT = 2304
    SCI_CHARRIGHT = 2306
    SCI_LINEUP = 2300
    SCI_LINEDOWN = 2301
    SCI_CHARLEFTEXTEND = 2305
    SCI_CHARRIGHTEXTEND = 2307
    SCI_LINEUPEXTEND = 2302
    SCI_LINEDOWNEXTEND = 2303
    SCI_HOMEEXTEND = 2313
    SCI_HOMEWRAP = 2349
    SCI_HOMEWRAPEXTEND = 2450
    SCI_END = 2310
    SCI_ENDEXTEND = 2311
    SCI_LINEENDWRAP = 2451
    SCI_LINEENDWRAPEXTEND = 2452
    SCI_WORDLEFT = 2308
    SCI_WORDRIGHT = 2309
    SCI_WORDLEFTEXTEND = 2390
    SCI_WORDRIGHTEXTEND = 2391
    SCI_DELETEBACK = 2326
    SCI_DELLINELEFT = 2395
    SCI_DELLINERIGHT = 2396
    SCI_LINECUT = 2337
    SCI_LINEDELETE = 2338
    SCI_LINETRANSPOSE = 2339
    SCI_DOCUMENTSTARTEXTEND = 2317
    SCI_DOCUMENTENDEXTEND = 2319
    SCI_VCHOME = 2331
    SCI_VCHOMEWRAP = 2453
    SCI_VCHOMEWRAPEXTEND = 2454
    SCI_PAGEUP = 2320
    SCI_PAGEDOWN = 2321
    SCI_PAGEUPEXTEND = 2322
    SCI_PAGEDOWNEXTEND = 2323
    SCI_DOCUMENTSTART = 2316
    SCI_DOCUMENTEND = 2318
    SCI_HOME = 2312
    SCI_LINEEND = 2314
    SCI_MARKERGET = 2046
    SCI_MARKERNEXT = 2047
    SCI_MARKERPREVIOUS = 2048
    SCI_GETCOLUMN = 2129
    SCI_GETCURLINE = 2027
    SCI_GOTOLINE = 2024
    SCI_POSITIONBEFORE = 2417
    SCI_POSITIONAFTER = 2418
    SCI_LINESCROLL = 2168
    SCI_SETFIRSTVISIBLELINE = 2613
    SCI_SETXOFFSET = 2397
    SCI_GETXOFFSET = 2398
    SCI_SETSCROLLWIDTH = 2274
    SCI_GETSCROLLWIDTH = 2275
    SCI_SETSCROLLWIDTHTRACKING = 2516
    SCI_GETSCROLLWIDTHTRACKING = 2517
    SCI_SETXCARETPOLICY = 2402
    SCI_GETXCARETPOLICY = 2409
    SCI_SETYCARETPOLICY = 2403
    SCI_GETYCARETPOLICY = 2410
    SCI_SETVISIBLEPOLICY = 2394
    SCI_GETVISIBLEPOLICY = 2479
    SCI_SETCARETPERIOD = 2076
    SCI_GETCARETPERIOD = 2075
    SCI_SETMOUSEDWELLTIME = 2264
    SCI_GETMOUSEDWELLTIME = 2265
    SCI_SETZOOM = 2373
    SCI_GETZOOM = 2374
    SCI_SETEDGEMODE = 2363
    SCI_GETEDGEMODE = 2362
    SCI_SETEDGECOLUMN = 2361
    SCI_GETEDGECOLUMN = 2360
    SCI_SETEDGECOLOUR = 2365
    SCI_GETEDGECOLOUR = 2364
    SCI_SETPRINTWRAPMODE = 2406
    SCI_GETPRINTWRAPMODE = 2407
    SCI_SETEXTRAASCENT = 2525
    SCI_GETEXTRAASCENT = 2526
    SCI_SETEXTRADESCENT = 2527
    SCI_GETEXTRADESCENT = 2528
    SCI_SETCARETSTICKY = 2458
    SCI_GETCARETSTICKY = 2457
    SCI_SETPASTECONVERTENDINGS = 2467
    SCI_GETPASTECONVERTENDINGS = 2468
    SCI_SETVIRTUALSPACEOPTIONS = 2596
    SCI_GETVIRTUALSPACEOPTIONS = 2597
    SCI_SETSTATUS = 2382
    SCI_GETSTATUS = 2383
    SCI_SETMODEVENTMASK = 2359
    SCI_GETMODEVENTMASK = 30012
    SCI_SETBUFFEREDDRAW = 2035
    SCI_GETBUFFEREDDRAW = 2034
    SCI_SETTWOPHASEDRAW = 2284
    SCI_GETTWOPHASEDRAW = 2283
    SCI_SETLAYOUTCACHE = 2272
    SCI_GETLAYOUTCACHE = 2273
    SCI_SETWHITESPACEFORE = 30120
    SCI_GETWHITESPACEFORE = 30121
    SCI_SETWHITESPACEBACK = 30122
    SCI_GETWHITESPACEBACK = 30123
    SCI_SETWHITESPACESIZE = 30124
    SCI_GETWHITESPACESIZE = 30125
    SCI_SETEXTRAFONTFLAG = 30126
    SCI_GETEXTRAFONTFLAG = 30127
    SCI_SETENDATLASTLINE = 30128
    SCI_GETENDATLASTLINE = 30129
    SCI_SETPUNCTUATIONCHARS = 30130
    SCI_GETPUNCTUATIONCHARS = 30131
    SCI_SETWORDCHARS = 30132
    SCI_GETWORDCHARS = 30133
    SCI_SETLINEENDTYPESALLOWED = 30134
    SCI_GETLINEENDTYPESALLOWED = 30135
    SCI_SETACCESSIBILITY = 30136
    SCI_GETACCESSIBILITY = 30137
    SCI_SETBIDIRECTIONAL = 30138
    SCI_GETBIDIRECTIONAL = 30139
    SCI_SETIDLESTYLING = 30140
    SCI_GETIDLESTYLING = 30141
    SCI_SETSELALPHA = 30142
    SCI_GETSELALPHA = 30143
    SCI_SETADDITIONALSELALPHA = 30144
    SCI_GETADDITIONALSELALPHA = 30145
    SCI_SETSELEOLFILLED = 30146
    SCI_GETSELEOLFILLED = 30147
    SCI_SETFONTLOCALE = 30148
    SCI_GETFONTLOCALE = 30149
    SCI_SETKEYSUNICODE = 30150
    SCI_GETKEYSUNICODE = 30151
    SCI_SETAUTOCASESENSITIVE = 30152
    SCI_GETAUTOCASESENSITIVE = 30153
    SCI_SETAUTOMAXHEIGHT = 30154
    SCI_GETAUTOMAXHEIGHT = 30155
    SCI_SETAUTOMAXWIDTH = 30156
    SCI_GETAUTOMAXWIDTH = 30157
    SCI_SETAUTODROPRESTOFWORD = 30158
    SCI_GETAUTODROPRESTOFWORD = 30159
    SCI_SETAUTOHIDE = 30160
    SCI_GETAUTOHIDE = 30161
    SCI_SETAUTOCANCELATSTART = 30162
    SCI_GETAUTOCANCELATSTART = 30163
    SCI_SETAUTOCURRENT = 30164
    SCI_GETAUTOCURRENT = 30165
    SCI_SETCARETLINEFRAME = 30166
    SCI_GETCARETLINEFRAME = 30167
    SCI_SETCARETLINEVISIBLEALWAYS = 30168
    SCI_GETCARETLINEVISIBLEALWAYS = 30169
    SCI_SETHSCROLLBAR = 30170
    SCI_GETHSCROLLBAR = 30171
    SCI_SETVSCROLLBAR = 30172
    SCI_GETVSCROLLBAR = 30173
    SCI_SETFOCUS = 30174
    SCI_SETCARETFORE = 2069
    SCI_GETCARETFORE = 2137
    SCI_SETCARETSTYLE = 2512
    SCI_GETCARETSTYLE = 2513
    SCI_SETADDITIONALCARETFORE = 2604
    SCI_GETADDITIONALCARETFORE = 2605
    SCI_SETADDITIONALSELFORE = 2609
    SCI_GETADDITIONALSELFORE = 2610
    SCI_SETADDITIONALSELBACK = 30001
    SCI_GETADDITIONALSELBACK = 30002
    SCI_SETADDITIONALCARETSBLINK = 30003
    SCI_GETADDITIONALCARETSBLINK = 30004
    SCI_SETADDITIONALCARETSVISIBLE = 30005
    SCI_GETADDITIONALCARETSVISIBLE = 30006
    SCI_SETHOTSPOTACTIVEBACK = 30007
    SCI_GETHOTSPOTACTIVEBACK = 30008
    SCI_GETHOTSPOTACTIVEUNDERLINE = 30009
    SCI_SETHOTSPOTSINGLELINE = 30010
    SCI_GETHOTSPOTSINGLELINE = 30011
    SCI_SETEOLMODE = 2031
    SCI_GETEOLMODE = 2030
    SCI_GETFIRSTVISIBLELINE = 2152
    SCI_LINESONSCREEN = 2370
    SCI_SETTABWIDTH = 2036
    SCI_GETTABWIDTH = 2121
    SCI_SETUSETABS = 2124
    SCI_GETUSETABS = 2125
    SCI_SETINDENT = 2122
    SCI_GETINDENT = 2123
    SCI_SETWRAPMODE = 2268
    SCI_GETWRAPMODE = 2269
    SCI_BRACEMATCH = 2353
    SCI_WORDSTARTPOSITION = 2266
    SCI_WORDENDPOSITION = 2267
    SCI_GETBRACEHIGHLIGHT = 2355
    SCI_GETBRACEBADLIGHT = 2498
    SCI_GETCARETLINEVISIBLE = 2095
    SCI_GETCARETLINEBACK = 2138
    SCI_LINEFROMPOSITION = 2166
    SCI_GETCURRENTPOS = 2008
    SCI_GETANCHOR = 2009
    SCI_GETTEXT = 2182
    SCI_GETLENGTH = 2006
    SCI_GETSELECTIONSTART = 2143
    SCI_GETSELECTIONEND = 2145
    SCI_GOTOPOS = 2025
    SCI_SETSEL = 2160
    SCI_SETEMPTYSELECTION = 2556
    SCI_GETSELECTIONS = 2570
    SCI_GETMAINSELECTION = 2571
    SCI_SETMAINSELECTION = 2579
    SCI_ROTATESELECTION = 2606
    SCI_SWAPMAINANCHORCARET = 2607
    SCI_GETMAINSELSTART = 2575
    SCI_GETMAINSELEND = 2576
    SCI_GETSELECTIONNSTART = 2573
    SCI_GETSELECTIONNEND = 2574
    SCI_SETSELECTIONNSTART = 2580
    SCI_SETSELECTIONNEND = 2581
    SCI_ADDSELECTION = 2572
    SCI_DROPSELECTIONN = 2671
    SCI_CLEARSELECTIONS = 2571 + 6
    SCI_GETTEXTRANGE = 2162
    SCI_REPLACESEL = 2170
    SCI_APPENDTEXT = 2282
    SCI_UNDO = 2176
    SCI_REDO = 2011
    SCI_CANUNDO = 2174
    SCI_CANREDO = 2016
    SCI_SETUNDOCOLLECTION = 2012
    SCI_GETUNDOCOLLECTION = 2019
    SCI_BEGINUNDOACTION = 2078
    SCI_ENDUNDOACTION = 2079
    SCI_EMPTYUNDOBUFFER = 2175
    SCI_GETMODIFY = 2159
    SCI_CLEAR = 2180
    SCI_SELECTALL = 2013
    SCI_SETREADONLY = 2171
    SCI_GETREADONLY = 2140
    SCI_INSERTTEXT = 2003
    SCI_DELETERANGE = 2645
    SCI_TARGETFROMSELECTION = 2287
    SCI_TARGETWHOLEDOCUMENT = 2690
    SCI_SETTARGETSTART = 2190
    SCI_GETTARGETSTART = 2191
    SCI_SETTARGETEND = 2192
    SCI_GETTARGETEND = 2193
    SCI_REPLACETARGET = 2194
    SCI_REPLACETARGETRE = 2195
    SCI_REPLACETARGETMINIMAL = 2779
    SCI_SEARCHINTARGET = 2197
    SCI_GETTARGETTEXT = 2687
    SCI_SETSEARCHFLAGS = 2198
    SCI_GETSEARCHFLAGS = 2199
    SCI_SETSELBACK = 2068
    SCI_SETSELFORE = 2067
    SCI_SETCARETLINEVISIBLE = 2096
    SCI_SETCARETLINEBACK = 2098
    SCI_SETCARETWIDTH = 2188
    SCI_GETCARETWIDTH = 2189
    SCI_SETMARGINLEFT = 2155
    SCI_GETMARGINLEFT = 2156
    SCI_SETMARGINRIGHT = 2157
    SCI_GETMARGINRIGHT = 2158
    SCI_SETVIEWWS = 2021
    SCI_GETVIEWWS = 2020
    SCI_SETVIEWEOL = 2356
    SCI_GETVIEWEOL = 2357
    SCI_SETCONTROLCHARSYMBOL = 2388
    SCI_GETCONTROLCHARSYMBOL = 2389
    SCI_SETINDENTATIONGUIDES = 2132
    SCI_GETINDENTATIONGUIDES = 2133
    SCI_SETWRAPVISUALFLAGS = 2460
    SCI_GETWRAPVISUALFLAGS = 2461
    SCI_SETSELECTIONMODE = 2422
    SCI_GETSELECTIONMODE = 2423
    SCI_SETMULTIPLESELECTION = 2563
    SCI_GETMULTIPLESELECTION = 2564
    SCI_SETADDITIONALSELECTIONTYPING = 2567
    SCI_GETADDITIONALSELECTIONTYPING = 2568
    SCI_SETMULTIPASTE = 2614
    SCI_SETINDICATORCURRENT = 2500
    SCI_SETINDICATORVALUE = 2502
    SCI_INDICSETSTYLE = 2080
    SCI_INDICSETFORE = 2081
    SCI_INDICATORFILLRANGE = 2504
    SCI_INDICATORCLEARRANGE = 2505
    SCI_STYLESETFORE = 2051
    SCI_STYLESETBACK = 2052
    SCI_STYLESETBOLD = 2053
    SCI_STYLESETITALIC = 2054
    SCI_STYLESETUNDERLINE = 2059
    SCI_GETSTYLEBITS = 2091
    SCI_SETSTYLEBITS = 2090
    SCI_STYLECLEARALL = 2050
    SCI_STARTSTYLING = 2032
    SCI_SETSTYLING = 2033
    SCI_GETFOLDLEVEL = 2223
    SCI_GETFOLDPARENT = 2225
    SCI_GETLASTCHILD = 2224
    SCI_FOLDLINE = 2237
    SCI_FOLDALL = 2662
    SCI_SHOWLINES = 2226
    SCI_HIDELINES = 2227
    SCI_GETLINEVISIBLE = 2228
    SC_FOLDLEVELNUMBERMASK = 0x0FFF
    SCFIND_MATCHCASE = 0x0004
    SCFIND_WHOLEWORD = 0x0002
    SCFIND_WORDSTART = 0x00100000
    SCFIND_REGEXP = 0x00200000

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._markers: dict[int, set[int]] = {}
        self._marker_colors: dict[int, QColor] = {}
        self._marker_symbols: dict[int, int] = {}
        self._next_marker_id = 1
        self._hidden_lines: set[int] = set()
        self._fold_hidden_lines: set[int] = set()
        self._collapsed_headers: set[int] = set()
        self._fold_regions: dict[int, FoldRegion] = {}
        self._use_tabs = False
        self._indent_width = 4
        self._folding_enabled = True
        self._lexer = None
        self._apis = None
        self._auto_completion_source = self.AcsAll
        self._auto_completion_threshold = 1
        self._auto_completion_case_sensitive = False
        self._auto_completion_use_single = True
        self._multiple_selection_enabled = False
        self._additional_selection_typing = False
        self._multi_paste = False
        self._rectangular_selection_modifier = self.SCMOD_ALT
        self._column_mode = False
        self._additional_carets: list[int] = []
        self._multi_ranges: list[tuple[int, int]] = []
        self._column_drag_anchor: tuple[int, int] | None = None
        self._column_drag_active = False
        self._column_block: ColumnBlock | None = None
        self._view_whitespace = False
        self._view_eol = False
        self._view_control_chars = False
        self._control_char_symbol = 0
        self._wrap_mode = self.WrapWord
        self._eol_mode = 0
        self._show_indent_guides = False
        self._show_wrap_symbol = False
        self._undo_collection_enabled = True
        self._completion_words: list[str] = []
        self._completion_model = QStringListModel(self)
        self._completer = QCompleter(self._completion_model, self)
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.activated.connect(self._insert_completion)
        self._annotations: dict[int, str] = {}
        self._brace_match_pair: tuple[int, int] | None = None
        self._margin_sensitive: dict[int, bool] = {}
        self._margin_types: dict[int, int] = {0: self.SC_MARGIN_SYMBOL, 1: self.SC_MARGIN_SYMBOL, 2: self.SC_MARGIN_NUMBER}
        self._margin_widths: dict[int, int] = {0: 14, 1: 14, 2: -1}
        self._line_states: dict[int, int] = {}
        self._virtual_first_visible_line = 0
        self._x_offset = 0
        self._scroll_width = 1
        self._scroll_width_tracking = False
        self._x_caret_policy = (0, 0)
        self._y_caret_policy = (0, 0)
        self._visible_policy = (0, 0)
        self._caret_period_ms = 500
        self._mouse_dwell_time_ms = 1000
        self._zoom = 0
        self._edge_mode = 0
        self._edge_column = 80
        self._edge_colour = QColor("#404040")
        self._print_wrap_mode = 0
        self._extra_ascent = 0
        self._extra_descent = 0
        self._caret_sticky = 0
        self._paste_convert_endings = False
        self._virtual_space_options = 0
        self._status = 0
        self._mod_event_mask = 0
        self._buffered_draw = True
        self._two_phase_draw = 0
        self._layout_cache = 1
        self._whitespace_fore = QColor("#6b7280")
        self._whitespace_back = QColor("#000000")
        self._whitespace_size = 1
        self._extra_font_flag = 0
        self._end_at_last_line = True
        self._punctuation_chars = ""
        self._word_chars = ""
        self._line_end_types_allowed = 0
        self._accessibility = 0
        self._bidirectional = 0
        self._idle_styling = 0
        self._sel_alpha = 256
        self._additional_sel_alpha = 256
        self._sel_eol_filled = False
        self._font_locale = ""
        self._keys_unicode = True
        self._auto_case_sensitive = False
        self._auto_max_height = 8
        self._auto_max_width = 0
        self._auto_drop_rest_of_word = False
        self._auto_hide = True
        self._auto_cancel_at_start = True
        self._auto_current = 0
        self._caret_line_frame = 0
        self._caret_line_visible_always = False
        self._h_scrollbar = True
        self._v_scrollbar = True
        self._caret_fore_colour = QColor("#ffffff")
        self._caret_style = 1
        self._additional_caret_fore = QColor("#ffffff")
        self._additional_sel_fore = QColor("#ffffff")
        self._additional_sel_back = QColor("#4a90e2")
        self._additional_carets_blink = True
        self._additional_carets_visible = True
        self._hotspot_active_back = QColor("#2b3a4a")
        self._hotspot_single_line = True
        self._indicator_current = 0
        self._indicator_value_current = 0
        self._indicator_styles: dict[int, int] = {}
        self._indicator_colors: dict[int, QColor] = {}
        self._indicator_ranges: dict[int, list[IndicatorRange]] = {}
        self._hotspot_ranges: list[HotspotRange] = []
        self._hotspot_color = QColor("#4fa3ff")
        self._hotspot_underline = True
        self._hotspot_active_color = QColor("#8fd0ff")
        self._active_hotspot_index = -1
        self._active_indicator_hit: tuple[int, int] | None = None
        self._margin_marker_masks: dict[int, int] = {0: -1}
        self._margin_left_padding = 8
        self._margin_right_padding = 4
        self._margin_bg_color = QColor("#202228")
        self._margin_fg_color = QColor("#8f95a1")
        self._caret_line_visible = True
        self._caret_line_color = QColor("#2f3640")
        self._style_current_pos = 0
        self._style_bits = 8
        self._style_formats: dict[int, QTextCharFormat] = {}
        self._style_ranges: list[tuple[int, int, int]] = []
        self._lexer_ranges: list[tuple[int, int, int]] = []
        self._background_overlays: dict[str, list[tuple[int, int, QColor]]] = {}
        self._target_start = 0
        self._target_end = 0
        self._search_flags = 0
        self._last_regex_match = None
        self._main_selection_index = 0
        self._rebuild_pending = False
        self._rebuild_timer = QTimer(self)
        self._rebuild_timer.setSingleShot(True)
        self._rebuild_timer.setInterval(12)
        self._rebuild_timer.timeout.connect(self._flush_deferred_rebuild)

        self._margin = _MarginArea(self)
        self.blockCountChanged.connect(self._update_margin_width)
        self.updateRequest.connect(self._update_margin_area)
        self.textChanged.connect(self._on_text_changed)
        self.cursorPositionChanged.connect(self._on_cursor_changed)
        self._update_margin_width(0)
        self._rebuild_fold_regions()
        self._refresh_extra_selections()

    # Minimal text API parity with QsciScintilla.
    def text(self, line: int | None = None) -> str:
        if line is None:
            return self.toPlainText()
        block = self.document().findBlockByNumber(int(line))
        return block.text() if block.isValid() else ""

    def setText(self, text: str) -> None:
        self.setPlainText(text)

    def insertAt(self, text: str, line: int, index: int) -> None:
        pos = self._index_from_line_col(int(line), int(index))
        cursor = self.textCursor()
        cursor.setPosition(pos)
        cursor.insertText(text)
        self.setTextCursor(cursor)

    def getCursorPosition(self) -> tuple[int, int]:
        cursor = self.textCursor()
        return cursor.blockNumber(), cursor.columnNumber()

    def setCursorPosition(self, line: int, index: int) -> None:
        pos = self._index_from_line_col(int(line), int(index))
        cursor = self.textCursor()
        cursor.setPosition(pos)
        self.setTextCursor(cursor)

    def hasSelectedText(self) -> bool:
        return self.textCursor().hasSelection()

    def selectedText(self) -> str:
        return self.textCursor().selectedText().replace("\u2029", "\n")

    def replaceSelectedText(self, text: str) -> None:
        cursor = self.textCursor()
        cursor.insertText(text)
        self.setTextCursor(cursor)

    def setSelection(self, line1: int, index1: int, line2: int, index2: int) -> None:
        start = self._index_from_line_col(int(line1), int(index1))
        end = self._index_from_line_col(int(line2), int(index2))
        cursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)

    def getSelection(self) -> tuple[int, int, int, int]:
        cursor = self.textCursor()
        if not cursor.hasSelection():
            line, col = self.getCursorPosition()
            return line, col, line, col
        start = min(cursor.selectionStart(), cursor.selectionEnd())
        end = max(cursor.selectionStart(), cursor.selectionEnd())
        start_block = self.document().findBlock(start)
        end_block = self.document().findBlock(max(start, end - 1))
        return (
            start_block.blockNumber(),
            start - start_block.position(),
            end_block.blockNumber(),
            end - end_block.position(),
        )

    def isModified(self) -> bool:
        return bool(self.document().isModified())

    def setModified(self, value: bool) -> None:
        self.document().setModified(bool(value))

    def setWrapMode(self, mode: int) -> None:
        self._wrap_mode = self.WrapWord if int(mode) == self.WrapWord else self.WrapNone
        self.setLineWrapMode(self.WidgetWidth if self._wrap_mode == self.WrapWord else self.NoWrap)

    def setTabWidth(self, width: int) -> None:
        self._indent_width = max(1, int(width))

    def setIndentationWidth(self, width: int) -> None:
        self._indent_width = max(1, int(width))

    def setIndentationsUseTabs(self, value: bool) -> None:
        self._use_tabs = bool(value)

    def setRectangularSelectionModifier(self, modifier: int) -> None:
        self._rectangular_selection_modifier = int(modifier)
        if self._rectangular_selection_modifier == self.SCMOD_ALT:
            self._column_mode = True
        if self._rectangular_selection_modifier == 0:
            self._column_mode = False

    def setMultipleSelectionEnabled(self, value: bool) -> None:
        self._multiple_selection_enabled = bool(value)
        if not self._multiple_selection_enabled:
            self._additional_carets = []
            self.viewport().update()

    def setAdditionalSelectionTyping(self, value: bool) -> None:
        self._additional_selection_typing = bool(value)

    def setMultiPaste(self, value: bool) -> None:
        self._multi_paste = bool(value)

    def setFolding(self, style: int) -> None:
        self._folding_enabled = int(style) != self.NoFoldStyle
        if not self._folding_enabled:
            self._collapsed_headers.clear()
            self._fold_hidden_lines.clear()
            self._refresh_visibility()
        self._margin.update()

    def setAutoCompletionSource(self, source: int) -> None:
        self._auto_completion_source = int(source)
        self._refresh_completion_words()

    def setAutoCompletionThreshold(self, threshold: int) -> None:
        self._auto_completion_threshold = int(threshold)

    def setAutoCompletionCaseSensitivity(self, value: bool) -> None:
        self._auto_completion_case_sensitive = bool(value)
        self._completer.setCaseSensitivity(Qt.CaseSensitive if self._auto_completion_case_sensitive else Qt.CaseInsensitive)

    def setAutoCompletionUseSingle(self, value: bool) -> None:
        self._auto_completion_use_single = bool(value)

    def setAPIs(self, apis) -> None:
        self._apis = apis
        self._refresh_completion_words()

    def set_auto_completion_words(self, words: list[str]) -> None:
        self._completion_words = sorted({str(word).strip() for word in words if str(word).strip()})
        self._refresh_completion_words()

    def isUndoAvailable(self) -> bool:
        return bool(self.document().isUndoAvailable())

    def isRedoAvailable(self) -> bool:
        return bool(self.document().isRedoAvailable())

    def deleteBack(self) -> None:
        if self._multiple_selection_enabled and self._additional_selection_typing and self._additional_carets:
            self._delete_at_all_carets(backward=True)
            return
        cursor = self.textCursor()
        if cursor.hasSelection():
            cursor.removeSelectedText()
        else:
            cursor.deletePreviousChar()
        self.setTextCursor(cursor)

    def deleteChar(self) -> None:
        if self._multiple_selection_enabled and self._additional_selection_typing and self._additional_carets:
            self._delete_at_all_carets(backward=False)
            return
        cursor = self.textCursor()
        if cursor.hasSelection():
            cursor.removeSelectedText()
        else:
            cursor.deleteChar()
        self.setTextCursor(cursor)

    def annotationSetText(self, line: int, text: str) -> None:
        ln = max(0, int(line))
        self._annotations[ln] = str(text)
        self.viewport().update()

    def annotationClearAll(self) -> None:
        self._annotations.clear()
        self.viewport().update()

    def callTipShow(self, pos: int, text: str) -> None:
        cursor = QTextCursor(self.document())
        cursor.setPosition(max(0, min(int(pos), len(self.toPlainText()))))
        rect = self.cursorRect(cursor)
        point = self.viewport().mapToGlobal(rect.bottomRight())
        QToolTip.showText(point, str(text), self)

    def callTipCancel(self) -> None:
        QToolTip.hideText()

    def setMarginSensitivity(self, margin: int, sensitive: bool) -> None:
        self._margin_sensitive[int(margin)] = bool(sensitive)

    def setMarginType(self, margin: int, margin_type: int) -> None:
        self._margin_types[int(margin)] = int(margin_type)
        self._update_margin_width(0)
        self._margin.update()

    def setMarginWidth(self, margin: int, width: int) -> None:
        self._margin_widths[int(margin)] = int(width)
        self._update_margin_width(0)
        self._margin.update()

    def setMarginLeft(self, width: int) -> None:
        self._margin_left_padding = max(0, int(width))
        self._update_margin_width(0)
        self._margin.update()

    def setMarginRight(self, width: int) -> None:
        self._margin_right_padding = max(0, int(width))
        self._update_margin_width(0)
        self._margin.update()

    def setMarginMarkerMask(self, margin: int, mask: int) -> None:
        self._margin_marker_masks[int(margin)] = int(mask)
        self._margin.update()

    def setCaretWidth(self, width: int) -> None:
        self.setCursorWidth(max(1, int(width)))

    def setCaretLineVisible(self, visible: bool) -> None:
        self._caret_line_visible = bool(visible)
        self._refresh_extra_selections()

    def setCaretLineBackgroundColor(self, color) -> None:
        if isinstance(color, QColor):
            self._caret_line_color = QColor(color)
        else:
            self._caret_line_color = QColor(str(color))
        self._refresh_extra_selections()

    def setMarginsBackgroundColor(self, color) -> None:
        if isinstance(color, QColor):
            self._margin_bg_color = QColor(color)
        else:
            self._margin_bg_color = QColor(str(color))
        self._margin.update()

    def setMarginsForegroundColor(self, color) -> None:
        if isinstance(color, QColor):
            self._margin_fg_color = QColor(color)
        else:
            self._margin_fg_color = QColor(str(color))
        self._margin.update()

    def setFoldMarginColors(self, foreground, background) -> None:
        self.setMarginsForegroundColor(foreground)
        self.setMarginsBackgroundColor(background)

    def indicatorDefine(self, style: int, indicator: int) -> int:
        idx = max(0, int(indicator))
        self._indicator_styles[idx] = int(style)
        if idx not in self._indicator_colors:
            self._indicator_colors[idx] = QColor("#f4d03f")
        return idx

    def setIndicatorForegroundColor(self, color, indicator: int) -> None:
        idx = max(0, int(indicator))
        if isinstance(color, QColor):
            self._indicator_colors[idx] = color
        else:
            self._indicator_colors[idx] = QColor(str(color))
        self._refresh_extra_selections()

    def setIndicatorCurrent(self, indicator: int) -> None:
        self._indicator_current = max(0, int(indicator))

    def setIndicatorValue(self, value: int) -> None:
        self._indicator_value_current = int(value)

    def indicatorFillRange(self, position: int, length: int) -> None:
        pos = max(0, int(position))
        end = max(pos, pos + max(0, int(length)))
        ranges = self._indicator_ranges.setdefault(self._indicator_current, [])
        ranges.append(
            IndicatorRange(
                start=pos,
                end=end,
                payload=str(self._indicator_value_current),
                value=int(self._indicator_value_current),
            )
        )
        self._refresh_extra_selections()

    def indicatorClearRange(self, position: int, length: int) -> None:
        pos = max(0, int(position))
        end = max(pos, pos + max(0, int(length)))
        for key in list(self._indicator_ranges.keys()):
            kept: list[IndicatorRange] = []
            for seg in self._indicator_ranges.get(key, []):
                lo = int(seg.start)
                hi = int(seg.end)
                if hi <= pos or lo >= end:
                    kept.append(seg)
                    continue
                if lo < pos:
                    kept.append(IndicatorRange(start=lo, end=pos, payload=seg.payload, value=seg.value))
                if hi > end:
                    kept.append(IndicatorRange(start=end, end=hi, payload=seg.payload, value=seg.value))
            self._indicator_ranges[key] = kept
        if self._active_indicator_hit is not None:
            aid, aidx = self._active_indicator_hit
            current = self._indicator_ranges.get(aid, [])
            if aidx >= len(current):
                self._active_indicator_hit = None
        self._refresh_extra_selections()

    def addIndicatorRange(self, start: int, end: int, *, indicator: int | None = None, payload: str = "", value: int = 0) -> None:
        idx = self._indicator_current if indicator is None else max(0, int(indicator))
        lo = max(0, min(int(start), int(end)))
        hi = max(0, max(int(start), int(end)))
        if hi <= lo:
            return
        self._indicator_ranges.setdefault(idx, []).append(
            IndicatorRange(start=lo, end=hi, payload=str(payload), value=int(value))
        )
        self._refresh_extra_selections()

    def clearHotspots(self) -> None:
        self._hotspot_ranges = []
        self._active_hotspot_index = -1
        self._refresh_extra_selections()

    def addHotspotRange(self, start: int, end: int, payload: str = "") -> None:
        lo = max(0, min(int(start), int(end)))
        hi = max(0, max(int(start), int(end)))
        if hi <= lo:
            return
        self._hotspot_ranges.append(HotspotRange(start=lo, end=hi, payload=str(payload)))
        self._refresh_extra_selections()

    def set_background_overlays(self, channel: str, ranges: list[tuple[int, int, QColor | str]]) -> None:
        key = str(channel or "").strip().lower()
        if not key:
            return
        clean: list[tuple[int, int, QColor]] = []
        doc_len = len(self.toPlainText())
        for start, end, color in ranges:
            lo = max(0, min(int(start), int(end)))
            hi = max(0, max(int(start), int(end)))
            if hi <= lo:
                continue
            if lo >= doc_len:
                continue
            qcolor = color if isinstance(color, QColor) else QColor(str(color))
            if not qcolor.isValid():
                continue
            clean.append((lo, min(hi, doc_len), qcolor))
        self._background_overlays[key] = clean
        self._refresh_extra_selections()

    def clear_background_overlays(self, channel: str | None = None) -> None:
        if channel is None:
            if not self._background_overlays:
                return
            self._background_overlays = {}
            self._refresh_extra_selections()
            return
        key = str(channel or "").strip().lower()
        if not key:
            return
        if key in self._background_overlays:
            self._background_overlays.pop(key, None)
            self._refresh_extra_selections()

    def setHotspotStyle(self, *, color: QColor | str | None = None, underline: bool | None = None) -> None:
        if color is not None:
            self._hotspot_color = color if isinstance(color, QColor) else QColor(str(color))
        if underline is not None:
            self._hotspot_underline = bool(underline)
        self._refresh_extra_selections()

    def _hotspot_index_at_pos(self, pos: int) -> int:
        for idx, hs in enumerate(self._hotspot_ranges):
            if hs.start <= pos < hs.end:
                return idx
        return -1

    def _indicator_hit_at_pos(self, pos: int) -> tuple[int, int] | None:
        for indic_id, ranges in self._indicator_ranges.items():
            for idx, seg in enumerate(ranges):
                if int(seg.start) <= pos < int(seg.end):
                    return int(indic_id), int(idx)
        return None

    def styleSetFore(self, style_id: int, color: QColor | str) -> None:
        fmt = self._style_formats.get(int(style_id), QTextCharFormat())
        fmt.setForeground(color if isinstance(color, QColor) else QColor(str(color)))
        self._style_formats[int(style_id)] = fmt
        self._refresh_extra_selections()

    def styleSetBack(self, style_id: int, color: QColor | str) -> None:
        fmt = self._style_formats.get(int(style_id), QTextCharFormat())
        fmt.setBackground(color if isinstance(color, QColor) else QColor(str(color)))
        self._style_formats[int(style_id)] = fmt
        self._refresh_extra_selections()

    def styleClearAll(self) -> None:
        self._style_formats.clear()
        self._style_ranges = []
        self._refresh_extra_selections()

    def styleSetBold(self, style_id: int, bold: bool) -> None:
        fmt = self._style_formats.get(int(style_id), QTextCharFormat())
        fmt.setFontWeight(75 if bool(bold) else 50)
        self._style_formats[int(style_id)] = fmt
        self._refresh_extra_selections()

    def styleSetItalic(self, style_id: int, italic: bool) -> None:
        fmt = self._style_formats.get(int(style_id), QTextCharFormat())
        fmt.setFontItalic(bool(italic))
        self._style_formats[int(style_id)] = fmt
        self._refresh_extra_selections()

    def styleSetUnderline(self, style_id: int, underline: bool) -> None:
        fmt = self._style_formats.get(int(style_id), QTextCharFormat())
        fmt.setFontUnderline(bool(underline))
        self._style_formats[int(style_id)] = fmt
        self._refresh_extra_selections()

    def startStyling(self, position: int) -> None:
        self._style_current_pos = max(0, int(position))

    def setStyling(self, length: int, style_id: int) -> None:
        if int(length) <= 0:
            return
        lo = self._style_current_pos
        hi = lo + int(length)
        self._style_ranges.append((lo, hi, int(style_id)))
        self._style_current_pos = hi
        self._refresh_extra_selections()

    def lexer(self):
        return self._lexer

    def setLexer(self, lexer) -> None:
        self._lexer = lexer
        self._rebuild_lexer_ranges()
        self._refresh_extra_selections()

    def set_column_mode(self, value: bool) -> None:
        self._column_mode = bool(value)
        if not self._column_mode:
            self._clear_multi_ranges()

    def foldAll(self, expand: bool) -> None:
        if not self._folding_enabled:
            return
        self._rebuild_fold_regions()
        if expand:
            self._collapsed_headers.clear()
            self._fold_hidden_lines.clear()
            self._refresh_visibility()
            return
        self._collapsed_headers = set(self._fold_regions.keys())
        self._rebuild_fold_hidden_lines()
        self._refresh_visibility()

    def fold_level(self, level: int, expand: bool) -> None:
        if not self._folding_enabled:
            return
        self._rebuild_fold_regions()
        target = max(0, int(level) - 1)
        for header, region in self._fold_regions.items():
            if region.level != target:
                continue
            if expand:
                self._collapsed_headers.discard(header)
            else:
                self._collapsed_headers.add(header)
        self._rebuild_fold_hidden_lines()
        self._refresh_visibility()

    def fold_line(self, line: int, expand: bool) -> None:
        if not self._folding_enabled:
            return
        self._rebuild_fold_regions()
        region = self._fold_regions.get(int(line))
        if region is None:
            return
        if expand:
            self._collapsed_headers.discard(region.start)
        else:
            self._collapsed_headers.add(region.start)
        self._rebuild_fold_hidden_lines()
        self._refresh_visibility()

    def lines(self) -> int:
        return max(1, self.document().blockCount())

    def markerDefine(self, symbol: int) -> int:
        marker_id = self._next_marker_id
        self._next_marker_id += 1
        self._markers.setdefault(marker_id, set())
        self._marker_symbols[marker_id] = int(symbol)
        return marker_id

    def setMarkerBackgroundColor(self, color, marker_id: int) -> None:
        if isinstance(color, QColor):
            self._marker_colors[int(marker_id)] = color
        else:
            self._marker_colors[int(marker_id)] = QColor(str(color))
        self._margin.update()

    def markerDeleteAll(self, marker_id: int) -> None:
        self._markers[int(marker_id)] = set()
        self._margin.update()

    def markerAdd(self, line: int, marker_id: int) -> None:
        self._markers.setdefault(int(marker_id), set()).add(max(0, int(line)))
        self._margin.update()

    def markerDelete(self, line: int, marker_id: int) -> None:
        self._markers.setdefault(int(marker_id), set()).discard(max(0, int(line)))
        self._margin.update()

    def hide_lines(self, start_line: int, end_line: int) -> bool:
        lo = min(int(start_line), int(end_line))
        hi = max(int(start_line), int(end_line))
        for line in range(lo, hi + 1):
            self._hidden_lines.add(line)
        self._refresh_visibility()
        return True

    def show_all_hidden_lines(self) -> bool:
        had_hidden = bool(self._hidden_lines or self._fold_hidden_lines or self._collapsed_headers)
        self._hidden_lines.clear()
        self._fold_hidden_lines.clear()
        self._collapsed_headers.clear()
        self._refresh_visibility()
        return had_hidden

    def show_lines(self, start_line: int, end_line: int) -> bool:
        lo = min(int(start_line), int(end_line))
        hi = max(int(start_line), int(end_line))
        if hi < lo:
            return False
        changed = False
        for line in range(lo, hi + 1):
            if line in self._hidden_lines:
                self._hidden_lines.discard(line)
                changed = True
        if changed:
            self._refresh_visibility()
        return changed

    def send_scintilla_named(self, command_name: str, *args: int) -> bool:
        command = str(command_name).strip().upper()
        if command == "SCI_HIDELINES" and len(args) >= 2:
            return self.hide_lines(int(args[0]), int(args[1]))
        if command == "SCI_SHOWLINES" and len(args) >= 2:
            return self.show_lines(int(args[0]), int(args[1]))
        if command == "SCI_SETSELECTIONMODE" and len(args) >= 1:
            self.set_column_mode(int(args[0]) == self.SC_SEL_RECTANGLE)
            return True
        if command == "SCI_SETMULTIPLESELECTION" and len(args) >= 1:
            self.setMultipleSelectionEnabled(bool(args[0]))
            return True
        if command == "SCI_SETADDITIONALSELECTIONTYPING" and len(args) >= 1:
            self.setAdditionalSelectionTyping(bool(args[0]))
            return True
        if command == "SCI_SETMULTIPASTE" and len(args) >= 1:
            self.setMultiPaste(bool(args[0]))
            return True
        if command == "SCI_SETVIEWWS" and len(args) >= 1:
            self._view_whitespace = bool(int(args[0]))
            self.viewport().update()
            return True
        if command == "SCI_SETVIEWEOL" and len(args) >= 1:
            self._view_eol = bool(int(args[0]))
            self.viewport().update()
            return True
        if command == "SCI_SETCONTROLCHARSYMBOL" and len(args) >= 1:
            self._control_char_symbol = int(args[0])
            self._view_control_chars = bool(self._control_char_symbol)
            self.viewport().update()
            return True
        if command == "SCI_SETMARGINSENSITIVEN" and len(args) >= 2:
            self.setMarginSensitivity(int(args[0]), bool(int(args[1])))
            return True
        if command == "SCI_SETMARGINTYPEN" and len(args) >= 2:
            self.setMarginType(int(args[0]), int(args[1]))
            return True
        if command == "SCI_SETMARGINWIDTHN" and len(args) >= 2:
            self.setMarginWidth(int(args[0]), int(args[1]))
            return True
        if command == "SCI_SETMARGINLEFT" and len(args) >= 1:
            self.setMarginLeft(int(args[0]))
            return True
        if command == "SCI_SETMARGINRIGHT" and len(args) >= 1:
            self.setMarginRight(int(args[0]))
            return True
        if command == "SCI_SETMARGINMASKN" and len(args) >= 2:
            self.setMarginMarkerMask(int(args[0]), int(args[1]))
            return True
        if command == "SCI_SETCARETWIDTH" and len(args) >= 1:
            self.setCaretWidth(int(args[0]))
            return True
        if command == "SCI_SETCARETLINEVISIBLE" and len(args) >= 1:
            self.setCaretLineVisible(bool(int(args[0])))
            return True
        if command == "SCI_SETINDICATORCURRENT" and len(args) >= 1:
            self.setIndicatorCurrent(int(args[0]))
            return True
        if command == "SCI_SETINDICATORVALUE" and len(args) >= 1:
            self.setIndicatorValue(int(args[0]))
            return True
        if command == "SCI_INDICSETSTYLE" and len(args) >= 2:
            self.indicatorDefine(int(args[1]), int(args[0]))
            return True
        if command == "SCI_INDICSETFORE" and len(args) >= 2:
            self.setIndicatorForegroundColor(self._qcolor_from_scintilla_rgb(int(args[1])), int(args[0]))
            return True
        if command == "SCI_INDICATORFILLRANGE" and len(args) >= 2:
            self.indicatorFillRange(int(args[0]), int(args[1]))
            return True
        if command == "SCI_INDICATORCLEARRANGE" and len(args) >= 2:
            self.indicatorClearRange(int(args[0]), int(args[1]))
            return True
        if command == "SCI_SETHOTSPOTACTIVEFORE" and len(args) >= 2:
            color = self._qcolor_from_scintilla_rgb(int(args[1]))
            self.setHotspotStyle(color=color)
            self._hotspot_active_color = color.lighter(130)
            return True
        if command == "SCI_SETHOTSPOTACTIVEUNDERLINE" and len(args) >= 1:
            self.setHotspotStyle(underline=bool(int(args[0])))
            return True
        if command == "SCI_STYLESETFORE" and len(args) >= 2:
            self.styleSetFore(int(args[0]), self._qcolor_from_scintilla_rgb(int(args[1])))
            return True
        if command == "SCI_STYLESETBACK" and len(args) >= 2:
            self.styleSetBack(int(args[0]), self._qcolor_from_scintilla_rgb(int(args[1])))
            return True
        if command == "SCI_STYLECLEARALL":
            self.styleClearAll()
            return True
        if command == "SCI_STYLESETBOLD" and len(args) >= 2:
            self.styleSetBold(int(args[0]), bool(int(args[1])))
            return True
        if command == "SCI_STYLESETITALIC" and len(args) >= 2:
            self.styleSetItalic(int(args[0]), bool(int(args[1])))
            return True
        if command == "SCI_STYLESETUNDERLINE" and len(args) >= 2:
            self.styleSetUnderline(int(args[0]), bool(int(args[1])))
            return True
        if command == "SCI_STARTSTYLING" and len(args) >= 1:
            self.startStyling(int(args[0]))
            return True
        if command == "SCI_SETSTYLING" and len(args) >= 2:
            self.setStyling(int(args[0]), int(args[1]))
            return True
        if command == "SCI_SETINDENTATIONGUIDES" and len(args) >= 1:
            self._show_indent_guides = bool(int(args[0]))
            self.viewport().update()
            return True
        if command == "SCI_SETWRAPVISUALFLAGS" and len(args) >= 1:
            self._show_wrap_symbol = bool(int(args[0]))
            self.viewport().update()
            return True
        if command == "SCI_SETCARETLINEBACK" and len(args) >= 1:
            self.setCaretLineBackgroundColor(self._qcolor_from_scintilla_rgb(int(args[0])))
            return True
        if command == "SCI_SETSELBACK" and len(args) >= 2:
            pal = self.palette()
            pal.setColor(QPalette.Highlight, self._qcolor_from_scintilla_rgb(int(args[1])))
            self.setPalette(pal)
            self.viewport().update()
            return True
        if command == "SCI_SETSELFORE" and len(args) >= 2:
            pal = self.palette()
            pal.setColor(QPalette.HighlightedText, self._qcolor_from_scintilla_rgb(int(args[1])))
            self.setPalette(pal)
            self.viewport().update()
            return True
        if command == "SCI_BRACEHIGHLIGHT" and len(args) >= 2:
            self._brace_match_pair = (int(args[0]), int(args[1]))
            self.viewport().update()
            return True
        if command == "SCI_BRACEBADLIGHT" and len(args) >= 1:
            self._brace_match_pair = (int(args[0]), int(args[0]))
            self.viewport().update()
            return True
        if command == "SCI_FOLDALL" and len(args) >= 1:
            self.foldAll(bool(int(args[0])))
            return True
        if command == "SCI_FOLDLINE" and len(args) >= 2:
            self.fold_line(int(args[0]), bool(int(args[1])))
            return True
        return False

    def SendScintilla(self, command, *args: int) -> int:
        msg = int(command)
        numeric_setters: dict[int, tuple[str, int]] = {
            int(self.SCI_SETMARGINLEFT): ("SCI_SETMARGINLEFT", 1),
            int(self.SCI_SETMARGINRIGHT): ("SCI_SETMARGINRIGHT", 1),
            int(self.SCI_SETCARETWIDTH): ("SCI_SETCARETWIDTH", 1),
            int(self.SCI_SETCARETLINEVISIBLE): ("SCI_SETCARETLINEVISIBLE", 1),
            int(self.SCI_SETCARETLINEBACK): ("SCI_SETCARETLINEBACK", 1),
            int(self.SCI_SETSELBACK): ("SCI_SETSELBACK", 2),
            int(self.SCI_SETSELFORE): ("SCI_SETSELFORE", 2),
            int(self.SCI_SETVIEWWS): ("SCI_SETVIEWWS", 1),
            int(self.SCI_SETVIEWEOL): ("SCI_SETVIEWEOL", 1),
            int(self.SCI_SETCONTROLCHARSYMBOL): ("SCI_SETCONTROLCHARSYMBOL", 1),
            int(self.SCI_SETINDENTATIONGUIDES): ("SCI_SETINDENTATIONGUIDES", 1),
            int(self.SCI_SETWRAPVISUALFLAGS): ("SCI_SETWRAPVISUALFLAGS", 1),
            int(self.SCI_SETSELECTIONMODE): ("SCI_SETSELECTIONMODE", 1),
            int(self.SCI_SETMULTIPLESELECTION): ("SCI_SETMULTIPLESELECTION", 1),
            int(self.SCI_SETADDITIONALSELECTIONTYPING): ("SCI_SETADDITIONALSELECTIONTYPING", 1),
            int(self.SCI_SETMULTIPASTE): ("SCI_SETMULTIPASTE", 1),
            int(self.SCI_SETINDICATORCURRENT): ("SCI_SETINDICATORCURRENT", 1),
            int(self.SCI_SETINDICATORVALUE): ("SCI_SETINDICATORVALUE", 1),
            int(self.SCI_INDICSETSTYLE): ("SCI_INDICSETSTYLE", 2),
            int(self.SCI_INDICSETFORE): ("SCI_INDICSETFORE", 2),
            int(self.SCI_INDICATORFILLRANGE): ("SCI_INDICATORFILLRANGE", 2),
            int(self.SCI_INDICATORCLEARRANGE): ("SCI_INDICATORCLEARRANGE", 2),
            int(self.SCI_STYLESETFORE): ("SCI_STYLESETFORE", 2),
            int(self.SCI_STYLESETBACK): ("SCI_STYLESETBACK", 2),
            int(self.SCI_STYLESETBOLD): ("SCI_STYLESETBOLD", 2),
            int(self.SCI_STYLESETITALIC): ("SCI_STYLESETITALIC", 2),
            int(self.SCI_STYLESETUNDERLINE): ("SCI_STYLESETUNDERLINE", 2),
            int(self.SCI_STYLECLEARALL): ("SCI_STYLECLEARALL", 0),
            int(self.SCI_STARTSTYLING): ("SCI_STARTSTYLING", 1),
            int(self.SCI_SETSTYLING): ("SCI_SETSTYLING", 2),
            int(self.SCI_FOLDALL): ("SCI_FOLDALL", 1),
            int(self.SCI_FOLDLINE): ("SCI_FOLDLINE", 2),
        }
        mapped = numeric_setters.get(msg)
        if mapped is not None:
            command_name, min_args = mapped
            if len(args) < min_args:
                return 0
            return 1 if self.send_scintilla_named(command_name, *args) else 0
        if msg == int(self.SCI_GETLINECOUNT):
            return max(1, int(self.blockCount()))
        if msg == int(self.SCI_GETTEXTLENGTH):
            return int(len(self.toPlainText()))
        if msg == int(self.SCI_GETLINE):
            line = max(0, int(args[0]) if args else 0)
            block = self.document().findBlockByNumber(line)
            if not block.isValid():
                return 0
            payload = block.text() + "\n"
            if len(args) >= 3:
                max_len = max(0, int(args[1]))
                clipped = payload[: max(0, max_len - 1)] if max_len else ""
                self._write_scintilla_text_target(args[2], clipped, max_len=max_len)
                return len(clipped)
            return len(payload)
        if msg == int(self.SCI_SETLINESTATE):
            if len(args) < 2:
                return 0
            line = max(0, int(args[0]))
            value = int(args[1])
            self._line_states[line] = value
            return int(value)
        if msg == int(self.SCI_GETLINESTATE):
            line = max(0, int(args[0]) if args else 0)
            return int(self._line_states.get(line, 0))
        if msg == int(self.SCI_GETMAXLINESTATE):
            if not self._line_states:
                return 0
            return int(max(self._line_states.values()))
        if msg == int(self.SCI_POSITIONFROMLINE):
            line = max(0, int(args[0]) if args else 0)
            block = self.document().findBlockByNumber(line)
            if not block.isValid():
                return int(len(self.toPlainText()))
            return int(block.position())
        if msg == int(self.SCI_GETLINEENDPOSITION):
            line = max(0, int(args[0]) if args else 0)
            block = self.document().findBlockByNumber(line)
            if not block.isValid():
                return int(len(self.toPlainText()))
            return int(block.position() + len(block.text()))
        if msg == int(self.SCI_LINELENGTH):
            line = max(0, int(args[0]) if args else 0)
            block = self.document().findBlockByNumber(line)
            if not block.isValid():
                return 0
            return int(len(block.text()))
        if msg == int(self.SCI_GETCHARAT):
            pos = max(0, int(args[0]) if args else 0)
            text = self.toPlainText()
            if pos < 0 or pos >= len(text):
                return 0
            return int(ord(text[pos]))
        if msg == int(self.SCI_GETSTYLEAT):
            pos = max(0, int(args[0]) if args else 0)
            return int(self._style_at_pos(pos))
        if msg == int(self.SCI_SETTABWIDTH):
            width = max(1, int(args[0])) if args else 4
            self.setTabWidth(width)
            return int(width)
        if msg == int(self.SCI_GETTABWIDTH):
            return int(self._indent_width)
        if msg == int(self.SCI_SETUSETABS):
            value = bool(int(args[0])) if args else False
            self.setIndentationsUseTabs(value)
            return 1 if value else 0
        if msg == int(self.SCI_GETUSETABS):
            return 1 if self._use_tabs else 0
        if msg == int(self.SCI_SETINDENT):
            width = max(1, int(args[0])) if args else 4
            self.setIndentationWidth(width)
            return int(width)
        if msg == int(self.SCI_GETINDENT):
            return int(self._indent_width)
        if msg == int(self.SCI_GETMARGINLEFT):
            return int(self._margin_left_padding)
        if msg == int(self.SCI_GETMARGINRIGHT):
            return int(self._margin_right_padding)
        if msg == int(self.SCI_SETWRAPMODE):
            mode = int(args[0]) if args else self.WrapNone
            self.setWrapMode(mode)
            return int(self._wrap_mode)
        if msg == int(self.SCI_GETWRAPMODE):
            return int(self._wrap_mode)
        if msg == int(self.SCI_GETCARETWIDTH):
            return int(self.cursorWidth())
        if msg == int(self.SCI_GETVIEWWS):
            return 1 if self._view_whitespace else 0
        if msg == int(self.SCI_GETVIEWEOL):
            return 1 if self._view_eol else 0
        if msg == int(self.SCI_GETCONTROLCHARSYMBOL):
            return int(self._control_char_symbol)
        if msg == int(self.SCI_GETINDENTATIONGUIDES):
            return 1 if self._show_indent_guides else 0
        if msg == int(self.SCI_GETWRAPVISUALFLAGS):
            return 1 if self._show_wrap_symbol else 0
        if msg == int(self.SCI_MARKERGET):
            line = max(0, int(args[0]) if args else 0)
            return int(self._marker_mask_for_line(line))
        if msg == int(self.SCI_MARKERNEXT):
            if len(args) < 2:
                return -1
            line = max(0, int(args[0]))
            mask = int(args[1])
            return int(self._marker_next_line(line, mask))
        if msg == int(self.SCI_MARKERPREVIOUS):
            if len(args) < 2:
                return -1
            line = max(0, int(args[0]))
            mask = int(args[1])
            return int(self._marker_previous_line(line, mask))
        if msg == int(self.SCI_GETCOLUMN):
            pos = max(0, int(args[0]) if args else 0)
            _line, col = self._line_col_from_pos(pos)
            return int(col)
        if msg == int(self.SCI_POSITIONBEFORE):
            pos = max(0, min(int(args[0]) if args else 0, len(self.toPlainText())))
            return int(max(0, pos - 1))
        if msg == int(self.SCI_POSITIONAFTER):
            pos = max(0, min(int(args[0]) if args else 0, len(self.toPlainText())))
            return int(min(len(self.toPlainText()), pos + 1))
        if msg == int(self.SCI_LINESCROLL):
            cols = int(args[0]) if len(args) >= 1 else 0
            lines = int(args[1]) if len(args) >= 2 else 0
            self._x_offset = max(0, int(self._x_offset + cols))
            self._virtual_first_visible_line = max(0, int(self._virtual_first_visible_line + lines))
            return int(self._virtual_first_visible_line)
        if msg == int(self.SCI_SETFIRSTVISIBLELINE):
            line = max(0, int(args[0]) if args else 0)
            self._virtual_first_visible_line = line
            return int(line)
        if msg == int(self.SCI_SETXOFFSET):
            off = max(0, int(args[0]) if args else 0)
            self._x_offset = off
            return int(off)
        if msg == int(self.SCI_GETXOFFSET):
            return int(self._x_offset)
        if msg == int(self.SCI_SETSCROLLWIDTH):
            width = max(1, int(args[0]) if args else 1)
            self._scroll_width = width
            return int(width)
        if msg == int(self.SCI_GETSCROLLWIDTH):
            return int(self._scroll_width)
        if msg == int(self.SCI_SETSCROLLWIDTHTRACKING):
            value = bool(int(args[0])) if args else False
            self._scroll_width_tracking = value
            return 1 if value else 0
        if msg == int(self.SCI_GETSCROLLWIDTHTRACKING):
            return 1 if self._scroll_width_tracking else 0
        if msg == int(self.SCI_SETXCARETPOLICY):
            policy = int(args[0]) if len(args) >= 1 else 0
            slop = int(args[1]) if len(args) >= 2 else 0
            self._x_caret_policy = (policy, slop)
            return int(policy)
        if msg == int(self.SCI_GETXCARETPOLICY):
            return int(self._x_caret_policy[0])
        if msg == int(self.SCI_SETYCARETPOLICY):
            policy = int(args[0]) if len(args) >= 1 else 0
            slop = int(args[1]) if len(args) >= 2 else 0
            self._y_caret_policy = (policy, slop)
            return int(policy)
        if msg == int(self.SCI_GETYCARETPOLICY):
            return int(self._y_caret_policy[0])
        if msg == int(self.SCI_SETVISIBLEPOLICY):
            policy = int(args[0]) if len(args) >= 1 else 0
            slop = int(args[1]) if len(args) >= 2 else 0
            self._visible_policy = (policy, slop)
            return int(policy)
        if msg == int(self.SCI_GETVISIBLEPOLICY):
            return int(self._visible_policy[0])
        if msg == int(self.SCI_SETCARETPERIOD):
            period = max(0, int(args[0])) if args else 0
            self._caret_period_ms = period
            return int(period)
        if msg == int(self.SCI_GETCARETPERIOD):
            return int(self._caret_period_ms)
        if msg == int(self.SCI_SETMOUSEDWELLTIME):
            dwell = int(args[0]) if args else 0
            self._mouse_dwell_time_ms = dwell
            return int(dwell)
        if msg == int(self.SCI_GETMOUSEDWELLTIME):
            return int(self._mouse_dwell_time_ms)
        if msg == int(self.SCI_SETZOOM):
            self._zoom = int(args[0]) if args else 0
            return int(self._zoom)
        if msg == int(self.SCI_GETZOOM):
            return int(self._zoom)
        if msg == int(self.SCI_SETEDGEMODE):
            self._edge_mode = int(args[0]) if args else 0
            return int(self._edge_mode)
        if msg == int(self.SCI_GETEDGEMODE):
            return int(self._edge_mode)
        if msg == int(self.SCI_SETEDGECOLUMN):
            self._edge_column = max(0, int(args[0]) if args else 0)
            return int(self._edge_column)
        if msg == int(self.SCI_GETEDGECOLUMN):
            return int(self._edge_column)
        if msg == int(self.SCI_SETEDGECOLOUR):
            value = int(args[0]) if args else 0
            self._edge_colour = self._qcolor_from_scintilla_rgb(value)
            return int(value)
        if msg == int(self.SCI_GETEDGECOLOUR):
            c = self._edge_colour
            return int(c.red()) | (int(c.green()) << 8) | (int(c.blue()) << 16)
        if msg == int(self.SCI_SETPRINTWRAPMODE):
            self._print_wrap_mode = int(args[0]) if args else 0
            return int(self._print_wrap_mode)
        if msg == int(self.SCI_GETPRINTWRAPMODE):
            return int(self._print_wrap_mode)
        if msg == int(self.SCI_SETEXTRAASCENT):
            self._extra_ascent = max(0, int(args[0]) if args else 0)
            return int(self._extra_ascent)
        if msg == int(self.SCI_GETEXTRAASCENT):
            return int(self._extra_ascent)
        if msg == int(self.SCI_SETEXTRADESCENT):
            self._extra_descent = max(0, int(args[0]) if args else 0)
            return int(self._extra_descent)
        if msg == int(self.SCI_GETEXTRADESCENT):
            return int(self._extra_descent)
        if msg == int(self.SCI_SETCARETSTICKY):
            self._caret_sticky = max(0, int(args[0]) if args else 0)
            return int(self._caret_sticky)
        if msg == int(self.SCI_GETCARETSTICKY):
            return int(self._caret_sticky)
        if msg == int(self.SCI_SETPASTECONVERTENDINGS):
            self._paste_convert_endings = bool(int(args[0])) if args else False
            return 1 if self._paste_convert_endings else 0
        if msg == int(self.SCI_GETPASTECONVERTENDINGS):
            return 1 if self._paste_convert_endings else 0
        if msg == int(self.SCI_SETVIRTUALSPACEOPTIONS):
            self._virtual_space_options = int(args[0]) if args else 0
            return int(self._virtual_space_options)
        if msg == int(self.SCI_GETVIRTUALSPACEOPTIONS):
            return int(self._virtual_space_options)
        if msg == int(self.SCI_SETSTATUS):
            self._status = int(args[0]) if args else 0
            return int(self._status)
        if msg == int(self.SCI_GETSTATUS):
            return int(self._status)
        if msg == int(self.SCI_SETMODEVENTMASK):
            self._mod_event_mask = int(args[0]) if args else 0
            return int(self._mod_event_mask)
        if msg == int(self.SCI_GETMODEVENTMASK):
            return int(self._mod_event_mask)
        if msg == int(self.SCI_SETBUFFEREDDRAW):
            self._buffered_draw = bool(int(args[0])) if args else False
            return 1 if self._buffered_draw else 0
        if msg == int(self.SCI_GETBUFFEREDDRAW):
            return 1 if self._buffered_draw else 0
        if msg == int(self.SCI_SETTWOPHASEDRAW):
            self._two_phase_draw = max(0, int(args[0]) if args else 0)
            return int(self._two_phase_draw)
        if msg == int(self.SCI_GETTWOPHASEDRAW):
            return int(self._two_phase_draw)
        if msg == int(self.SCI_SETLAYOUTCACHE):
            self._layout_cache = max(0, int(args[0]) if args else 0)
            return int(self._layout_cache)
        if msg == int(self.SCI_GETLAYOUTCACHE):
            return int(self._layout_cache)
        extra_state_result = handle_extra_state_command(self, msg, args)
        if extra_state_result is not None:
            return int(extra_state_result)
        if msg == int(self.SCI_SETCARETFORE):
            value = int(args[0]) if args else 0
            self._caret_fore_colour = self._qcolor_from_scintilla_rgb(value)
            return int(value)
        if msg == int(self.SCI_GETCARETFORE):
            c = self._caret_fore_colour
            return int(c.red()) | (int(c.green()) << 8) | (int(c.blue()) << 16)
        if msg == int(self.SCI_SETCARETSTYLE):
            self._caret_style = max(0, int(args[0]) if args else 0)
            return int(self._caret_style)
        if msg == int(self.SCI_GETCARETSTYLE):
            return int(self._caret_style)
        if msg == int(self.SCI_SETADDITIONALCARETFORE):
            value = int(args[0]) if args else 0
            self._additional_caret_fore = self._qcolor_from_scintilla_rgb(value)
            return int(value)
        if msg == int(self.SCI_GETADDITIONALCARETFORE):
            c = self._additional_caret_fore
            return int(c.red()) | (int(c.green()) << 8) | (int(c.blue()) << 16)
        if msg == int(self.SCI_SETADDITIONALSELFORE):
            value = int(args[0]) if args else 0
            self._additional_sel_fore = self._qcolor_from_scintilla_rgb(value)
            return int(value)
        if msg == int(self.SCI_GETADDITIONALSELFORE):
            c = self._additional_sel_fore
            return int(c.red()) | (int(c.green()) << 8) | (int(c.blue()) << 16)
        if msg == int(self.SCI_SETADDITIONALSELBACK):
            value = int(args[0]) if args else 0
            self._additional_sel_back = self._qcolor_from_scintilla_rgb(value)
            return int(value)
        if msg == int(self.SCI_GETADDITIONALSELBACK):
            c = self._additional_sel_back
            return int(c.red()) | (int(c.green()) << 8) | (int(c.blue()) << 16)
        if msg == int(self.SCI_SETADDITIONALCARETSBLINK):
            self._additional_carets_blink = bool(int(args[0])) if args else False
            return 1 if self._additional_carets_blink else 0
        if msg == int(self.SCI_GETADDITIONALCARETSBLINK):
            return 1 if self._additional_carets_blink else 0
        if msg == int(self.SCI_SETADDITIONALCARETSVISIBLE):
            self._additional_carets_visible = bool(int(args[0])) if args else False
            return 1 if self._additional_carets_visible else 0
        if msg == int(self.SCI_GETADDITIONALCARETSVISIBLE):
            return 1 if self._additional_carets_visible else 0
        if msg == int(self.SCI_SETHOTSPOTACTIVEBACK):
            value = int(args[0]) if args else 0
            self._hotspot_active_back = self._qcolor_from_scintilla_rgb(value)
            return int(value)
        if msg == int(self.SCI_GETHOTSPOTACTIVEBACK):
            c = self._hotspot_active_back
            return int(c.red()) | (int(c.green()) << 8) | (int(c.blue()) << 16)
        if msg == int(self.SCI_GETHOTSPOTACTIVEUNDERLINE):
            return 1 if self._hotspot_underline else 0
        if msg == int(self.SCI_SETHOTSPOTSINGLELINE):
            self._hotspot_single_line = bool(int(args[0])) if args else False
            return 1 if self._hotspot_single_line else 0
        if msg == int(self.SCI_GETHOTSPOTSINGLELINE):
            return 1 if self._hotspot_single_line else 0
        if msg == int(self.SCI_SETEOLMODE):
            self._eol_mode = max(0, min(2, int(args[0]) if args else 0))
            return int(self._eol_mode)
        if msg == int(self.SCI_GETEOLMODE):
            return int(self._eol_mode)
        if msg == int(self.SCI_GETFIRSTVISIBLELINE):
            return int(self._virtual_first_visible_line)
        if msg == int(self.SCI_LINESONSCREEN):
            lh = max(1, self.fontMetrics().height())
            return max(1, int(self.viewport().height() // lh))
        if msg == int(self.SCI_BRACEMATCH):
            pos = max(0, int(args[0]) if args else 0)
            text = self.toPlainText()
            pair = self._find_brace_pair_at(text, pos)
            if pair is None:
                return -1
            a, b = int(pair[0]), int(pair[1])
            if a == pos:
                return b
            if b == pos:
                return a
            return -1
        if msg == int(self.SCI_GETBRACEHIGHLIGHT):
            idx = int(args[0]) if args else 0
            pair = self._brace_match_pair
            if pair is None:
                return -1
            a, b = int(pair[0]), int(pair[1])
            if a >= 0 and b >= 0:
                return a if idx == 0 else b
            return -1
        if msg == int(self.SCI_GETBRACEBADLIGHT):
            pair = self._brace_match_pair
            if pair is None:
                return -1
            a, b = int(pair[0]), int(pair[1])
            if a == b and a >= 0:
                return a
            return -1
        if msg == int(self.SCI_WORDSTARTPOSITION):
            pos = max(0, min(int(args[0]) if args else 0, len(self.toPlainText())))
            only_word = bool(int(args[1])) if len(args) >= 2 else True
            return int(self._word_start_position(pos, only_word_chars=only_word))
        if msg == int(self.SCI_WORDENDPOSITION):
            pos = max(0, min(int(args[0]) if args else 0, len(self.toPlainText())))
            only_word = bool(int(args[1])) if len(args) >= 2 else True
            return int(self._word_end_position(pos, only_word_chars=only_word))
        if msg == int(self.SCI_GETCARETLINEVISIBLE):
            return 1 if self._caret_line_visible else 0
        if msg == int(self.SCI_GETCARETLINEBACK):
            c = self._caret_line_color
            return int(c.red()) | (int(c.green()) << 8) | (int(c.blue()) << 16)
        if msg == int(self.SCI_GETCURRENTPOS):
            return int(self.textCursor().position())
        if msg == int(self.SCI_GETLENGTH):
            return int(len(self.toPlainText()))
        if msg == int(self.SCI_SETTARGETSTART):
            text_len = len(self.toPlainText())
            self._target_start = max(0, min(int(args[0]) if args else 0, text_len))
            return int(self._target_start)
        if msg == int(self.SCI_SETTARGETEND):
            text_len = len(self.toPlainText())
            self._target_end = max(0, min(int(args[0]) if args else 0, text_len))
            return int(self._target_end)
        if msg == int(self.SCI_GETTARGETSTART):
            return int(self._target_start)
        if msg == int(self.SCI_GETTARGETEND):
            return int(self._target_end)
        if msg == int(self.SCI_GETTARGETTEXT):
            text = self.toPlainText()
            lo = max(0, min(int(self._target_start), int(self._target_end), len(text)))
            hi = max(0, min(max(int(self._target_start), int(self._target_end)), len(text)))
            seg = text[lo:hi]
            if len(args) >= 1:
                self._write_scintilla_text_target(args[0], seg)
            return len(seg)
        if msg == int(self.SCI_SETSEARCHFLAGS):
            self._search_flags = int(args[0]) if args else 0
            return int(self._search_flags)
        if msg == int(self.SCI_GETSEARCHFLAGS):
            return int(self._search_flags)
        if msg == int(self.SCI_GETSELECTIONMODE):
            return int(self.SC_SEL_RECTANGLE if self._column_mode else self.SC_SEL_STREAM)
        if msg == int(self.SCI_GETMULTIPLESELECTION):
            return 1 if self._multiple_selection_enabled else 0
        if msg == int(self.SCI_GETADDITIONALSELECTIONTYPING):
            return 1 if self._additional_selection_typing else 0
        if msg == int(self.SCI_SETSTYLEBITS):
            if args:
                self._style_bits = max(1, min(8, int(args[0])))
            return int(self._style_bits)
        if msg == int(self.SCI_GETSTYLEBITS):
            return int(self._style_bits)
        if msg == int(self.SCI_GETTEXT):
            text = self.toPlainText()
            if len(args) >= 2:
                max_len = max(0, int(args[0]))
                clipped = text[: max(0, max_len - 1)] if max_len else ""
                self._write_scintilla_text_target(args[1], clipped, max_len=max_len)
                return len(clipped)
            return len(text)
        if msg == int(self.SCI_GETANCHOR):
            c = self.textCursor()
            return int(c.anchor())
        if msg == int(self.SCI_SETSAVEPOINT):
            self.document().setModified(False)
            return 1
        movement_edit_result = handle_movement_edit_command(self, msg, args)
        if movement_edit_result is not None:
            return int(movement_edit_result)
        if msg == int(self.SCI_CANCEL):
            c = self.textCursor()
            if c.hasSelection():
                c.setPosition(c.position())
                self.setTextCursor(c)
            return 1
        selection_undo_result = handle_selection_undo_command(self, msg, args)
        if selection_undo_result is not None:
            return int(selection_undo_result)
        if msg == int(self.SCI_INSERTTEXT):
            if len(args) < 3:
                return 0
            if self.isReadOnly():
                return 0
            pos = max(0, min(int(args[0]), len(self.toPlainText())))
            text = self._read_scintilla_text_arg(args[2], int(args[1]))
            c = self.textCursor()
            c.setPosition(pos)
            c.insertText(text)
            self.setTextCursor(c)
            return len(text)
        if msg == int(self.SCI_DELETERANGE):
            if len(args) < 2:
                return 0
            if self.isReadOnly():
                return 0
            pos = max(0, min(int(args[0]), len(self.toPlainText())))
            length = max(0, int(args[1]))
            end = max(pos, min(pos + length, len(self.toPlainText())))
            if end <= pos:
                return 0
            c = self.textCursor()
            c.setPosition(pos)
            c.setPosition(end, QTextCursor.KeepAnchor)
            c.removeSelectedText()
            self.setTextCursor(c)
            return end - pos
        if msg == int(self.SCI_REPLACESEL):
            if len(args) < 2:
                return 0
            if self.isReadOnly():
                return 0
            replacement = self._read_scintilla_text_arg(args[1], int(args[0]))
            c = self.textCursor()
            c.insertText(replacement)
            self.setTextCursor(c)
            return len(replacement)
        if msg == int(self.SCI_APPENDTEXT):
            if len(args) < 2:
                return 0
            if self.isReadOnly():
                return 0
            append_text = self._read_scintilla_text_arg(args[1], int(args[0]))
            c = self.textCursor()
            c.movePosition(QTextCursor.End)
            c.insertText(append_text)
            self.setTextCursor(c)
            return len(append_text)
        if msg == int(self.SCI_GETSELECTIONSTART):
            c = self.textCursor()
            return int(min(c.selectionStart(), c.selectionEnd()))
        if msg == int(self.SCI_GETSELECTIONEND):
            c = self.textCursor()
            return int(max(c.selectionStart(), c.selectionEnd()))
        if msg == int(self.SCI_GETSELECTIONS):
            if self._multiple_selection_enabled and self._additional_carets:
                return int(len(self._additional_carets) + 1)
            return 1
        if msg == int(self.SCI_GETMAINSELECTION):
            return int(self._coerce_main_selection_index(self._main_selection_index))
        if msg == int(self.SCI_SETMAINSELECTION):
            if not args:
                return int(self._coerce_main_selection_index(self._main_selection_index))
            idx = self._coerce_main_selection_index(int(args[0]))
            self._main_selection_index = idx
            return int(idx)
        if msg == int(self.SCI_ROTATESELECTION):
            self._rotate_main_selection()
            return int(self._main_selection_index)
        if msg == int(self.SCI_SWAPMAINANCHORCARET):
            self._swap_main_anchor_caret()
            return 1
        if msg == int(self.SCI_GETMAINSELSTART):
            start, _end = self._selection_n_range(self._coerce_main_selection_index(self._main_selection_index))
            return int(start)
        if msg == int(self.SCI_GETMAINSELEND):
            _start, end = self._selection_n_range(self._coerce_main_selection_index(self._main_selection_index))
            return int(end)
        if msg == int(self.SCI_GETSELECTIONNSTART):
            idx = int(args[0]) if args else 0
            start, _end = self._selection_n_range(idx)
            return int(start)
        if msg == int(self.SCI_GETSELECTIONNEND):
            idx = int(args[0]) if args else 0
            _start, end = self._selection_n_range(idx)
            return int(end)
        if msg == int(self.SCI_SETSELECTIONNSTART):
            if len(args) < 2:
                return 0
            self._set_selection_n_boundary(int(args[0]), int(args[1]), is_start=True)
            return 1
        if msg == int(self.SCI_SETSELECTIONNEND):
            if len(args) < 2:
                return 0
            self._set_selection_n_boundary(int(args[0]), int(args[1]), is_start=False)
            return 1
        if msg == int(self.SCI_ADDSELECTION):
            if len(args) < 2:
                return 0
            caret = max(0, min(int(args[0]), len(self.toPlainText())))
            anchor = max(0, min(int(args[1]), len(self.toPlainText())))
            self._add_selection(caret=caret, anchor=anchor)
            return 1
        if msg == int(self.SCI_DROPSELECTIONN):
            if not args:
                return 0
            self._drop_selection_n(int(args[0]))
            return 1
        if msg == int(self.SCI_CLEARSELECTIONS):
            self._clear_additional_selections()
            return 1
        if msg == int(self.SCI_GETTEXTRANGE):
            if len(args) < 2:
                return 0
            lo = max(0, min(int(args[0]), int(args[1])))
            hi = max(0, max(int(args[0]), int(args[1])))
            text = self.toPlainText()
            seg = text[lo:hi]
            if len(args) >= 3:
                self._write_scintilla_text_target(args[2], seg)
            return len(seg)
        if msg == int(self.SCI_TARGETFROMSELECTION):
            c = self.textCursor()
            self._target_start = int(min(c.selectionStart(), c.selectionEnd()))
            self._target_end = int(max(c.selectionStart(), c.selectionEnd()))
            return int(self._target_end - self._target_start)
        if msg == int(self.SCI_TARGETWHOLEDOCUMENT):
            self._target_start = 0
            self._target_end = int(len(self.toPlainText()))
            return int(self._target_end)
        if msg == int(self.SCI_SEARCHINTARGET):
            if len(args) < 2:
                return -1
            needle = self._read_scintilla_text_arg(args[1], int(args[0]))
            if not needle:
                return -1
            text = self.toPlainText()
            start = max(0, min(int(self._target_start), len(text)))
            end = max(0, min(int(self._target_end), len(text)))
            reverse = start > end
            lo = min(start, end)
            hi = max(start, end)
            self._last_regex_match = None
            idx = self._search_in_target(text, needle, lo, hi, reverse=reverse)
            if idx < 0:
                return -1
            match_len = len(needle)
            if self._last_regex_match is not None:
                match_len = max(0, int(self._last_regex_match.end() - self._last_regex_match.start()))
            self._target_start = int(idx)
            self._target_end = int(idx + match_len)
            return int(idx)
        if msg == int(self.SCI_REPLACETARGET):
            if len(args) < 2:
                return 0
            text = self.toPlainText()
            lo = max(0, min(int(self._target_start), int(self._target_end), len(text)))
            hi = max(0, min(max(int(self._target_start), int(self._target_end)), len(text)))
            replacement = self._read_scintilla_text_arg(args[1], int(args[0]))
            return self._replace_target_span(lo, hi, replacement)
        if msg == int(self.SCI_REPLACETARGETRE):
            if len(args) < 2:
                return 0
            text = self.toPlainText()
            lo = max(0, min(int(self._target_start), int(self._target_end), len(text)))
            hi = max(0, min(max(int(self._target_start), int(self._target_end)), len(text)))
            replacement_raw = self._read_scintilla_text_arg(args[1], int(args[0]))
            if self._last_regex_match is not None:
                try:
                    replacement = self._last_regex_match.expand(replacement_raw)
                except Exception:
                    replacement = replacement_raw
            else:
                replacement = replacement_raw
            return self._replace_target_span(lo, hi, replacement)
        if msg == int(self.SCI_REPLACETARGETMINIMAL):
            if len(args) < 2:
                return 0
            text = self.toPlainText()
            lo = max(0, min(int(self._target_start), int(self._target_end), len(text)))
            hi = max(0, min(max(int(self._target_start), int(self._target_end)), len(text)))
            replacement = self._read_scintilla_text_arg(args[1], int(args[0]))
            original = text[lo:hi]
            prefix = 0
            max_prefix = min(len(original), len(replacement))
            while prefix < max_prefix and original[prefix] == replacement[prefix]:
                prefix += 1
            suffix = 0
            max_suffix = min(len(original) - prefix, len(replacement) - prefix)
            while suffix < max_suffix and original[len(original) - 1 - suffix] == replacement[len(replacement) - 1 - suffix]:
                suffix += 1
            new_lo = lo + prefix
            new_hi = hi - suffix
            new_text = replacement[prefix : len(replacement) - suffix if suffix > 0 else len(replacement)]
            return self._replace_target_span(new_lo, new_hi, new_text)
        if msg == int(self.SCI_LINEFROMPOSITION):
            pos = max(0, min(int(args[0]) if args else 0, len(self.toPlainText())))
            block = self.document().findBlock(pos)
            return int(block.blockNumber()) if block.isValid() else 0
        if msg == int(self.SCI_GETLINEVISIBLE):
            line = max(0, int(args[0]) if args else 0)
            block = self.document().findBlockByNumber(line)
            if not block.isValid():
                return 0
            return 1 if block.isVisible() else 0
        if msg == int(self.SCI_GETFOLDLEVEL):
            line = max(0, int(args[0]) if args else 0)
            region = self._fold_regions.get(line)
            if region is not None:
                return int(region.level) & int(self.SC_FOLDLEVELNUMBERMASK)
            block = self.document().findBlockByNumber(line)
            if not block.isValid():
                return 0
            return int(self._indent_of_line(block.text())) & int(self.SC_FOLDLEVELNUMBERMASK)
        if msg == int(self.SCI_GETFOLDPARENT):
            line = max(0, int(args[0]) if args else 0)
            self._rebuild_fold_regions()
            return int(self._fold_parent_for_line(line))
        if msg == int(self.SCI_GETLASTCHILD):
            line = max(0, int(args[0]) if args else 0)
            level = int(args[1]) if len(args) >= 2 else -1
            self._rebuild_fold_regions()
            return int(self._fold_last_child_for_line(line, level))
        if msg == int(self.SCI_HIDELINES) and len(args) >= 2:
            return 1 if self.hide_lines(int(args[0]), int(args[1])) else 0
        if msg == int(self.SCI_SHOWLINES) and len(args) >= 2:
            return 1 if self.show_lines(int(args[0]), int(args[1])) else 0
        return 0

    @staticmethod
    def _write_scintilla_text_target(target, text: str, *, max_len: int | None = None) -> None:
        payload = str(text)
        if isinstance(target, dict):
            target["text"] = payload
            return
        if isinstance(target, list):
            target.clear()
            target.append(payload)
            return
        if isinstance(target, bytearray):
            encoded = payload.encode("utf-8")
            if max_len is not None and max_len > 0:
                encoded = encoded[: max(0, max_len - 1)]
                write_len = min(len(target), len(encoded))
                if write_len > 0:
                    target[:write_len] = encoded[:write_len]
                if write_len < len(target):
                    target[write_len] = 0
                return
            write_len = min(len(target), len(encoded))
            if write_len > 0:
                target[:write_len] = encoded[:write_len]
            return

    @staticmethod
    def _read_scintilla_text_arg(source, max_len: int | None = None) -> str:
        if isinstance(source, dict):
            value = source.get("text", "")
            text = str(value)
        elif isinstance(source, list):
            text = str(source[0]) if source else ""
        elif isinstance(source, (bytes, bytearray)):
            raw = bytes(source)
            zero = raw.find(b"\x00")
            if zero >= 0:
                raw = raw[:zero]
            text = raw.decode("utf-8", errors="ignore")
        else:
            text = str(source or "")
        if max_len is None:
            return text
        limit = int(max_len)
        if limit < 0:
            return text
        return text[:limit]

    def _search_in_target(self, text: str, needle: str, lo: int, hi: int, *, reverse: bool = False) -> int:
        match_case = bool(int(self._search_flags) & int(self.SCFIND_MATCHCASE))
        whole_word = bool(int(self._search_flags) & int(self.SCFIND_WHOLEWORD))
        word_start = bool(int(self._search_flags) & int(self.SCFIND_WORDSTART))
        regex_mode = bool(int(self._search_flags) & int(self.SCFIND_REGEXP))
        if regex_mode:
            return self._regex_search_in_target(
                text,
                needle,
                lo,
                hi,
                reverse=reverse,
                whole_word=whole_word,
                word_start=word_start,
                match_case=match_case,
            )
        hay = text if match_case else text.lower()
        ndl = needle if match_case else needle.lower()
        if not ndl:
            return -1
        start = max(0, min(int(lo), len(hay)))
        end = max(start, min(int(hi), len(hay)))
        if reverse:
            idx = hay.rfind(ndl, start, end)
            while idx >= 0:
                if self._matches_word_constraints(text, idx, idx + len(needle), whole_word=whole_word, word_start=word_start):
                    return int(idx)
                idx = hay.rfind(ndl, start, idx)
            return -1
        idx = hay.find(ndl, start, end)
        while idx >= 0:
            if self._matches_word_constraints(text, idx, idx + len(needle), whole_word=whole_word, word_start=word_start):
                return int(idx)
            idx = hay.find(ndl, idx + 1, end)
        return -1

    def _regex_search_in_target(
        self,
        text: str,
        pattern: str,
        lo: int,
        hi: int,
        *,
        reverse: bool,
        whole_word: bool,
        word_start: bool,
        match_case: bool,
    ) -> int:
        flags = 0 if match_case else re.IGNORECASE
        try:
            regex = re.compile(pattern, flags)
        except re.error:
            return -1
        matches = []
        for m in regex.finditer(text, lo, hi):
            s = int(m.start())
            e = int(m.end())
            if e <= s:
                continue
            if not self._matches_word_constraints(text, s, e, whole_word=whole_word, word_start=word_start):
                continue
            matches.append(m)
        if not matches:
            return -1
        match = matches[-1] if reverse else matches[0]
        self._last_regex_match = match
        return int(match.start())

    @staticmethod
    def _is_word_char(ch: str) -> bool:
        return ch.isalnum() or ch == "_"

    def _is_whole_word_match(self, text: str, start: int, end: int) -> bool:
        left_ok = start <= 0 or not self._is_word_char(text[start - 1])
        right_ok = end >= len(text) or not self._is_word_char(text[end])
        return bool(left_ok and right_ok)

    def _is_word_start_match(self, text: str, start: int) -> bool:
        return bool(start <= 0 or not self._is_word_char(text[start - 1]))

    def _matches_word_constraints(self, text: str, start: int, end: int, *, whole_word: bool, word_start: bool) -> bool:
        if whole_word:
            return self._is_whole_word_match(text, start, end)
        if word_start:
            return self._is_word_start_match(text, start)
        return True

    def _replace_target_span(self, lo: int, hi: int, replacement: str) -> int:
        cursor = self.textCursor()
        cursor.setPosition(max(0, int(lo)))
        cursor.setPosition(max(0, int(hi)), QTextCursor.KeepAnchor)
        cursor.insertText(str(replacement))
        self.setTextCursor(cursor)
        self._target_start = int(lo)
        self._target_end = int(lo + len(str(replacement)))
        return len(str(replacement))

    def _page_move(self, *, up: bool, extend: bool) -> int:
        steps = max(1, int(self.SendScintilla(self.SCI_LINESONSCREEN)) - 1)
        c = self.textCursor()
        op = QTextCursor.Up if up else QTextCursor.Down
        mode = QTextCursor.KeepAnchor if extend else QTextCursor.MoveAnchor
        for _ in range(steps):
            c.movePosition(op, mode)
        self.setTextCursor(c)
        return int(c.position())

    def _word_start_position(self, pos: int, *, only_word_chars: bool) -> int:
        text = self.toPlainText()
        p = max(0, min(int(pos), len(text)))
        if p <= 0:
            return 0
        while p > 0:
            ch = text[p - 1]
            if only_word_chars:
                if not self._is_word_char(ch):
                    break
            else:
                if ch.isspace():
                    break
            p -= 1
        return int(p)

    def _word_end_position(self, pos: int, *, only_word_chars: bool) -> int:
        text = self.toPlainText()
        p = max(0, min(int(pos), len(text)))
        n = len(text)
        while p < n:
            ch = text[p]
            if only_word_chars:
                if not self._is_word_char(ch):
                    break
            else:
                if ch.isspace():
                    break
            p += 1
        return int(p)

    def _selection_n_range(self, idx: int) -> tuple[int, int]:
        index = max(0, int(idx))
        c = self.textCursor()
        main = (int(min(c.selectionStart(), c.selectionEnd())), int(max(c.selectionStart(), c.selectionEnd())))
        if index == 0:
            return main
        if not self._multiple_selection_enabled:
            return main
        extra_i = index - 1
        if 0 <= extra_i < len(self._additional_carets):
            p = int(self._additional_carets[extra_i])
            return p, p
        return main

    def _coerce_main_selection_index(self, idx: int) -> int:
        total = 1
        if self._multiple_selection_enabled and self._additional_carets:
            total = len(self._additional_carets) + 1
        return max(0, min(int(idx), max(0, total - 1)))

    def _rotate_main_selection(self) -> None:
        total = 1
        if self._multiple_selection_enabled and self._additional_carets:
            total = len(self._additional_carets) + 1
        if total <= 1:
            self._main_selection_index = 0
            return
        self._main_selection_index = (int(self._main_selection_index) + 1) % int(total)

    def _swap_main_anchor_caret(self) -> None:
        main_idx = self._coerce_main_selection_index(self._main_selection_index)
        if main_idx != 0:
            return
        c = self.textCursor()
        pos = int(c.position())
        anc = int(c.anchor())
        if pos == anc:
            return
        c.setPosition(pos)
        c.setPosition(anc, QTextCursor.KeepAnchor)
        self.setTextCursor(c)

    def _set_selection_n_boundary(self, idx: int, pos: int, *, is_start: bool) -> None:
        index = max(0, int(idx))
        p = max(0, min(int(pos), len(self.toPlainText())))
        if index == 0:
            c = self.textCursor()
            other = c.selectionEnd() if is_start else c.selectionStart()
            c.setPosition(p)
            c.setPosition(max(0, min(int(other), len(self.toPlainText()))), QTextCursor.KeepAnchor)
            self.setTextCursor(c)
            return
        if not self._multiple_selection_enabled:
            return
        extra_i = index - 1
        if extra_i < 0:
            return
        while len(self._additional_carets) <= extra_i:
            self._additional_carets.append(int(self.textCursor().position()))
        self._additional_carets[extra_i] = p
        self.viewport().update()

    def _add_selection(self, *, caret: int, anchor: int) -> None:
        # Compat model stores additional selections as carets; selection ranges are not fully tracked yet.
        self._multiple_selection_enabled = True
        cp = int(caret)
        if cp not in self._additional_carets and cp != int(self.textCursor().position()):
            self._additional_carets.append(cp)
        self.viewport().update()

    def _drop_selection_n(self, idx: int) -> None:
        index = int(idx)
        if index <= 0:
            return
        if not self._multiple_selection_enabled:
            return
        extra_i = index - 1
        if 0 <= extra_i < len(self._additional_carets):
            del self._additional_carets[extra_i]
        self._main_selection_index = self._coerce_main_selection_index(self._main_selection_index)
        self.viewport().update()

    def _clear_additional_selections(self) -> None:
        self._additional_carets = []
        self._multiple_selection_enabled = False
        self._additional_selection_typing = False
        self._main_selection_index = 0
        self.viewport().update()

    def _style_at_pos(self, pos: int) -> int:
        p = max(0, int(pos))
        for lo, hi, style_id in reversed([*self._lexer_ranges, *self._style_ranges]):
            if int(lo) <= p < int(hi):
                return int(style_id)
        return 0

    def _marker_mask_for_line(self, line: int) -> int:
        ln = max(0, int(line))
        mask = 0
        for marker_id, lines in self._markers.items():
            try:
                bit = int(marker_id)
            except Exception:
                continue
            if bit < 0 or bit > 30:
                continue
            if ln in lines:
                mask |= (1 << bit)
        return int(mask)

    def _marker_line_matches_mask(self, line: int, mask: int) -> bool:
        line_mask = self._marker_mask_for_line(line)
        if int(mask) < 0:
            return line_mask != 0
        return (line_mask & int(mask)) != 0

    def _marker_next_line(self, line: int, mask: int) -> int:
        max_line = max(0, self.blockCount() - 1)
        for ln in range(max(0, int(line)), max_line + 1):
            if self._marker_line_matches_mask(ln, int(mask)):
                return int(ln)
        return -1

    def _marker_previous_line(self, line: int, mask: int) -> int:
        max_line = max(0, self.blockCount() - 1)
        start = min(max_line, max(0, int(line)))
        for ln in range(start, -1, -1):
            if self._marker_line_matches_mask(ln, int(mask)):
                return int(ln)
        return -1

    def _fold_parent_for_line(self, line: int) -> int:
        best_parent = -1
        best_span = None
        for header, region in self._fold_regions.items():
            if int(region.start) < int(line) <= int(region.end):
                span = int(region.end) - int(region.start)
                if best_span is None or span < best_span or (span == best_span and int(region.start) > best_parent):
                    best_span = span
                    best_parent = int(header)
        return int(best_parent)

    def _fold_last_child_for_line(self, line: int, level: int) -> int:
        region = self._fold_regions.get(int(line))
        if region is None:
            return int(line)
        return int(region.end)

    def margin_width(self) -> int:
        return sum(width for _idx, _kind, _x, width in self._margin_segments()) + self._margin_left_padding + self._margin_right_padding

    def _margin_segments(self) -> list[tuple[int, str, int, int]]:
        digits = max(2, len(str(self.blockCount())))
        dynamic_number_width = 8 + self.fontMetrics().horizontalAdvance("9" * digits)
        x = self._margin_left_padding
        segments: list[tuple[int, str, int, int]] = []
        for idx in (0, 1, 2):
            raw = int(self._margin_widths.get(idx, 0))
            width = dynamic_number_width if raw < 0 else max(0, raw)
            if width <= 0:
                continue
            margin_type = int(self._margin_types.get(idx, self.SC_MARGIN_SYMBOL))
            kind = "symbol"
            if idx == 0:
                kind = "fold"
            elif margin_type == self.SC_MARGIN_NUMBER:
                kind = "number"
            elif margin_type in {self.SC_MARGIN_TEXT, self.SC_MARGIN_RTEXT}:
                kind = "text"
            segments.append((idx, kind, x, width))
            x += width
        return segments

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        width = self.margin_width()
        self._margin.setGeometry(QRect(cr.left(), cr.top(), width, cr.height()))

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        self._paint_multi_ranges()
        self._paint_annotations()
        self._paint_symbol_overlays()
        self._paint_brace_match()
        if not self._additional_carets:
            return
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing, False)
        color = self.palette().color(self.palette().Text)
        color.setAlpha(210)
        painter.setPen(color)
        for pos in self._additional_carets:
            cursor = QTextCursor(self.document())
            cursor.setPosition(max(0, min(pos, len(self.toPlainText()))))
            rect = self.cursorRect(cursor)
            if not rect.isValid():
                continue
            painter.drawLine(rect.left(), rect.top(), rect.left(), rect.bottom())
        painter.end()

    def _paint_annotations(self) -> None:
        if not self._annotations:
            return
        painter = QPainter(self.viewport())
        color = QColor("#6f7684")
        painter.setPen(color)
        block = self.firstVisibleBlock()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        while block.isValid() and top <= self.viewport().height():
            if block.isVisible() and bottom >= 0:
                line = block.blockNumber()
                note = self._annotations.get(line, "")
                if note:
                    x = int(self.contentOffset().x() + 4)
                    y = int(top + self.fontMetrics().height() - 2)
                    painter.drawText(x, y, note)
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
        painter.end()

    def _paint_brace_match(self) -> None:
        pair = self._brace_match_pair
        if pair is None:
            return
        painter = QPainter(self.viewport())
        color = QColor("#5da9ff")
        color.setAlpha(150)
        painter.setPen(color)
        for pos in pair:
            if pos < 0:
                continue
            cursor = QTextCursor(self.document())
            cursor.setPosition(max(0, min(pos, len(self.toPlainText()))))
            rect = self.cursorRect(cursor)
            if rect.isValid():
                painter.drawRect(rect.adjusted(0, 0, max(1, self.fontMetrics().horizontalAdvance(" ")), 0))
        painter.end()

    def _paint_multi_ranges(self) -> None:
        ranges = [(s, e) for s, e in self._multi_ranges if e > s]
        if not ranges:
            return
        painter = QPainter(self.viewport())
        color = self.palette().color(self.palette().Highlight)
        color.setAlpha(90)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        for start, end in ranges:
            c1 = QTextCursor(self.document())
            c2 = QTextCursor(self.document())
            c1.setPosition(max(0, min(start, len(self.toPlainText()))))
            c2.setPosition(max(0, min(end, len(self.toPlainText()))))
            r1 = self.cursorRect(c1)
            r2 = self.cursorRect(c2)
            if not r1.isValid() or not r2.isValid():
                continue
            x1 = min(r1.left(), r2.left())
            x2 = max(r1.left(), r2.left())
            if x1 == x2:
                x2 = x1 + max(2, self.fontMetrics().horizontalAdvance(" "))
            rect = QRect(x1, r1.top(), x2 - x1, r1.height())
            painter.drawRect(rect)
        painter.end()

    def _paint_symbol_overlays(self) -> None:
        if not (
            self._view_whitespace
            or self._view_eol
            or self._view_control_chars
            or self._show_indent_guides
            or self._show_wrap_symbol
        ):
            return
        painter = QPainter(self.viewport())
        overlay = QColor("#8d939f")
        overlay.setAlpha(120)
        painter.setPen(overlay)
        block = self.firstVisibleBlock()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        char_w = max(1, self.fontMetrics().horizontalAdvance(" "))
        while block.isValid() and top <= self.viewport().height():
            if block.isVisible() and bottom >= 0:
                text = block.text()
                base_x = self.contentOffset().x()
                if self._view_whitespace:
                    for idx, ch in enumerate(text):
                        if ch == " ":
                            x = int(base_x + idx * char_w + (char_w // 2))
                            y = int(top + self.fontMetrics().ascent())
                            painter.drawPoint(x, y)
                if self._show_indent_guides:
                    indent = self._indent_of_line(text)
                    for col in range(self._indent_width, indent + 1, max(1, self._indent_width)):
                        x = int(base_x + col * char_w)
                        painter.drawLine(x, top + 1, x, bottom - 1)
                if self._view_control_chars:
                    for idx, ch in enumerate(text):
                        if ord(ch) < 32 and ch != "\t":
                            x = int(base_x + idx * char_w)
                            y = int(top + self.fontMetrics().ascent())
                            painter.drawText(x, y, ".")
                if self._view_eol:
                    x = int(base_x + len(text) * char_w + 2)
                    y = int(top + self.fontMetrics().ascent())
                    painter.drawText(x, y, "$")
                if self._show_wrap_symbol and self.lineWrapMode() == self.WidgetWidth and len(text) * char_w > self.viewport().width():
                    x = max(2, self.viewport().width() - 14)
                    y = int(top + self.fontMetrics().ascent())
                    painter.drawText(x, y, "\\")
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
        painter.end()
    def paint_margin(self, event) -> None:
        painter = QPainter(self._margin)
        bg = QColor(self._margin_bg_color)
        fg = QColor(self._margin_fg_color)
        painter.fillRect(event.rect(), bg)
        segments = self._margin_segments()

        block = self.firstVisibleBlock()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                line = block.blockNumber()
                text_color = QColor(fg)
                if line == self.textCursor().blockNumber():
                    text_color = fg.lighter(135) if fg.lightness() < 128 else fg.darker(135)
                for idx, kind, x, width in segments:
                    if kind == "number":
                        painter.setPen(text_color)
                        painter.drawText(
                            x,
                            top,
                            width,
                            self.fontMetrics().height(),
                            int(Qt.AlignRight | Qt.AlignVCenter),
                            str(line + 1),
                        )
                    elif kind == "fold":
                        self._paint_fold_glyph(painter, line, x, top)
                    else:
                        self._paint_marker_glyph(painter, line, x, top, margin=idx)
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
        painter.end()

    def handle_margin_click(self, event: QMouseEvent) -> None:
        line = self._line_from_y(int(event.position().y()))
        if line < 0:
            return
        x = int(event.position().x())
        margin_idx = -1
        margin_kind = ""
        for idx, kind, seg_x, width in self._margin_segments():
            if seg_x <= x < (seg_x + width):
                margin_idx = idx
                margin_kind = kind
                break
        if margin_kind == "fold" and line in self._fold_regions:
            if line in self._collapsed_headers:
                self.fold_line(line, expand=True)
            else:
                self.fold_line(line, expand=False)
            return
        if margin_idx >= 0 and self._margin_sensitive.get(margin_idx, False):
            self.marginClicked.emit(margin_idx, line)
        self.setCursorPosition(line, 0)
        self.setFocus()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        mods = event.modifiers()
        add_multi_caret = bool(mods & Qt.ControlModifier) and bool(mods & Qt.AltModifier)
        if self._multiple_selection_enabled and add_multi_caret:
            self._clear_multi_ranges()
            cursor = self.cursorForPosition(event.position().toPoint())
            pos = int(cursor.position())
            if pos in self._additional_carets:
                self._additional_carets = [p for p in self._additional_carets if p != pos]
            else:
                self._additional_carets.append(pos)
                self._additional_carets = sorted(set(self._additional_carets))
            self.viewport().update()
            return
        if event.button() == Qt.LeftButton and self._column_mode:
            cursor = self.cursorForPosition(event.position().toPoint())
            self._column_drag_anchor = (cursor.blockNumber(), cursor.columnNumber())
            self._column_drag_active = True
            self._apply_column_drag(cursor.blockNumber(), cursor.columnNumber())
            self.viewport().update()
            return
        if self._additional_carets:
            self._additional_carets = []
            self._clear_multi_ranges()
            self.viewport().update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._column_drag_active and self._column_drag_anchor is not None:
            cursor = self.cursorForPosition(event.position().toPoint())
            self._apply_column_drag(cursor.blockNumber(), cursor.columnNumber())
            self.viewport().update()
            return
        pos = int(self.cursorForPosition(event.position().toPoint()).position())
        active_idx = self._hotspot_index_at_pos(pos)
        indic_hit = self._indicator_hit_at_pos(pos)
        if active_idx != self._active_hotspot_index:
            self._active_hotspot_index = active_idx
            self._refresh_extra_selections()
        if indic_hit != self._active_indicator_hit:
            self._active_indicator_hit = indic_hit
            self._refresh_extra_selections()
        if active_idx >= 0:
            payload = self._hotspot_ranges[active_idx].payload
            self.hotspotHovered.emit(pos, payload)
            self.viewport().setCursor(Qt.PointingHandCursor)
        elif indic_hit is not None:
            indic_id, _hit_idx = indic_hit
            payload = self._indicator_ranges.get(indic_id, [])[ _hit_idx ].payload if _hit_idx < len(self._indicator_ranges.get(indic_id, [])) else ""
            self.indicatorHovered.emit(indic_id, pos, payload)
            self.viewport().setCursor(Qt.PointingHandCursor)
        else:
            self.viewport().unsetCursor()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._column_drag_active and event.button() == Qt.LeftButton:
            cursor = self.cursorForPosition(event.position().toPoint())
            self._apply_column_drag(cursor.blockNumber(), cursor.columnNumber())
            self._column_drag_active = False
            self.viewport().update()
            return
        if event.button() == Qt.LeftButton:
            pos = int(self.cursorForPosition(event.position().toPoint()).position())
            idx = self._hotspot_index_at_pos(pos)
            if idx >= 0:
                self.hotspotClicked.emit(pos, self._hotspot_ranges[idx].payload)
            else:
                indic_hit = self._indicator_hit_at_pos(pos)
                if indic_hit is not None:
                    indic_id, hit_idx = indic_hit
                    payload = ""
                    ranges = self._indicator_ranges.get(indic_id, [])
                    if 0 <= hit_idx < len(ranges):
                        payload = ranges[hit_idx].payload
                    self.indicatorClicked.emit(indic_id, pos, payload)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            if self._completer.popup().isVisible():
                self._completer.popup().hide()
                return
            self._clear_multi_ranges()
            self._additional_carets = []
            self.viewport().update()
            return
        if self._multi_ranges and (self._column_mode or self._additional_selection_typing):
            if event.key() in {Qt.Key_Backspace, Qt.Key_Delete}:
                self._delete_multi_ranges(backward=event.key() == Qt.Key_Backspace)
                return
            if event.matches(QKeySequence.Paste):
                text = self._clipboard_text()
                if text:
                    if self._multi_paste:
                        lines = text.splitlines()
                        if len(lines) == len(self._multi_ranges):
                            self._replace_ranges_with_text_rows(self._multi_ranges, lines)
                            return
                    self._replace_ranges_with_text(self._multi_ranges, text)
                return
            if event.key() in {Qt.Key_Return, Qt.Key_Enter}:
                self._replace_ranges_with_text(self._multi_ranges, self._block_newline_text())
                return
            if event.key() == Qt.Key_Tab:
                text = "\t" if self._use_tabs else (" " * self._indent_width)
                self._replace_ranges_with_text(self._multi_ranges, text)
                return
            text = event.text()
            if text and not (event.modifiers() & (Qt.ControlModifier | Qt.MetaModifier)):
                self._replace_ranges_with_text(self._multi_ranges, text)
                return
        if not (self._multiple_selection_enabled and self._additional_selection_typing and self._additional_carets):
            super().keyPressEvent(event)
            return
        if self.textCursor().hasSelection():
            super().keyPressEvent(event)
            return
        if event.key() in {Qt.Key_Left, Qt.Key_Right, Qt.Key_Home, Qt.Key_End}:
            self._move_all_carets(event.key(), keep_anchor=bool(event.modifiers() & Qt.ShiftModifier))
            return
        if event.key() in {Qt.Key_Backspace, Qt.Key_Delete}:
            self._delete_at_all_carets(backward=event.key() == Qt.Key_Backspace)
            return
        if event.matches(QKeySequence.Paste):
            text = self._clipboard_text()
            if text:
                if self._multi_paste:
                    positions = sorted(set([self.textCursor().position(), *self._additional_carets]))
                    lines = text.splitlines()
                    if len(lines) == len(positions):
                        self._insert_rows_at_all_carets(lines)
                        return
                self._insert_text_at_all_carets(text)
                return
        if event.key() in {Qt.Key_Return, Qt.Key_Enter}:
            self._insert_text_at_all_carets(self._block_newline_text())
            return
        if event.key() == Qt.Key_Tab:
            self._insert_text_at_all_carets("\t" if self._use_tabs else (" " * self._indent_width))
            return
        text = event.text()
        if text and not (event.modifiers() & (Qt.ControlModifier | Qt.MetaModifier)):
            self._insert_text_at_all_carets(text)
            return
        force_completion = event.key() == Qt.Key_Space and bool(event.modifiers() & Qt.ControlModifier)
        super().keyPressEvent(event)
        if force_completion:
            self._invoke_completion(force=True)
            return
        if text and self._auto_completion_source != self.AcsNone:
            self._invoke_completion(force=False)

    def _insert_text_at_all_carets(self, text: str) -> None:
        positions = sorted(set([self.textCursor().position(), *self._additional_carets]))
        if not positions:
            return
        primary = self.textCursor().position()
        delta = 0
        new_positions: list[int] = []
        cursor = self.textCursor()
        cursor.beginEditBlock()
        for pos in positions:
            adjusted = pos + delta
            cursor.setPosition(adjusted)
            cursor.insertText(text)
            new_positions.append(adjusted + len(text))
            delta += len(text)
        cursor.endEditBlock()
        if primary in positions:
            idx = positions.index(primary)
            new_primary = new_positions[idx]
        else:
            new_primary = new_positions[-1]
        caret = self.textCursor()
        caret.setPosition(new_primary)
        self.setTextCursor(caret)
        self._additional_carets = [p for p in new_positions if p != new_primary]
        self.viewport().update()

    def _insert_rows_at_all_carets(self, rows: list[str]) -> None:
        positions = sorted(set([self.textCursor().position(), *self._additional_carets]))
        if not positions or len(rows) != len(positions):
            return
        primary = self.textCursor().position()
        shift = 0
        new_positions: list[int] = []
        cursor = self.textCursor()
        cursor.beginEditBlock()
        for pos, row in zip(positions, rows):
            adjusted = pos + shift
            cursor.setPosition(adjusted)
            cursor.insertText(row)
            new_positions.append(adjusted + len(row))
            shift += len(row)
        cursor.endEditBlock()
        if primary in positions:
            idx = positions.index(primary)
            new_primary = new_positions[idx]
        else:
            new_primary = new_positions[-1]
        caret = self.textCursor()
        caret.setPosition(new_primary)
        self.setTextCursor(caret)
        self._additional_carets = [p for p in new_positions if p != new_primary]
        self.viewport().update()

    def _move_all_carets(self, key: int, *, keep_anchor: bool) -> None:
        positions = sorted(set([self.textCursor().position(), *self._additional_carets]))
        if not positions:
            return
        source = self.toPlainText()
        new_positions: list[int] = []
        for pos in positions:
            if key == Qt.Key_Left:
                new_pos = max(0, pos - 1)
            elif key == Qt.Key_Right:
                new_pos = min(len(source), pos + 1)
            elif key == Qt.Key_Home:
                line, _col = self._line_col_from_pos(pos)
                new_pos = self._index_from_line_col(line, 0)
            elif key == Qt.Key_End:
                line, _col = self._line_col_from_pos(pos)
                block = self.document().findBlockByNumber(line)
                new_pos = block.position() + (len(block.text()) if block.isValid() else 0)
            else:
                new_pos = pos
            new_positions.append(new_pos)
        primary_new = new_positions[-1]
        tc = self.textCursor()
        if keep_anchor:
            tc.setPosition(tc.position())
            tc.setPosition(primary_new, QTextCursor.KeepAnchor)
        else:
            tc.setPosition(primary_new)
        self.setTextCursor(tc)
        self._additional_carets = new_positions[:-1]
        self.viewport().update()

    def _delete_at_all_carets(self, *, backward: bool) -> None:
        positions = sorted(set([self.textCursor().position(), *self._additional_carets]))
        if not positions:
            return
        primary = self.textCursor().position()
        shift = 0
        new_positions: list[int] = []
        cursor = self.textCursor()
        cursor.beginEditBlock()
        for pos in positions:
            adjusted = max(0, min(len(self.toPlainText()), pos + shift))
            if backward:
                if adjusted <= 0:
                    new_positions.append(0)
                    continue
                cursor.setPosition(adjusted - 1)
                cursor.setPosition(adjusted, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
                shift -= 1
                new_positions.append(adjusted - 1)
            else:
                if adjusted >= len(self.toPlainText()):
                    new_positions.append(adjusted)
                    continue
                cursor.setPosition(adjusted)
                cursor.setPosition(adjusted + 1, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
                shift -= 1
                new_positions.append(adjusted)
        cursor.endEditBlock()
        if primary in positions:
            idx = positions.index(primary)
            new_primary = new_positions[idx]
        else:
            new_primary = new_positions[-1]
        caret = self.textCursor()
        caret.setPosition(max(0, new_primary))
        self.setTextCursor(caret)
        self._additional_carets = [p for p in new_positions if p != new_primary]
        self.viewport().update()

    def _replace_ranges_with_text(self, ranges: list[tuple[int, int]], text: str) -> None:
        ordered = sorted((min(s, e), max(s, e)) for s, e in ranges)
        if not ordered:
            return
        primary = self.textCursor().position()
        shift = 0
        new_positions: list[int] = []
        cursor = self.textCursor()
        cursor.beginEditBlock()
        for start, end in ordered:
            start_adj = max(0, min(len(self.toPlainText()), start + shift))
            end_adj = max(start_adj, min(len(self.toPlainText()), end + shift))
            cursor.setPosition(start_adj)
            cursor.setPosition(end_adj, QTextCursor.KeepAnchor)
            cursor.insertText(text)
            delta = len(text) - (end_adj - start_adj)
            shift += delta
            new_positions.append(start_adj + len(text))
        cursor.endEditBlock()
        candidate_old = [start for start, _ in ordered]
        if candidate_old:
            primary_idx = min(range(len(candidate_old)), key=lambda i: abs(candidate_old[i] - primary))
            new_primary = new_positions[primary_idx]
        else:
            new_primary = self.textCursor().position()
        caret = self.textCursor()
        caret.setPosition(max(0, new_primary))
        self.setTextCursor(caret)
        self._additional_carets = [p for p in new_positions if p != new_primary]
        if self._column_mode and self._column_block is not None and "\n" not in text and "\r" not in text:
            width = len(text)
            self._column_block.col_hi = self._column_block.col_lo + max(0, width)
            self._reapply_column_block()
        else:
            self._clear_multi_ranges()
        self.viewport().update()

    def _replace_ranges_with_text_rows(self, ranges: list[tuple[int, int]], rows: list[str]) -> None:
        ordered = sorted((min(s, e), max(s, e), idx) for idx, (s, e) in enumerate(ranges))
        if not ordered or len(rows) != len(ordered):
            return
        primary = self.textCursor().position()
        shift = 0
        new_positions: list[int] = [0] * len(rows)
        cursor = self.textCursor()
        cursor.beginEditBlock()
        for start, end, idx in ordered:
            text = rows[idx]
            start_adj = max(0, min(len(self.toPlainText()), start + shift))
            end_adj = max(start_adj, min(len(self.toPlainText()), end + shift))
            cursor.setPosition(start_adj)
            cursor.setPosition(end_adj, QTextCursor.KeepAnchor)
            cursor.insertText(text)
            delta = len(text) - (end_adj - start_adj)
            shift += delta
            new_positions[idx] = start_adj + len(text)
        cursor.endEditBlock()
        candidate_old = [min(s, e) for s, e in ranges]
        if candidate_old:
            primary_idx = min(range(len(candidate_old)), key=lambda i: abs(candidate_old[i] - primary))
            new_primary = new_positions[primary_idx]
        else:
            new_primary = self.textCursor().position()
        caret = self.textCursor()
        caret.setPosition(max(0, new_primary))
        self.setTextCursor(caret)
        self._additional_carets = [p for p in new_positions if p != new_primary]
        if self._column_mode and self._column_block is not None:
            width = max((len(row) for row in rows), default=0)
            self._column_block.col_hi = self._column_block.col_lo + max(0, width)
            self._reapply_column_block()
        else:
            self._clear_multi_ranges()
        self.viewport().update()

    def _delete_multi_ranges(self, *, backward: bool) -> None:
        ranges = [(s, e) for s, e in self._multi_ranges if s != e]
        if ranges:
            self._replace_ranges_with_text(ranges, "")
            return
        self._delete_at_all_carets(backward=backward)

    def _clipboard_text(self) -> str:
        try:
            from PySide6.QtGui import QGuiApplication

            clip = QGuiApplication.clipboard()
            return clip.text() if clip is not None else ""
        except Exception:
            return ""

    def _on_text_changed(self) -> None:
        self._rebuild_pending = True
        if not self._rebuild_timer.isActive():
            self._rebuild_timer.start()

    def _on_cursor_changed(self) -> None:
        self._auto_brace_match()
        self._margin.update()
        self.viewport().update()

    def _update_margin_width(self, _new_count: int) -> None:
        self.setViewportMargins(self.margin_width(), 0, 0, 0)
        self._margin.setFixedWidth(self.margin_width())

    def _update_margin_area(self, rect, dy: int) -> None:
        if dy:
            self._margin.scroll(0, dy)
        else:
            self._margin.update(0, rect.y(), self._margin.width(), rect.height())

    def _paint_marker_glyph(self, painter: QPainter, line: int, x: int, top: int, *, margin: int) -> None:
        marker_id = self._first_masked_marker_for_line(line, margin=margin)
        if marker_id is None:
            return
        color = self._marker_colors.get(marker_id, QColor("#ffcc00"))
        symbol = int(self._marker_symbols.get(marker_id, self.Circle))
        h = self.fontMetrics().height()
        size = max(6, min(10, h - 2))
        left = int(x + 2)
        top_y = int(top + max(1, (h - size) // 2))
        rect = QRect(left, top_y, size, size)
        painter.setBrush(color)
        painter.setPen(color.darker(130))
        if symbol == self.Empty:
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(rect)
        elif symbol in {self.Circle, self.RoundRect}:
            if symbol == self.RoundRect:
                painter.drawRoundedRect(rect, 2, 2)
            else:
                painter.drawEllipse(rect)
        elif symbol in {self.RightArrow, self.Arrow, self.ShortArrow}:
            cy = rect.center().y()
            tip = rect.right()
            tail = rect.left()
            half = max(2, rect.height() // 3)
            poly = QPolygon([QPoint(tail, cy - half), QPoint(tip, cy), QPoint(tail, cy + half)])
            painter.drawPolygon(poly)
        elif symbol == self.Plus:
            painter.drawRect(rect)
            painter.drawLine(rect.left() + 2, rect.center().y(), rect.right() - 2, rect.center().y())
            painter.drawLine(rect.center().x(), rect.top() + 2, rect.center().x(), rect.bottom() - 2)
        elif symbol == self.Minus:
            painter.drawRect(rect)
            painter.drawLine(rect.left() + 2, rect.center().y(), rect.right() - 2, rect.center().y())
        elif symbol == self.SmallRect:
            painter.drawRect(rect.adjusted(1, 1, -1, -1))
        else:
            painter.drawEllipse(rect)

    def _first_masked_marker_for_line(self, line: int, *, margin: int) -> int | None:
        mask = int(self._margin_marker_masks.get(int(margin), -1))
        for mid, lines in self._markers.items():
            if line not in lines:
                continue
            if mask == -1:
                return mid
            if 0 <= int(mid) < 63 and (mask & (1 << int(mid))):
                return mid
        return None

    def _paint_fold_glyph(self, painter: QPainter, line: int, x: int, top: int) -> None:
        if not self._folding_enabled or line not in self._fold_regions:
            return
        h = self.fontMetrics().height()
        y = top + max(1, (h - 10) // 2)
        box = QRect(x + 2, y, 10, 10)
        painter.setPen(QColor("#8f95a1"))
        painter.setBrush(QColor("#2c2f36"))
        painter.drawRect(box)
        painter.drawLine(box.left() + 2, box.center().y(), box.right() - 2, box.center().y())
        if line in self._collapsed_headers:
            painter.drawLine(box.center().x(), box.top() + 2, box.center().x(), box.bottom() - 2)

    def _line_from_y(self, y: int) -> int:
        block = self.firstVisibleBlock()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        while block.isValid():
            if block.isVisible() and top <= y <= bottom:
                return block.blockNumber()
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
        return -1

    def _rebuild_fold_regions(self) -> None:
        lines = self.toPlainText().splitlines()
        if not lines:
            self._fold_regions = {}
            self._collapsed_headers.clear()
            self._fold_hidden_lines.clear()
            return
        non_blank: list[tuple[int, int]] = []
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            non_blank.append((idx, self._indent_of_line(line)))
        if len(non_blank) < 2:
            self._fold_regions = {}
            self._collapsed_headers.clear()
            self._fold_hidden_lines.clear()
            return
        regions: dict[int, FoldRegion] = {}
        stack: list[tuple[int, int]] = []
        prev_line, prev_indent = non_blank[0]
        for current_line, current_indent in non_blank[1:]:
            while stack and current_indent <= stack[-1][1]:
                header_line, header_indent = stack.pop()
                regions[header_line] = FoldRegion(
                    start=header_line,
                    end=prev_line,
                    level=max(0, header_indent // max(1, self._indent_width)),
                )
            if current_indent > prev_indent:
                stack.append((prev_line, prev_indent))
            prev_line, prev_indent = current_line, current_indent
        while stack:
            header_line, header_indent = stack.pop()
            regions[header_line] = FoldRegion(
                start=header_line,
                end=prev_line,
                level=max(0, header_indent // max(1, self._indent_width)),
            )
        indent_regions = {k: v for k, v in regions.items() if v.end > v.start}
        bracket_regions = self._build_bracket_fold_regions(lines)
        merged: dict[int, FoldRegion] = {}
        for start, region in indent_regions.items():
            merged[start] = region
        for start, region in bracket_regions.items():
            current = merged.get(start)
            if current is None:
                merged[start] = region
                continue
            if region.end > current.end:
                merged[start] = FoldRegion(start=start, end=region.end, level=min(current.level, region.level))
        self._fold_regions = merged
        self._collapsed_headers = {line for line in self._collapsed_headers if line in self._fold_regions}
        self._rebuild_fold_hidden_lines()

    def _build_bracket_fold_regions(self, lines: list[str]) -> dict[int, FoldRegion]:
        regions: dict[int, FoldRegion] = {}
        stack: list[tuple[int, int]] = []
        in_block_comment = False
        in_string: str | None = None
        escape = False
        for line_no, line in enumerate(lines):
            i = 0
            while i < len(line):
                ch = line[i]
                nxt = line[i + 1] if i + 1 < len(line) else ""
                if in_string is not None:
                    if escape:
                        escape = False
                        i += 1
                        continue
                    if ch == "\\":
                        escape = True
                        i += 1
                        continue
                    if ch == in_string:
                        in_string = None
                    i += 1
                    continue
                if in_block_comment:
                    if ch == "*" and nxt == "/":
                        in_block_comment = False
                        i += 2
                        continue
                    i += 1
                    continue
                if ch == "/" and nxt == "/":
                    break
                if ch == "/" and nxt == "*":
                    in_block_comment = True
                    i += 2
                    continue
                if ch in {"'", '"', "`"}:
                    in_string = ch
                    i += 1
                    continue
                if ch == "{":
                    stack.append((line_no, len(stack)))
                elif ch == "}":
                    if stack:
                        start_line, depth = stack.pop()
                        if line_no > start_line:
                            current = regions.get(start_line)
                            candidate = FoldRegion(start=start_line, end=line_no, level=depth)
                            if current is None or candidate.end > current.end:
                                regions[start_line] = candidate
                i += 1
        return regions

    def _rebuild_fold_hidden_lines(self) -> None:
        hidden: set[int] = set()
        for header in self._collapsed_headers:
            region = self._fold_regions.get(header)
            if region is None:
                continue
            for line in range(region.start + 1, region.end + 1):
                hidden.add(line)
        self._fold_hidden_lines = hidden

    def _refresh_visibility(self) -> None:
        hidden_union = self._hidden_lines | self._fold_hidden_lines
        block = self.document().firstBlock()
        while block.isValid():
            line = block.blockNumber()
            should_show = line not in hidden_union
            if block.isVisible() != should_show:
                block.setVisible(should_show)
            block = block.next()
        self.document().markContentsDirty(0, self.document().characterCount())
        self.viewport().update()
        self._margin.update()

    def _indent_of_line(self, line: str) -> int:
        total = 0
        for ch in line:
            if ch == " ":
                total += 1
            elif ch == "\t":
                total += max(1, self._indent_width)
            else:
                break
        return total

    def _index_from_line_col(self, line: int, col: int) -> int:
        line = max(0, int(line))
        col = max(0, int(col))
        block = self.document().findBlockByNumber(line)
        if not block.isValid():
            return max(0, len(self.toPlainText()))
        return min(block.position() + col, block.position() + len(block.text()))

    def _line_col_from_pos(self, pos: int) -> tuple[int, int]:
        block = self.document().findBlock(max(0, min(pos, len(self.toPlainText()))))
        return block.blockNumber(), max(0, min(pos - block.position(), len(block.text())))

    def _clear_multi_ranges(self) -> None:
        self._multi_ranges = []
        self._column_block = None

    def _apply_column_drag(self, line: int, col: int) -> None:
        if self._column_drag_anchor is None:
            return
        a_line, a_col = self._column_drag_anchor
        line_lo = min(a_line, line)
        line_hi = max(a_line, line)
        col_lo = min(a_col, col)
        col_hi = max(a_col, col)
        ranges: list[tuple[int, int]] = []
        carets: list[int] = []
        for ln in range(line_lo, line_hi + 1):
            start = self._index_from_line_col(ln, col_lo)
            end = self._index_from_line_col(ln, col_hi)
            ranges.append((start, end))
            carets.append(end)
        if not carets:
            return
        primary = carets[-1]
        tc = self.textCursor()
        tc.setPosition(primary)
        self.setTextCursor(tc)
        self._additional_carets = [p for p in carets[:-1] if p != primary]
        self._multi_ranges = ranges
        self._column_block = ColumnBlock(
            line_lo=line_lo,
            line_hi=line_hi,
            col_lo=col_lo,
            col_hi=col_hi,
        )

    def _reapply_column_block(self) -> None:
        block = self._column_block
        if block is None:
            return
        ranges: list[tuple[int, int]] = []
        carets: list[int] = []
        for ln in range(block.line_lo, block.line_hi + 1):
            start = self._index_from_line_col(ln, block.col_lo)
            end = self._index_from_line_col(ln, block.col_hi)
            ranges.append((start, end))
            carets.append(end)
        if not carets:
            self._clear_multi_ranges()
            return
        primary = carets[-1]
        tc = self.textCursor()
        tc.setPosition(primary)
        self.setTextCursor(tc)
        self._additional_carets = [p for p in carets[:-1] if p != primary]
        self._multi_ranges = ranges

    def _block_newline_text(self) -> str:
        cursor = self.textCursor()
        block = cursor.block()
        line = block.text() if block.isValid() else ""
        indent_chars: list[str] = []
        for ch in line:
            if ch in {" ", "\t"}:
                indent_chars.append(ch)
            else:
                break
        return "\n" + "".join(indent_chars)

    def _refresh_completion_words(self) -> None:
        if self._auto_completion_source == self.AcsNone:
            self._completion_model.setStringList([])
            return
        words = set(self._completion_words)
        if self._auto_completion_source in {self.AcsDocument, self.AcsAll}:
            words.update(self._document_words())
        if self._auto_completion_source in {self.AcsAPIs, self.AcsAll}:
            words.update(self._api_words())
            if self._completion_words:
                words.update(self._completion_words)
        self._completion_model.setStringList(sorted(words))

    def _api_words(self) -> set[str]:
        apis = self._apis
        if apis is None:
            return set()
        for attr in ("api_list", "words", "_words", "_api"):
            value = getattr(apis, attr, None)
            if callable(value):
                try:
                    value = value()
                except Exception:
                    continue
            if value is None:
                continue
            try:
                return {str(item).strip() for item in value if str(item).strip()}
            except Exception:
                continue
        return set()

    def _flush_deferred_rebuild(self) -> None:
        if not self._rebuild_pending:
            return
        self._rebuild_pending = False
        self._rebuild_fold_regions()
        self._rebuild_lexer_ranges()
        self._refresh_visibility()
        self._refresh_extra_selections()
        self._margin.update()

    def _document_words(self) -> set[str]:
        return {m.group(0) for m in re.finditer(r"[A-Za-z_][A-Za-z0-9_]{1,}", self.toPlainText())}

    def _current_word_span(self) -> tuple[int, int]:
        cursor = self.textCursor()
        pos = cursor.position()
        text = self.toPlainText()
        if not text:
            return pos, pos
        start = pos
        while start > 0 and (text[start - 1].isalnum() or text[start - 1] == "_"):
            start -= 1
        end = pos
        while end < len(text) and (text[end].isalnum() or text[end] == "_"):
            end += 1
        return start, end

    def _invoke_completion(self, *, force: bool) -> None:
        self._refresh_completion_words()
        start, end = self._current_word_span()
        prefix = self.toPlainText()[start:end]
        threshold = max(1, int(self._auto_completion_threshold))
        if not force and len(prefix) < threshold:
            self._completer.popup().hide()
            return
        self._completer.setCompletionPrefix(prefix)
        popup = self._completer.popup()
        if popup is None:
            return
        cr = self.cursorRect()
        cr.setWidth(max(220, popup.sizeHintForColumn(0) + 24))
        self._completer.complete(cr)

    def _insert_completion(self, completion: str) -> None:
        text = str(completion or "")
        if not text:
            return
        start, end = self._current_word_span()
        cursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        cursor.insertText(text)
        self.setTextCursor(cursor)

    def _rebuild_lexer_ranges(self) -> None:
        if self._lexer is None:
            self._lexer_ranges = []
            return
        language = self._detect_lexer_language(self._lexer)
        source = self.toPlainText()
        if not source:
            self._lexer_ranges = []
            return
        ranges: list[tuple[int, int, int]] = []
        if language == "python":
            kw = r"\b(?:and|as|assert|break|class|continue|def|del|elif|else|except|False|finally|for|from|global|if|import|in|is|lambda|None|nonlocal|not|or|pass|raise|return|True|try|while|with|yield)\b"
            ranges.extend(self._find_style_ranges(source, kw, 1))
            ranges.extend(self._find_style_ranges(source, r"#.*", 2))
            ranges.extend(self._find_style_ranges(source, r"('([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\")", 3))
            ranges.extend(self._find_style_ranges(source, r"\b\d+(\.\d+)?\b", 4))
        elif language in {"javascript", "typescript", "json"}:
            kw = r"\b(?:break|case|catch|class|const|continue|debugger|default|delete|do|else|export|extends|false|finally|for|function|if|import|in|instanceof|let|new|null|return|super|switch|this|throw|true|try|typeof|var|void|while|with|yield)\b"
            ranges.extend(self._find_style_ranges(source, kw, 1))
            ranges.extend(self._find_style_ranges(source, r"//.*", 2))
            ranges.extend(self._find_style_ranges(source, r"/\*[\s\S]*?\*/", 2))
            ranges.extend(self._find_style_ranges(source, r"('([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\"|`([^`\\]|\\.)*`)", 3))
            ranges.extend(self._find_style_ranges(source, r"\b\d+(\.\d+)?\b", 4))
        elif language == "markdown":
            ranges.extend(self._find_style_ranges(source, r"^#{1,6} .*$", 5, flags=re.MULTILINE))
            ranges.extend(self._find_style_ranges(source, r"`{1,3}[^`]+`{1,3}", 3))
            ranges.extend(self._find_style_ranges(source, r"\*\*[^*]+\*\*", 1))
        self._lexer_ranges = ranges
        self._ensure_default_styles()

    def _detect_lexer_language(self, lexer) -> str:
        label = ""
        for attr in ("language", "name"):
            value = getattr(lexer, attr, None)
            if callable(value):
                try:
                    label = str(value()).strip().lower()
                except Exception:
                    label = ""
            else:
                label = str(value or "").strip().lower()
            if label:
                break
        if not label:
            label = lexer.__class__.__name__.lower()
        if "python" in label:
            return "python"
        if "json" in label:
            return "json"
        if "typescript" in label:
            return "typescript"
        if "javascript" in label or "js" in label:
            return "javascript"
        if "markdown" in label or "md" in label:
            return "markdown"
        return "plain"

    def _find_style_ranges(self, source: str, pattern: str, style_id: int, *, flags: int = 0) -> list[tuple[int, int, int]]:
        out: list[tuple[int, int, int]] = []
        for match in re.finditer(pattern, source, flags):
            lo, hi = match.span()
            if hi > lo:
                out.append((lo, hi, int(style_id)))
        return out

    def _ensure_default_styles(self) -> None:
        defaults: dict[int, tuple[str, bool, bool, bool]] = {
            1: ("#b96ad9", True, False, False),
            2: ("#7a828f", False, True, False),
            3: ("#6fb1ff", False, False, False),
            4: ("#f2c879", False, False, False),
            5: ("#cfd8e3", True, False, False),
        }
        for style_id, (color, bold, italic, under) in defaults.items():
            if style_id in self._style_formats:
                continue
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            fmt.setFontWeight(75 if bold else 50)
            fmt.setFontItalic(italic)
            fmt.setFontUnderline(under)
            self._style_formats[style_id] = fmt

    def _refresh_extra_selections(self) -> None:
        selections: list[QTextEdit.ExtraSelection] = []
        if self._caret_line_visible:
            current_line = QTextEdit.ExtraSelection()
            current_line.cursor = self.textCursor()
            current_line.cursor.clearSelection()
            line_fmt = QTextCharFormat()
            bg = QColor(self._caret_line_color)
            if not bg.isValid():
                bg = self.palette().alternateBase().color()
            line_fmt.setBackground(bg)
            line_fmt.setProperty(QTextCharFormat.FullWidthSelection, True)
            current_line.format = line_fmt
            selections.append(current_line)
        doc_len = len(self.toPlainText())
        for lo, hi, style_id in [*self._lexer_ranges, *self._style_ranges]:
            fmt = self._style_formats.get(style_id)
            if fmt is None:
                continue
            sel = QTextEdit.ExtraSelection()
            sel.cursor = self.textCursor()
            sel.cursor.setPosition(max(0, min(lo, doc_len)))
            sel.cursor.setPosition(max(0, min(hi, doc_len)), QTextCursor.KeepAnchor)
            sel.format = QTextCharFormat(fmt)
            selections.append(sel)
        for indic_id, ranges in self._indicator_ranges.items():
            color = self._indicator_colors.get(indic_id, QColor("#f4d03f"))
            style = int(self._indicator_styles.get(indic_id, 0))
            for idx, seg in enumerate(ranges):
                lo = int(seg.start)
                hi = int(seg.end)
                sel = QTextEdit.ExtraSelection()
                sel.cursor = self.textCursor()
                sel.cursor.setPosition(max(0, min(lo, doc_len)))
                sel.cursor.setPosition(max(0, min(hi, doc_len)), QTextCursor.KeepAnchor)
                fmt = QTextCharFormat()
                hit = self._active_indicator_hit == (int(indic_id), int(idx))
                active_color = color.lighter(130) if hit else color
                if style == self.INDIC_HIDDEN:
                    continue
                if style == self.INDIC_PLAIN:
                    fmt.setUnderlineStyle(QTextCharFormat.SingleUnderline)
                    fmt.setUnderlineColor(active_color)
                elif style == self.INDIC_SQUIGGLE:
                    fmt.setUnderlineStyle(QTextCharFormat.WaveUnderline)
                    fmt.setUnderlineColor(active_color)
                elif style == self.INDIC_TT:
                    fmt.setUnderlineStyle(QTextCharFormat.DotLine)
                    fmt.setUnderlineColor(active_color)
                elif style == self.INDIC_DIAGONAL:
                    fmt.setUnderlineStyle(QTextCharFormat.DashUnderline)
                    fmt.setUnderlineColor(active_color)
                elif style == self.INDIC_STRIKE:
                    fmt.setFontStrikeOut(True)
                    fmt.setForeground(active_color)
                else:
                    shade = QColor(active_color)
                    shade.setAlpha(90 if style == self.INDIC_BOX else 70)
                    fmt.setBackground(shade)
                    if style == self.INDIC_ROUNDBOX:
                        fmt.setUnderlineStyle(QTextCharFormat.SingleUnderline)
                        fmt.setUnderlineColor(active_color.darker(120))
                sel.format = fmt
                selections.append(sel)
        for idx, hs in enumerate(self._hotspot_ranges):
            sel = QTextEdit.ExtraSelection()
            sel.cursor = self.textCursor()
            sel.cursor.setPosition(max(0, min(hs.start, doc_len)))
            sel.cursor.setPosition(max(0, min(hs.end, doc_len)), QTextCursor.KeepAnchor)
            fmt = QTextCharFormat()
            fmt.setForeground(self._hotspot_active_color if idx == self._active_hotspot_index else self._hotspot_color)
            fmt.setFontUnderline(self._hotspot_underline)
            sel.format = fmt
            selections.append(sel)
        for ranges in self._background_overlays.values():
            for lo, hi, color in ranges:
                sel = QTextEdit.ExtraSelection()
                sel.cursor = self.textCursor()
                sel.cursor.setPosition(max(0, min(lo, doc_len)))
                sel.cursor.setPosition(max(0, min(hi, doc_len)), QTextCursor.KeepAnchor)
                fmt = QTextCharFormat()
                fmt.setBackground(color)
                sel.format = fmt
                selections.append(sel)
        self.setExtraSelections(selections)

    @staticmethod
    def _qcolor_from_scintilla_rgb(value: int) -> QColor:
        iv = int(value)
        r = iv & 0xFF
        g = (iv >> 8) & 0xFF
        b = (iv >> 16) & 0xFF
        return QColor(r, g, b)

    def _auto_brace_match(self) -> None:
        text = self.toPlainText()
        if not text:
            self._brace_match_pair = None
            return
        pos = self.textCursor().position()
        pair = self._find_nearby_brace_pair(text, pos)
        self._brace_match_pair = pair

    def _find_nearby_brace_pair(self, text: str, pos: int) -> tuple[int, int] | None:
        if pos > 0 and pos - 1 < len(text):
            pair = self._find_brace_pair_at(text, pos - 1)
            if pair is not None:
                return pair
        if pos < len(text):
            pair = self._find_brace_pair_at(text, pos)
            if pair is not None:
                return pair
        return None

    def _find_brace_pair_at(self, text: str, index: int) -> tuple[int, int] | None:
        if index < 0 or index >= len(text):
            return None
        ch = text[index]
        opens = {"(": ")", "[": "]", "{": "}"}
        closes = {")": "(", "]": "[", "}": "{"}
        if ch in opens:
            target = opens[ch]
            depth = 0
            for i in range(index + 1, len(text)):
                c = text[i]
                if c == ch:
                    depth += 1
                elif c == target:
                    if depth == 0:
                        return index, i
                    depth -= 1
            return index, -1
        if ch in closes:
            target = closes[ch]
            depth = 0
            for i in range(index - 1, -1, -1):
                c = text[i]
                if c == ch:
                    depth += 1
                elif c == target:
                    if depth == 0:
                        return i, index
                    depth -= 1
            return -1, index
        return None
