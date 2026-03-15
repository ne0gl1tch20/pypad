"""Startup recovery dialog for early-launch diagnostics and safe-mode controls."""

from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from pypad.ui.theme.theme_tokens import build_dialog_theme_qss_from_tokens, build_tokens_from_settings


class StartupRecoveryDialog(QDialog):
    """Purpose-built startup diagnostics and recovery controls shown after the splash trigger."""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self._window = parent
        self.setWindowTitle("Startup Recovery / Safe Mode")
        self.resize(1180, 780)
        self.setModal(True)
        self._snapshot_editors: dict[str, QTextEdit] = {}

        tokens = build_tokens_from_settings(getattr(parent, "settings", {}) if parent is not None else {})
        self.setStyleSheet(build_dialog_theme_qss_from_tokens(tokens))

        layout = QVBoxLayout(self)
        self.mode_banner = QLabel(self)
        self.mode_banner.setWordWrap(True)
        self.mode_banner.setObjectName("startupRecoveryBanner")
        layout.addWidget(self.mode_banner)
        self.summary_label = QLabel(self)
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        layout.addWidget(splitter, 1)

        left_host = QWidget(splitter)
        left_layout = QVBoxLayout(left_host)

        status_group = QGroupBox("Startup Status", left_host)
        status_layout = QGridLayout(status_group)
        self.status_safe_mode_value = QLabel(status_group)
        self.status_fast_startup_value = QLabel(status_group)
        self.status_recovery_mode_value = QLabel(status_group)
        self.status_crash_snapshot_value = QLabel(status_group)
        status_layout.addWidget(QLabel("Plugin safe mode", status_group), 0, 0)
        status_layout.addWidget(self.status_safe_mode_value, 0, 1)
        status_layout.addWidget(QLabel("Fast startup", status_group), 1, 0)
        status_layout.addWidget(self.status_fast_startup_value, 1, 1)
        status_layout.addWidget(QLabel("Recovery mode", status_group), 2, 0)
        status_layout.addWidget(self.status_recovery_mode_value, 2, 1)
        status_layout.addWidget(QLabel("Crash snapshots", status_group), 3, 0)
        status_layout.addWidget(self.status_crash_snapshot_value, 3, 1)
        left_layout.addWidget(status_group)

        controls_group = QGroupBox("Startup Controls", left_host)
        controls_layout = QFormLayout(controls_group)
        self.plugin_safe_mode_checkbox = QCheckBox("Skip plugin loading during startup", controls_group)
        self.fast_startup_checkbox = QCheckBox("Use fast startup mode", controls_group)
        self.crash_snapshot_checkbox = QCheckBox("Persist crash snapshots", controls_group)
        self.recovery_mode_combo = QComboBox(controls_group)
        self.recovery_mode_combo.addItems(["ask", "auto_restore", "auto_discard"])
        controls_layout.addRow("Plugin startup safe mode", self.plugin_safe_mode_checkbox)
        controls_layout.addRow("Fast startup mode", self.fast_startup_checkbox)
        controls_layout.addRow("Crash snapshot capture", self.crash_snapshot_checkbox)
        controls_layout.addRow("Recovery mode", self.recovery_mode_combo)
        left_layout.addWidget(controls_group)

        actions_group = QGroupBox("Recovery Actions", left_host)
        actions_layout = QGridLayout(actions_group)
        self.apply_btn = QPushButton("Apply Startup Settings", actions_group)
        self.retry_recovery_btn = QPushButton("Retry Recovery Check", actions_group)
        self.clear_snapshot_btn = QPushButton("Clear Crash Snapshot", actions_group)
        self.restart_safe_mode_btn = QPushButton("Restart In Safe Mode", actions_group)
        self.restart_normal_btn = QPushButton("Restart Normally", actions_group)
        self.open_debug_log_btn = QPushButton("Open Debug Log", actions_group)
        self.open_crash_log_btn = QPushButton("Open Crash Log", actions_group)
        self.export_btn = QPushButton("Export Diagnostics Bundle", actions_group)
        self.developer_hub_btn = QPushButton("Open Developer Hub", actions_group)
        action_buttons = [
            self.apply_btn,
            self.retry_recovery_btn,
            self.clear_snapshot_btn,
            self.restart_safe_mode_btn,
            self.restart_normal_btn,
            self.open_debug_log_btn,
            self.open_crash_log_btn,
            self.export_btn,
            self.developer_hub_btn,
        ]
        for index, button in enumerate(action_buttons):
            row = index // 2
            col = index % 2
            actions_layout.addWidget(button, row, col)
        left_layout.addWidget(actions_group)
        left_layout.addStretch(1)

        right_host = QWidget(splitter)
        right_layout = QVBoxLayout(right_host)

        self._build_snapshot_editor(right_layout, "Startup State")
        self._build_snapshot_editor(right_layout, "Recovery State")
        self._build_snapshot_editor(right_layout, "Recent Startup Logs")
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, Qt.Horizontal, self)
        self.copy_btn = QPushButton("Copy Summary", self)
        buttons.addButton(self.copy_btn, QDialogButtonBox.ActionRole)
        buttons.rejected.connect(self.close)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.apply_btn.clicked.connect(self._apply_settings)
        self.retry_recovery_btn.clicked.connect(self._retry_recovery)
        self.clear_snapshot_btn.clicked.connect(self._clear_crash_snapshot)
        self.restart_safe_mode_btn.clicked.connect(self._restart_in_safe_mode)
        self.restart_normal_btn.clicked.connect(self._restart_normally)
        self.open_debug_log_btn.clicked.connect(lambda: self._open_path(getattr(self._window, "_get_debug_logs_file_path")()))
        self.open_crash_log_btn.clicked.connect(lambda: self._open_path(getattr(self._window, "_get_crash_logs_file_path")()))
        self.export_btn.clicked.connect(self._export_diagnostics)
        self.developer_hub_btn.clicked.connect(lambda: getattr(self._window, "open_developer_hub")("Startup", force=True))
        self.copy_btn.clicked.connect(self._copy_summary)

        self.refresh()

    def _build_snapshot_editor(self, layout: QVBoxLayout, title: str) -> None:
        """Add one read-only diagnostics pane."""
        label = QLabel(title, self)
        editor = QTextEdit(self)
        editor.setReadOnly(True)
        editor.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(label)
        layout.addWidget(editor, 1)
        self._snapshot_editors[title] = editor

    def refresh(self) -> None:
        """Refresh the visible recovery and startup state."""
        startup = dict(getattr(self._window, "build_startup_state_snapshot", lambda: {})())
        recovery = dict(getattr(self._window, "build_recovery_state_snapshot", lambda: {})())
        safe_mode = bool(self._window.settings.get("plugin_startup_safe_mode", False))
        fast_startup = bool(self._window.settings.get("fast_startup_mode", True))
        crash_snapshots = bool(self._window.settings.get("crash_snapshot_enabled", True))
        recovery_mode = str(self._window.settings.get("recovery_mode", "ask") or "ask")
        self.plugin_safe_mode_checkbox.setChecked(safe_mode)
        self.fast_startup_checkbox.setChecked(fast_startup)
        self.crash_snapshot_checkbox.setChecked(crash_snapshots)
        self.recovery_mode_combo.setCurrentText(recovery_mode)
        self.status_safe_mode_value.setText("ON" if safe_mode else "OFF")
        self.status_fast_startup_value.setText("ON" if fast_startup else "OFF")
        self.status_recovery_mode_value.setText(recovery_mode)
        self.status_crash_snapshot_value.setText("ON" if crash_snapshots else "OFF")
        startup_lines = list(startup.get("startup_log_lines", []) or [])
        self._snapshot_editors["Startup State"].setPlainText(json.dumps(startup, indent=2, sort_keys=True, ensure_ascii=False))
        self._snapshot_editors["Recovery State"].setPlainText(json.dumps(recovery, indent=2, sort_keys=True, ensure_ascii=False))
        self._snapshot_editors["Recent Startup Logs"].setPlainText("\n".join(startup_lines[-120:]))
        self.mode_banner.setText(
            "Startup safe mode is currently ON. Plugin loading will be skipped on relaunch."
            if safe_mode
            else "Startup safe mode is currently OFF. Normal plugin startup behavior is enabled."
        )
        self.summary_label.setText(
            "This startup dashboard keeps the main editor hidden while you inspect recovery state, "
            "switch startup behavior, and decide whether to relaunch normally or in safe mode."
        )

    def _apply_settings(self) -> None:
        """Persist startup-focused recovery settings immediately."""
        self._window.settings["plugin_startup_safe_mode"] = self.plugin_safe_mode_checkbox.isChecked()
        self._window.settings["fast_startup_mode"] = self.fast_startup_checkbox.isChecked()
        self._window.settings["crash_snapshot_enabled"] = self.crash_snapshot_checkbox.isChecked()
        self._window.settings["recovery_mode"] = self.recovery_mode_combo.currentText()
        if hasattr(self._window, "save_settings_to_disk"):
            self._window.save_settings_to_disk()
        self._window.show_status_message("Startup recovery settings saved.", 3200)
        self.refresh()

    def _retry_recovery(self) -> None:
        """Re-run crash-recovery offer logic using the current settings."""
        try:
            getattr(self._window, "_offer_crash_recovery")()
        except Exception as exc:
            QMessageBox.warning(self, "Startup Recovery", f"Could not retry recovery:\n{exc}")
            return
        self._window.show_status_message("Recovery check retried.", 3200)
        self.refresh()

    def _clear_crash_snapshot(self) -> None:
        """Delete any persisted crash snapshot so the next launch starts cleanly."""
        store = getattr(self._window, "recovery_state_store", None)
        if store is None or not hasattr(store, "clear_crash_snapshot"):
            QMessageBox.information(self, "Startup Recovery", "Crash snapshot storage is not available.")
            return
        try:
            store.clear_crash_snapshot()
        except Exception as exc:
            QMessageBox.warning(self, "Startup Recovery", f"Could not clear crash snapshot:\n{exc}")
            return
        self._window.show_status_message("Crash snapshot cleared.", 3200)
        self.refresh()

    def _export_diagnostics(self) -> None:
        """Delegate diagnostics bundle export to the existing advanced-features path."""
        try:
            getattr(self._window, "export_diagnostics_bundle")()
        except Exception as exc:
            QMessageBox.warning(self, "Startup Recovery", f"Could not export diagnostics bundle:\n{exc}")

    def _restart_in_safe_mode(self) -> None:
        """Persist safe-mode startup settings and relaunch the app."""
        answer = QMessageBox.question(
            self,
            "Restart In Safe Mode",
            "Restart the app now with plugin startup safe mode enabled?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            getattr(self._window, "restart_in_startup_safe_mode")()
        except Exception as exc:
            QMessageBox.warning(self, "Startup Recovery", f"Could not restart in safe mode:\n{exc}")

    def _restart_normally(self) -> None:
        """Clear startup safe mode and relaunch the app."""
        answer = QMessageBox.question(
            self,
            "Restart Normally",
            "Restart the app now with plugin startup safe mode disabled?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            getattr(self._window, "restart_normally_from_safe_mode")()
        except Exception as exc:
            QMessageBox.warning(self, "Startup Recovery", f"Could not restart normally:\n{exc}")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Treat closing the startup dashboard as an app-exit decision."""
        super().closeEvent(event)
        if not event.isAccepted():
            return
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _copy_summary(self) -> None:
        """Copy the current startup and recovery state to the clipboard."""
        text = "\n\n".join(
            [
                "Startup State",
                self._snapshot_editors["Startup State"].toPlainText(),
                "Recovery State",
                self._snapshot_editors["Recovery State"].toPlainText(),
            ]
        )
        QApplication.clipboard().setText(text)

    def _open_path(self, path: Path) -> None:
        """Open an existing local path using the platform shell."""
        target = Path(path)
        if not target.exists():
            QMessageBox.information(self, "Open Path", f"Path not found:\n{target}")
            return
        try:
            os.startfile(str(target))  # type: ignore[attr-defined]
        except Exception as exc:
            QMessageBox.warning(self, "Open Path", f"Could not open path:\n{exc}")
