"""Implement selection and undo/redo command handlers for the Scintilla compatibility layer.

This module belongs to the Scintilla compatibility layer used when native QScintilla is unavailable. It helps explain how `pypad.ui.editor.scintilla_compat` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

from PySide6.QtGui import QTextCursor


def handle_selection_undo_command(editor, msg: int, args: tuple[int, ...]) -> int | None:
    """Execute the `handle_selection_undo_command` workflow."""
    if msg == int(editor.SCI_SETSEL):
        if len(args) < 2:
            return 0
        start = max(0, min(int(args[0]), len(editor.toPlainText())))
        end = max(0, min(int(args[1]), len(editor.toPlainText())))
        c = editor.textCursor()
        c.setPosition(start)
        c.setPosition(end, QTextCursor.KeepAnchor)
        editor.setTextCursor(c)
        return 1
    if msg == int(editor.SCI_SETEMPTYSELECTION):
        pos = max(0, min(int(args[0]) if args else 0, len(editor.toPlainText())))
        c = editor.textCursor()
        c.setPosition(pos)
        editor.setTextCursor(c)
        return int(pos)
    if msg == int(editor.SCI_SETREADONLY):
        ro = bool(int(args[0])) if args else False
        editor.setReadOnly(ro)
        return 1 if ro else 0
    if msg == int(editor.SCI_GETREADONLY):
        return 1 if editor.isReadOnly() else 0
    if msg == int(editor.SCI_UNDO):
        return int(editor._undo_from_frames() or 1)
    if msg == int(editor.SCI_REDO):
        return int(editor._redo_from_frames() or 1)
    if msg == int(editor.SCI_CANUNDO):
        if getattr(editor, "_undo_frames", None):
            return 1
        return 1 if editor.isUndoAvailable() else 0
    if msg == int(editor.SCI_CANREDO):
        if getattr(editor, "_redo_frames", None):
            return 1
        return 1 if editor.isRedoAvailable() else 0
    if msg == int(editor.SCI_SETUNDOCOLLECTION):
        editor._undo_collection_enabled = bool(int(args[0])) if args else True
        return 1 if editor._undo_collection_enabled else 0
    if msg == int(editor.SCI_GETUNDOCOLLECTION):
        return 1 if editor._undo_collection_enabled else 0
    if msg == int(editor.SCI_BEGINUNDOACTION):
        editor._begin_undo_action()
        return 1
    if msg == int(editor.SCI_ENDUNDOACTION):
        editor._end_undo_action()
        return 1
    if msg == int(editor.SCI_EMPTYUNDOBUFFER):
        try:
            editor.document().clearUndoRedoStacks()
        except Exception:
            pass
        editor._undo_frames = []
        editor._redo_frames = []
        return 1
    if msg == int(editor.SCI_GETMODIFY):
        return 1 if editor.document().isModified() else 0
    if msg == int(editor.SCI_CLEAR):
        if editor.isReadOnly():
            return 0
        c = editor.textCursor()
        if c.hasSelection():
            c.removeSelectedText()
            editor.setTextCursor(c)
            return 1
        return 0
    if msg == int(editor.SCI_SELECTALL):
        editor.selectAll()
        return 1
    return None
