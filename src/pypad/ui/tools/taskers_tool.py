"""Lightweight local task management tied to notes and workspaces."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDateTimeEdit, QFormLayout, QGroupBox, QHBoxLayout, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget

from .base_dialog import ToolDialogBase


def task_scope_from_window(window) -> tuple[str, str]:
    """Return note/workspace task scope key and label."""
    tab = window.active_tab() if hasattr(window, "active_tab") else None
    if tab is not None and getattr(tab, "current_file", None):
        return str(tab.current_file), "Current note"
    root = str(getattr(window, "settings", {}).get("workspace_root", "") or "").strip()
    if root:
        return f"workspace:{root}", "Workspace"
    return "__general__", "General"


class TaskersToolDialog(ToolDialogBase):
    """Manage local tasks and optionally promote them into reminders."""

    def __init__(self, parent, initial_text: str = "") -> None:
        super().__init__(
            parent,
            tool_id="taskers",
            title="Taskers",
            help_text=(
                "Track lightweight local tasks for the current note or workspace. "
                "Tasks can become reminders and can be inserted into the editor as Markdown checklists."
            ),
            output_label="Task summary",
        )
        self.scope_key, self.scope_label = task_scope_from_window(parent)
        shell = QWidget(self)
        layout = QVBoxLayout(shell)
        self.list_widget = QListWidget(shell)
        self.list_widget.itemChanged.connect(self._persist)
        layout.addWidget(self.list_widget)

        form_box = QGroupBox("Task details", shell)
        form = QFormLayout(form_box)
        self.title_edit = QTextEdit(form_box)
        self.title_edit.setFixedHeight(56)
        self.priority_combo = QComboBox(form_box)
        self.priority_combo.addItems(["Low", "Medium", "High"])
        self.due_edit = QDateTimeEdit(form_box)
        self.due_edit.setCalendarPopup(True)
        self.due_edit.setDateTime(self.due_edit.dateTime().currentDateTime().addDays(1))
        form.addRow("Task:", self.title_edit)
        form.addRow("Priority:", self.priority_combo)
        form.addRow("Due:", self.due_edit)
        layout.addWidget(form_box)

        row = QHBoxLayout()
        self.add_btn = QPushButton("Add", shell)
        self.delete_btn = QPushButton("Delete", shell)
        self.reminder_btn = QPushButton("Create Reminder", shell)
        self.insert_btn.setText("Insert Checklist")
        row.addWidget(self.add_btn)
        row.addWidget(self.delete_btn)
        row.addWidget(self.reminder_btn)
        row.addStretch(1)
        layout.addLayout(row)
        self.add_section(shell)
        self.add_btn.clicked.connect(self.add_task)
        self.delete_btn.clicked.connect(self.delete_task)
        self.reminder_btn.clicked.connect(self.create_reminder)
        self.insert_btn.clicked.disconnect()
        self.insert_btn.clicked.connect(self.insert_checklist)
        self._load_tasks()
        seed = str(initial_text or "").strip()
        if seed:
            self.title_edit.setPlainText(seed)

    def _task_store(self) -> dict[str, list[dict[str, str]]]:
        store = self.window.settings.get("task_lists", {})
        if not isinstance(store, dict):
            store = {}
        return store

    def _load_tasks(self) -> None:
        self.list_widget.clear()
        tasks = self._task_store().get(self.scope_key, [])
        if not isinstance(tasks, list):
            tasks = []
        for task in tasks:
            item = QListWidgetItem(f"[{task.get('priority', 'Medium')}] {task.get('title', 'Untitled')} | {task.get('due', '')}", self.list_widget)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if str(task.get("done", "false")).lower() == "true" else Qt.Unchecked)
            item.setData(Qt.UserRole, dict(task))

    def _persist(self) -> None:
        tasks: list[dict[str, str]] = []
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            payload = dict(item.data(Qt.UserRole) or {})
            payload["done"] = "true" if item.checkState() == Qt.Checked else "false"
            tasks.append(payload)
        store = dict(self._task_store())
        store[self.scope_key] = tasks
        self.window.settings["task_lists"] = store
        saver = getattr(self.window, "save_settings_to_disk", None)
        if callable(saver):
            saver()
        self.output.setPlainText(f"{len(tasks)} tasks stored for {self.scope_label.lower()}.")

    def add_task(self) -> None:
        title = self.title_edit.toPlainText().strip()
        if not title:
            QMessageBox.information(self, self.windowTitle(), "Enter a task first.")
            return
        payload = {
            "title": title,
            "priority": self.priority_combo.currentText(),
            "due": self.due_edit.dateTime().toString(Qt.ISODate),
            "done": "false",
        }
        item = QListWidgetItem(f"[{payload['priority']}] {payload['title']} | {payload['due']}", self.list_widget)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Unchecked)
        item.setData(Qt.UserRole, payload)
        self.title_edit.clear()
        self._persist()

    def delete_task(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            return
        self.list_widget.takeItem(self.list_widget.row(item))
        self._persist()

    def create_reminder(self) -> None:
        item = self.list_widget.currentItem()
        if item is None or not hasattr(self.window, "reminders_store"):
            return
        task = dict(item.data(Qt.UserRole) or {})
        due_iso = str(task.get("due", "") or "").strip()
        try:
            due = datetime.fromisoformat(due_iso)
        except Exception:
            due = datetime.now() + timedelta(hours=1)
        self.window.reminders_store.add(
            title=str(task.get("title", "Task")),
            note_ref=self.scope_key,
            due_dt=due,
            notes=f"Imported from Taskers ({task.get('priority', 'Medium')})",
            recurrence="none",
        )
        self.window.reminders_store.save()
        self.output.setPlainText("Reminder created from selected task.")

    def insert_checklist(self) -> None:
        lines: list[str] = []
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            task = dict(item.data(Qt.UserRole) or {})
            prefix = "x" if item.checkState() == Qt.Checked else " "
            lines.append(f"- [{prefix}] {task.get('title', 'Untitled')} ({task.get('priority', 'Medium')})")
        self.output.setPlainText("\n".join(lines))
        super().insert_output()

    def state(self) -> dict[str, Any]:
        return {"scope_key": self.scope_key}
