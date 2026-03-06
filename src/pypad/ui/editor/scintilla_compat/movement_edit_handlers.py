from __future__ import annotations

from PySide6.QtGui import QTextCursor


def handle_movement_edit_command(editor, msg: int, args: tuple[int, ...]) -> int | None:
    if msg == int(editor.SCI_GETCURLINE):
        cur = editor.textCursor()
        block = cur.block()
        line_text = block.text() if block.isValid() else ""
        payload = line_text + "\n"
        if len(args) >= 2:
            max_len = max(0, int(args[0]))
            clipped = payload[: max(0, max_len - 1)] if max_len else ""
            editor._write_scintilla_text_target(args[1], clipped, max_len=max_len)
            return len(clipped)
        return len(payload)
    if msg == int(editor.SCI_GOTOLINE):
        line = max(0, int(args[0]) if args else 0)
        pos = editor._index_from_line_col(line, 0)
        c = editor.textCursor()
        c.setPosition(pos)
        editor.setTextCursor(c)
        return int(pos)
    if msg == int(editor.SCI_GOTOPOS):
        pos = max(0, min(int(args[0]) if args else 0, len(editor.toPlainText())))
        c = editor.textCursor()
        c.setPosition(pos)
        editor.setTextCursor(c)
        return int(pos)
    if msg == int(editor.SCI_CHARLEFT):
        c = editor.textCursor()
        c.movePosition(QTextCursor.Left)
        editor.setTextCursor(c)
        return int(c.position())
    if msg == int(editor.SCI_CHARRIGHT):
        c = editor.textCursor()
        c.movePosition(QTextCursor.Right)
        editor.setTextCursor(c)
        return int(c.position())
    if msg == int(editor.SCI_LINEUP):
        c = editor.textCursor()
        c.movePosition(QTextCursor.Up)
        editor.setTextCursor(c)
        return int(c.position())
    if msg == int(editor.SCI_LINEDOWN):
        c = editor.textCursor()
        c.movePosition(QTextCursor.Down)
        editor.setTextCursor(c)
        return int(c.position())
    if msg == int(editor.SCI_PAGEUP):
        return int(editor._page_move(up=True, extend=False))
    if msg == int(editor.SCI_PAGEDOWN):
        return int(editor._page_move(up=False, extend=False))
    if msg == int(editor.SCI_PAGEUPEXTEND):
        return int(editor._page_move(up=True, extend=True))
    if msg == int(editor.SCI_PAGEDOWNEXTEND):
        return int(editor._page_move(up=False, extend=True))
    if msg == int(editor.SCI_CHARLEFTEXTEND):
        c = editor.textCursor()
        c.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)
        editor.setTextCursor(c)
        return int(c.position())
    if msg == int(editor.SCI_CHARRIGHTEXTEND):
        c = editor.textCursor()
        c.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
        editor.setTextCursor(c)
        return int(c.position())
    if msg == int(editor.SCI_LINEUPEXTEND):
        c = editor.textCursor()
        c.movePosition(QTextCursor.Up, QTextCursor.KeepAnchor)
        editor.setTextCursor(c)
        return int(c.position())
    if msg == int(editor.SCI_LINEDOWNEXTEND):
        c = editor.textCursor()
        c.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor)
        editor.setTextCursor(c)
        return int(c.position())
    if msg == int(editor.SCI_HOMEEXTEND):
        c = editor.textCursor()
        c.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
        editor.setTextCursor(c)
        return int(c.position())
    if msg == int(editor.SCI_HOMEWRAP):
        return int(editor.SendScintilla(editor.SCI_HOME))
    if msg == int(editor.SCI_HOMEWRAPEXTEND):
        return int(editor.SendScintilla(editor.SCI_HOMEEXTEND))
    if msg == int(editor.SCI_END):
        c = editor.textCursor()
        c.movePosition(QTextCursor.EndOfLine)
        editor.setTextCursor(c)
        return int(c.position())
    if msg == int(editor.SCI_ENDEXTEND):
        c = editor.textCursor()
        c.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        editor.setTextCursor(c)
        return int(c.position())
    if msg == int(editor.SCI_LINEENDWRAP):
        return int(editor.SendScintilla(editor.SCI_END))
    if msg == int(editor.SCI_LINEENDWRAPEXTEND):
        return int(editor.SendScintilla(editor.SCI_ENDEXTEND))
    if msg == int(editor.SCI_WORDLEFT):
        c = editor.textCursor()
        pos = editor._word_start_position(c.position(), only_word_chars=True)
        c.setPosition(pos)
        editor.setTextCursor(c)
        return int(pos)
    if msg == int(editor.SCI_WORDRIGHT):
        c = editor.textCursor()
        pos = editor._word_end_position(c.position(), only_word_chars=True)
        c.setPosition(pos)
        editor.setTextCursor(c)
        return int(pos)
    if msg == int(editor.SCI_WORDLEFTEXTEND):
        c = editor.textCursor()
        pos = editor._word_start_position(c.position(), only_word_chars=True)
        c.setPosition(pos, QTextCursor.KeepAnchor)
        editor.setTextCursor(c)
        return int(pos)
    if msg == int(editor.SCI_WORDRIGHTEXTEND):
        c = editor.textCursor()
        pos = editor._word_end_position(c.position(), only_word_chars=True)
        c.setPosition(pos, QTextCursor.KeepAnchor)
        editor.setTextCursor(c)
        return int(pos)
    if msg == int(editor.SCI_DOCUMENTSTART):
        c = editor.textCursor()
        c.setPosition(0)
        editor.setTextCursor(c)
        return 0
    if msg == int(editor.SCI_DOCUMENTSTARTEXTEND):
        c = editor.textCursor()
        c.setPosition(0, QTextCursor.KeepAnchor)
        editor.setTextCursor(c)
        return 0
    if msg == int(editor.SCI_DOCUMENTEND):
        end = len(editor.toPlainText())
        c = editor.textCursor()
        c.setPosition(end)
        editor.setTextCursor(c)
        return int(end)
    if msg == int(editor.SCI_DOCUMENTENDEXTEND):
        end = len(editor.toPlainText())
        c = editor.textCursor()
        c.setPosition(end, QTextCursor.KeepAnchor)
        editor.setTextCursor(c)
        return int(end)
    if msg == int(editor.SCI_VCHOME):
        c = editor.textCursor()
        block = c.block()
        if block.isValid():
            text = block.text()
            first_non_ws = 0
            while first_non_ws < len(text) and text[first_non_ws] in {" ", "\t"}:
                first_non_ws += 1
            pos = block.position() + first_non_ws
        else:
            pos = 0
        c.setPosition(pos)
        editor.setTextCursor(c)
        return int(pos)
    if msg == int(editor.SCI_VCHOMEWRAP):
        return int(editor.SendScintilla(editor.SCI_VCHOME))
    if msg == int(editor.SCI_VCHOMEWRAPEXTEND):
        target = int(editor.SendScintilla(editor.SCI_VCHOME))
        c = editor.textCursor()
        c.setPosition(target, QTextCursor.KeepAnchor)
        editor.setTextCursor(c)
        return int(target)
    if msg == int(editor.SCI_HOME):
        c = editor.textCursor()
        block = c.block()
        pos = block.position() if block.isValid() else 0
        c.setPosition(pos)
        editor.setTextCursor(c)
        return int(pos)
    if msg == int(editor.SCI_LINEEND):
        c = editor.textCursor()
        block = c.block()
        pos = (block.position() + len(block.text())) if block.isValid() else len(editor.toPlainText())
        c.setPosition(pos)
        editor.setTextCursor(c)
        return int(pos)
    if msg == int(editor.SCI_DELETEBACK):
        if editor.isReadOnly():
            return 0
        c = editor.textCursor()
        if c.hasSelection():
            c.removeSelectedText()
        else:
            c.deletePreviousChar()
        editor.setTextCursor(c)
        return 1
    if msg == int(editor.SCI_DELLINELEFT):
        if editor.isReadOnly():
            return 0
        c = editor.textCursor()
        block = c.block()
        if block.isValid():
            c.setPosition(block.position(), QTextCursor.KeepAnchor)
            c.removeSelectedText()
            editor.setTextCursor(c)
        return 1
    if msg == int(editor.SCI_DELLINERIGHT):
        if editor.isReadOnly():
            return 0
        c = editor.textCursor()
        block = c.block()
        if block.isValid():
            end = block.position() + len(block.text())
            c.setPosition(end, QTextCursor.KeepAnchor)
            c.removeSelectedText()
            editor.setTextCursor(c)
        return 1
    if msg == int(editor.SCI_LINECUT):
        if editor.isReadOnly():
            return 0
        c = editor.textCursor()
        block = c.block()
        if block.isValid():
            start = block.position()
            end = start + len(block.text())
            text = editor.toPlainText()
            if end < len(text) and text[end] == "\n":
                end += 1
            c.setPosition(start)
            c.setPosition(end, QTextCursor.KeepAnchor)
            c.removeSelectedText()
            editor.setTextCursor(c)
        return 1
    if msg == int(editor.SCI_LINEDELETE):
        if editor.isReadOnly():
            return 0
        c = editor.textCursor()
        block = c.block()
        if block.isValid():
            start = block.position()
            end = start + len(block.text())
            text = editor.toPlainText()
            if end < len(text) and text[end] == "\n":
                end += 1
            c.setPosition(start)
            c.setPosition(end, QTextCursor.KeepAnchor)
            c.removeSelectedText()
            editor.setTextCursor(c)
        return 1
    if msg == int(editor.SCI_LINETRANSPOSE):
        if editor.isReadOnly():
            return 0
        lines = editor.toPlainText().split("\n")
        c = editor.textCursor()
        line = c.blockNumber()
        if line <= 0 or line >= len(lines):
            return 0
        lines[line - 1], lines[line] = lines[line], lines[line - 1]
        new_text = "\n".join(lines)
        editor.setPlainText(new_text)
        c = editor.textCursor()
        c.setPosition(editor._index_from_line_col(max(0, line - 1), 0))
        editor.setTextCursor(c)
        return 1
    return None
