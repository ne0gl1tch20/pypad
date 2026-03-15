"""Handle compatibility-layer state transitions that do not fit into the core editing command groups.

This module belongs to the Scintilla compatibility layer used when native QScintilla is unavailable. It helps explain how `pypad.ui.editor.scintilla_compat` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations


def handle_extra_state_command(editor, msg: int, args: tuple[int, ...]) -> int | None:
    """Apply Scintilla-compatible commands that mutate extra editor state."""
    if msg == int(editor.SCI_SETWHITESPACEFORE):
        value = int(args[0]) if args else 0
        editor._whitespace_fore = editor._qcolor_from_scintilla_rgb(value)
        return int(value)
    if msg == int(editor.SCI_GETWHITESPACEFORE):
        c = editor._whitespace_fore
        return int(c.red()) | (int(c.green()) << 8) | (int(c.blue()) << 16)
    if msg == int(editor.SCI_SETWHITESPACEBACK):
        value = int(args[0]) if args else 0
        editor._whitespace_back = editor._qcolor_from_scintilla_rgb(value)
        return int(value)
    if msg == int(editor.SCI_GETWHITESPACEBACK):
        c = editor._whitespace_back
        return int(c.red()) | (int(c.green()) << 8) | (int(c.blue()) << 16)
    if msg == int(editor.SCI_SETWHITESPACESIZE):
        editor._whitespace_size = max(1, int(args[0]) if args else 1)
        return int(editor._whitespace_size)
    if msg == int(editor.SCI_GETWHITESPACESIZE):
        return int(editor._whitespace_size)
    if msg == int(editor.SCI_SETEXTRAFONTFLAG):
        editor._extra_font_flag = int(args[0]) if args else 0
        return int(editor._extra_font_flag)
    if msg == int(editor.SCI_GETEXTRAFONTFLAG):
        return int(editor._extra_font_flag)
    if msg == int(editor.SCI_SETENDATLASTLINE):
        editor._end_at_last_line = bool(int(args[0])) if args else False
        return 1 if editor._end_at_last_line else 0
    if msg == int(editor.SCI_GETENDATLASTLINE):
        return 1 if editor._end_at_last_line else 0
    if msg == int(editor.SCI_SETPUNCTUATIONCHARS):
        if len(args) >= 2:
            editor._punctuation_chars = editor._read_scintilla_text_arg(args[1], int(args[0]))
        else:
            editor._punctuation_chars = ""
        return len(editor._punctuation_chars)
    if msg == int(editor.SCI_GETPUNCTUATIONCHARS):
        if len(args) >= 1:
            editor._write_scintilla_text_target(args[0], editor._punctuation_chars)
        return len(editor._punctuation_chars)
    if msg == int(editor.SCI_SETWORDCHARS):
        if len(args) >= 2:
            editor._word_chars = editor._read_scintilla_text_arg(args[1], int(args[0]))
        else:
            editor._word_chars = ""
        return len(editor._word_chars)
    if msg == int(editor.SCI_GETWORDCHARS):
        if len(args) >= 1:
            editor._write_scintilla_text_target(args[0], editor._word_chars)
        return len(editor._word_chars)
    if msg == int(editor.SCI_SETLINEENDTYPESALLOWED):
        editor._line_end_types_allowed = int(args[0]) if args else 0
        return int(editor._line_end_types_allowed)
    if msg == int(editor.SCI_GETLINEENDTYPESALLOWED):
        return int(editor._line_end_types_allowed)
    if msg == int(editor.SCI_SETACCESSIBILITY):
        editor._accessibility = int(args[0]) if args else 0
        return int(editor._accessibility)
    if msg == int(editor.SCI_GETACCESSIBILITY):
        return int(editor._accessibility)
    if msg == int(editor.SCI_SETBIDIRECTIONAL):
        editor._bidirectional = int(args[0]) if args else 0
        return int(editor._bidirectional)
    if msg == int(editor.SCI_GETBIDIRECTIONAL):
        return int(editor._bidirectional)
    if msg == int(editor.SCI_SETIDLESTYLING):
        editor._idle_styling = int(args[0]) if args else 0
        return int(editor._idle_styling)
    if msg == int(editor.SCI_GETIDLESTYLING):
        return int(editor._idle_styling)
    if msg == int(editor.SCI_SETSELALPHA):
        editor._sel_alpha = max(0, min(256, int(args[0]) if args else 256))
        return int(editor._sel_alpha)
    if msg == int(editor.SCI_GETSELALPHA):
        return int(editor._sel_alpha)
    if msg == int(editor.SCI_SETADDITIONALSELALPHA):
        editor._additional_sel_alpha = max(0, min(256, int(args[0]) if args else 256))
        return int(editor._additional_sel_alpha)
    if msg == int(editor.SCI_GETADDITIONALSELALPHA):
        return int(editor._additional_sel_alpha)
    if msg == int(editor.SCI_SETSELEOLFILLED):
        editor._sel_eol_filled = bool(int(args[0])) if args else False
        return 1 if editor._sel_eol_filled else 0
    if msg == int(editor.SCI_GETSELEOLFILLED):
        return 1 if editor._sel_eol_filled else 0
    if msg == int(editor.SCI_SETFONTLOCALE):
        if len(args) >= 2:
            editor._font_locale = editor._read_scintilla_text_arg(args[1], int(args[0]))
        else:
            editor._font_locale = ""
        return len(editor._font_locale)
    if msg == int(editor.SCI_GETFONTLOCALE):
        if len(args) >= 1:
            editor._write_scintilla_text_target(args[0], editor._font_locale)
        return len(editor._font_locale)
    if msg == int(editor.SCI_SETKEYSUNICODE):
        editor._keys_unicode = bool(int(args[0])) if args else False
        return 1 if editor._keys_unicode else 0
    if msg == int(editor.SCI_GETKEYSUNICODE):
        return 1 if editor._keys_unicode else 0
    if msg == int(editor.SCI_SETAUTOCASESENSITIVE):
        editor._auto_case_sensitive = bool(int(args[0])) if args else False
        return 1 if editor._auto_case_sensitive else 0
    if msg == int(editor.SCI_GETAUTOCASESENSITIVE):
        return 1 if editor._auto_case_sensitive else 0
    if msg == int(editor.SCI_SETAUTOMAXHEIGHT):
        editor._auto_max_height = max(1, int(args[0]) if args else 1)
        return int(editor._auto_max_height)
    if msg == int(editor.SCI_GETAUTOMAXHEIGHT):
        return int(editor._auto_max_height)
    if msg == int(editor.SCI_SETAUTOMAXWIDTH):
        editor._auto_max_width = max(0, int(args[0]) if args else 0)
        return int(editor._auto_max_width)
    if msg == int(editor.SCI_GETAUTOMAXWIDTH):
        return int(editor._auto_max_width)
    if msg == int(editor.SCI_SETAUTODROPRESTOFWORD):
        editor._auto_drop_rest_of_word = bool(int(args[0])) if args else False
        return 1 if editor._auto_drop_rest_of_word else 0
    if msg == int(editor.SCI_GETAUTODROPRESTOFWORD):
        return 1 if editor._auto_drop_rest_of_word else 0
    if msg == int(editor.SCI_SETAUTOHIDE):
        editor._auto_hide = bool(int(args[0])) if args else False
        return 1 if editor._auto_hide else 0
    if msg == int(editor.SCI_GETAUTOHIDE):
        return 1 if editor._auto_hide else 0
    if msg == int(editor.SCI_SETAUTOCANCELATSTART):
        editor._auto_cancel_at_start = bool(int(args[0])) if args else False
        return 1 if editor._auto_cancel_at_start else 0
    if msg == int(editor.SCI_GETAUTOCANCELATSTART):
        return 1 if editor._auto_cancel_at_start else 0
    if msg == int(editor.SCI_SETAUTOCURRENT):
        editor._auto_current = max(0, int(args[0]) if args else 0)
        return int(editor._auto_current)
    if msg == int(editor.SCI_GETAUTOCURRENT):
        return int(editor._auto_current)
    if msg == int(editor.SCI_SETCARETLINEFRAME):
        editor._caret_line_frame = max(0, int(args[0]) if args else 0)
        return int(editor._caret_line_frame)
    if msg == int(editor.SCI_GETCARETLINEFRAME):
        return int(editor._caret_line_frame)
    if msg == int(editor.SCI_SETCARETLINEVISIBLEALWAYS):
        editor._caret_line_visible_always = bool(int(args[0])) if args else False
        return 1 if editor._caret_line_visible_always else 0
    if msg == int(editor.SCI_GETCARETLINEVISIBLEALWAYS):
        return 1 if editor._caret_line_visible_always else 0
    if msg == int(editor.SCI_SETHSCROLLBAR):
        editor._h_scrollbar = bool(int(args[0])) if args else False
        return 1 if editor._h_scrollbar else 0
    if msg == int(editor.SCI_GETHSCROLLBAR):
        return 1 if editor._h_scrollbar else 0
    if msg == int(editor.SCI_SETVSCROLLBAR):
        editor._v_scrollbar = bool(int(args[0])) if args else False
        return 1 if editor._v_scrollbar else 0
    if msg == int(editor.SCI_GETVSCROLLBAR):
        return 1 if editor._v_scrollbar else 0
    if msg == int(editor.SCI_SETFOCUS):
        focus = bool(int(args[0])) if args else False
        if focus:
            editor.setFocus()
        else:
            editor.clearFocus()
        return 1 if focus else 0
    return None
