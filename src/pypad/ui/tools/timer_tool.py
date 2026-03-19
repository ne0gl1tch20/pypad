"""Productivity timer and stopwatch dialog."""

from __future__ import annotations

import time
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFormLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton, QSpinBox

from .base_dialog import ToolDialogBase


def format_seconds(seconds: int) -> str:
    """Format seconds as HH:MM:SS."""
    total = max(0, int(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class TimerToolDialog(ToolDialogBase):
    """Local countdown timer and stopwatch."""

    def __init__(self, parent) -> None:
        super().__init__(
            parent,
            tool_id="timer_stopwatch",
            title="Timer / Stopwatch",
            help_text="Run a local countdown or stopwatch. Presets are for productivity timing and stay fully offline.",
        )
        group = QGroupBox("Session", self)
        form = QFormLayout(group)
        self.minutes_spin = QSpinBox(group)
        self.minutes_spin.setRange(1, 240)
        self.minutes_spin.setValue(25)
        self.display = QLabel("00:00:00", group)
        self.mode_label = QLabel("Mode: idle", group)
        row = QHBoxLayout()
        self.start_timer_btn = QPushButton("Start Timer", group)
        self.start_stopwatch_btn = QPushButton("Start Stopwatch", group)
        self.stop_btn = QPushButton("Stop", group)
        self.reset_btn = QPushButton("Reset", group)
        self.pomodoro_btn = QPushButton("Pomodoro 25m", group)
        self.start_timer_btn.clicked.connect(self.start_timer)
        self.start_stopwatch_btn.clicked.connect(self.start_stopwatch)
        self.stop_btn.clicked.connect(self.stop)
        self.reset_btn.clicked.connect(self.reset)
        self.pomodoro_btn.clicked.connect(self._apply_pomodoro)
        for btn in (self.start_timer_btn, self.start_stopwatch_btn, self.stop_btn, self.reset_btn, self.pomodoro_btn):
            row.addWidget(btn)
        form.addRow("Minutes:", self.minutes_spin)
        form.addRow("Clock:", self.display)
        form.addRow("State:", self.mode_label)
        form.addRow(row)
        self.add_section(group)

        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._tick)
        self._mode = "idle"
        self._started_at = 0.0
        self._elapsed_before_pause = 0.0
        self._target_seconds = 0
        self.load_persisted_state()

    def _apply_pomodoro(self) -> None:
        self.minutes_spin.setValue(25)

    def start_timer(self) -> None:
        self._mode = "timer"
        self._started_at = time.monotonic()
        self._elapsed_before_pause = 0.0
        self._target_seconds = int(self.minutes_spin.value()) * 60
        self._timer.start()
        self.mode_label.setText("Mode: countdown")
        self._tick()

    def start_stopwatch(self) -> None:
        self._mode = "stopwatch"
        self._started_at = time.monotonic()
        self._elapsed_before_pause = 0.0
        self._timer.start()
        self.mode_label.setText("Mode: stopwatch")
        self._tick()

    def stop(self) -> None:
        if self._mode == "idle":
            return
        self._elapsed_before_pause = self._elapsed_seconds()
        self._timer.stop()
        self.mode_label.setText(f"Mode: paused {self._mode}")

    def reset(self) -> None:
        self._mode = "idle"
        self._started_at = 0.0
        self._elapsed_before_pause = 0.0
        self._target_seconds = 0
        self._timer.stop()
        self.display.setText("00:00:00")
        self.mode_label.setText("Mode: idle")
        self.output.clear()

    def _elapsed_seconds(self) -> int:
        if self._started_at <= 0:
            return int(self._elapsed_before_pause)
        return int(self._elapsed_before_pause + (time.monotonic() - self._started_at))

    def _tick(self) -> None:
        elapsed = self._elapsed_seconds()
        if self._mode == "stopwatch":
            self.display.setText(format_seconds(elapsed))
            self.output.setPlainText(f"Stopwatch: {self.display.text()}")
            return
        if self._mode == "timer":
            remaining = max(0, self._target_seconds - elapsed)
            self.display.setText(format_seconds(remaining))
            self.output.setPlainText(f"Timer remaining: {self.display.text()}")
            if remaining <= 0:
                self._timer.stop()
                self.mode_label.setText("Mode: countdown complete")
                if hasattr(self.window, "show_status_message"):
                    self.window.show_status_message("Timer complete.", 3000)

    def state(self) -> dict[str, Any]:
        return {"minutes": self.minutes_spin.value()}

    def restore_state(self, state: dict[str, Any]) -> None:
        self.minutes_spin.setValue(max(1, min(240, int(state.get("minutes", 25)))))
