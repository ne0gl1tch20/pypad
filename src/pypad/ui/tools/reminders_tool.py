"""Reminder launcher and status view integrated into built-in tools."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from .base_dialog import ToolDialogBase


def summarize_reminders(store) -> str:
    """Summarize reminder state for status UI."""
    reminders = list(getattr(store, "reminders", [])) if store is not None else []
    total = len(reminders)
    overdue = sum(1 for reminder in reminders if not reminder.fired and reminder.due_datetime <= datetime.now())
    recurring = sum(1 for reminder in reminders if str(reminder.recurrence) != "none")
    return f"{total} reminders\n{overdue} overdue\n{recurring} recurring"


class RemindersToolDialog(ToolDialogBase):
    """Surface reminder status and launch the richer reminder editor."""

    def __init__(self, parent) -> None:
        super().__init__(
            parent,
            tool_id="reminders_hub",
            title="Reminders",
            help_text=(
                "Review reminder status, then open the full reminder editor. "
                "This reuses PyPad's existing reminder store and note linking."
            ),
            output_label="Reminder status",
        )
        self.insert_btn.setVisible(False)
        self.copy_btn.setVisible(False)
        self.save_btn.setVisible(False)
        shell = QWidget(self)
        layout = QVBoxLayout(shell)
        self.summary_label = QLabel(shell)
        self.summary_label.setWordWrap(True)
        self.open_btn = QPushButton("Open Reminder Manager", shell)
        self.refresh_btn = QPushButton("Refresh Status", shell)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.open_btn)
        layout.addWidget(self.refresh_btn)
        layout.addStretch(1)
        self.add_section(shell)
        self.open_btn.clicked.connect(self.open_manager)
        self.refresh_btn.clicked.connect(self.refresh_summary)
        self.refresh_summary()

    def refresh_summary(self) -> None:
        summary = summarize_reminders(getattr(self.window, "reminders_store", None))
        self.summary_label.setText(summary.replace("\n", " | "))
        self.output.setPlainText(summary)

    def open_manager(self) -> None:
        if hasattr(self.window, "show_reminders"):
            self.window.show_reminders()
            self.refresh_summary()
