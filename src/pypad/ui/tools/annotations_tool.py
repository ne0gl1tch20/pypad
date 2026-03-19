"""Polished annotations and highlights manager for the active note."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QInputDialog, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget

from .base_dialog import ToolDialogBase


def note_key_for_window(window) -> str:
    """Return the settings key for the active note."""
    tab = window.active_tab() if hasattr(window, "active_tab") else None
    if tab is None:
        return "__untitled__"
    return str(getattr(tab, "current_file", "") or "__untitled__")


def apply_annotations_to_editor(tab, notes: dict[str, str]) -> None:
    """Push saved notes into the editor inline-annotation layer when available."""
    widget = getattr(getattr(tab, "text_edit", None), "widget", None)
    if widget is None or not hasattr(widget, "annotationSetText"):
        return
    if hasattr(widget, "annotationClearAll"):
        widget.annotationClearAll()
    for line_text, note in notes.items():
        try:
            widget.annotationSetText(max(0, int(line_text) - 1), str(note))
        except Exception:
            continue


class AnnotationsToolDialog(ToolDialogBase):
    """Review, edit, and jump through note annotations."""

    def __init__(self, parent) -> None:
        super().__init__(
            parent,
            tool_id="annotations_manager",
            title="Highlights + Notes",
            help_text=(
                "Attach notes to lines or the current selection, browse them, jump back into the document, "
                "and keep inline annotations visible in the editor when supported."
            ),
            output_label="Annotation details",
        )
        self.key = note_key_for_window(parent)
        shell = QWidget(self)
        layout = QVBoxLayout(shell)
        self.list_widget = QListWidget(shell)
        self.note_preview = QTextEdit(shell)
        self.note_preview.setReadOnly(True)
        row = QHBoxLayout()
        self.add_selection_btn = QPushButton("Annotate Selection", shell)
        self.add_line_btn = QPushButton("Add Line Note", shell)
        self.edit_btn = QPushButton("Edit", shell)
        self.jump_btn = QPushButton("Jump", shell)
        self.delete_btn = QPushButton("Delete", shell)
        for button in (self.add_selection_btn, self.add_line_btn, self.edit_btn, self.jump_btn, self.delete_btn):
            row.addWidget(button)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.note_preview)
        layout.addLayout(row)
        self.add_section(shell)
        self.add_selection_btn.clicked.connect(self.add_from_selection)
        self.add_line_btn.clicked.connect(self.add_line_note)
        self.edit_btn.clicked.connect(self.edit_current)
        self.jump_btn.clicked.connect(self.jump_to_current)
        self.delete_btn.clicked.connect(self.delete_current)
        self.list_widget.currentItemChanged.connect(self._load_preview)
        self._refresh()

    def _store(self) -> dict[str, dict[str, str]]:
        store = self.window.settings.get("annotations", {})
        return dict(store) if isinstance(store, dict) else {}

    def _note_map(self) -> dict[str, str]:
        notes = self._store().get(self.key, {})
        return dict(notes) if isinstance(notes, dict) else {}

    def _persist(self, notes: dict[str, str]) -> None:
        store = self._store()
        store[self.key] = dict(notes)
        self.window.settings["annotations"] = store
        saver = getattr(self.window, "save_settings_to_disk", None)
        if callable(saver):
            saver()
        tab = self.window.active_tab() if hasattr(self.window, "active_tab") else None
        if tab is not None:
            apply_annotations_to_editor(tab, notes)

    def _refresh(self) -> None:
        self.list_widget.clear()
        notes = self._note_map()
        for line, text in sorted(notes.items(), key=lambda item: int(str(item[0]))):
            item = QListWidgetItem(f"Line {line}: {str(text).splitlines()[0]}", self.list_widget)
            item.setData(Qt.UserRole, {"line": str(line), "text": str(text)})
        self.output.setPlainText(f"{len(notes)} notes for the current document.")

    def _load_preview(self, current, _previous) -> None:
        payload = dict(current.data(Qt.UserRole) or {}) if current is not None else {}
        text = str(payload.get("text", ""))
        self.note_preview.setPlainText(text)
        self.output.setPlainText(text or "Select an annotation.")

    def add_from_selection(self) -> None:
        tab = self.window.active_tab() if hasattr(self.window, "active_tab") else None
        if tab is None:
            return
        line, _ = tab.text_edit.cursor_position()
        seed = tab.text_edit.selected_text().strip()
        text, ok = QInputDialog.getMultiLineText(self, self.windowTitle(), "Note:", seed)
        if ok and text.strip():
            notes = self._note_map()
            notes[str(line + 1)] = text.strip()
            self._persist(notes)
            self._refresh()

    def add_line_note(self) -> None:
        line, ok = QInputDialog.getInt(self, self.windowTitle(), "Line number:", 1, 1, 1_000_000)
        if not ok:
            return
        text, ok = QInputDialog.getMultiLineText(self, self.windowTitle(), "Note:")
        if ok and text.strip():
            notes = self._note_map()
            notes[str(line)] = text.strip()
            self._persist(notes)
            self._refresh()

    def edit_current(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            return
        payload = dict(item.data(Qt.UserRole) or {})
        text, ok = QInputDialog.getMultiLineText(self, self.windowTitle(), "Edit note:", str(payload.get("text", "")))
        if ok and text.strip():
            notes = self._note_map()
            notes[str(payload.get("line", ""))] = text.strip()
            self._persist(notes)
            self._refresh()

    def jump_to_current(self) -> None:
        item = self.list_widget.currentItem()
        tab = self.window.active_tab() if hasattr(self.window, "active_tab") else None
        if item is None or tab is None:
            return
        payload = dict(item.data(Qt.UserRole) or {})
        line = max(0, int(str(payload.get("line", "1"))) - 1)
        tab.text_edit.set_cursor_position(line, 0)
        if hasattr(tab.text_edit.widget, "setFocus"):
            tab.text_edit.widget.setFocus()

    def delete_current(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            return
        payload = dict(item.data(Qt.UserRole) or {})
        notes = self._note_map()
        removed = notes.pop(str(payload.get("line", "")), None)
        if removed is None:
            QMessageBox.information(self, self.windowTitle(), "Nothing to remove.")
            return
        self._persist(notes)
        self._refresh()

    def state(self) -> dict[str, Any]:
        return {"document_key": self.key}
