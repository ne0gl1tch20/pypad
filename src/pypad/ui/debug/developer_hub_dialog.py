"""Developer diagnostics hub for inspecting runtime state and internal app telemetry."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from pypad.ui.theme.theme_tokens import build_dialog_theme_qss_from_tokens, build_tokens_from_settings


class DeveloperHubDialog(QDialog):
    """Multi-tab diagnostics workspace shown when developer mode is enabled."""

    TAB_ORDER = [
        "Overview",
        "AI",
        "Logs",
        "Runtime",
        "Settings",
        "Startup",
        "Layout",
        "Updater",
        "Plugins",
        "Recovery",
    ]

    def __init__(self, parent, *, initial_tab: str | None = None) -> None:
        """Build the developer hub and populate its tab content."""
        super().__init__(parent)
        self._window = parent
        self.setWindowTitle("Developer Hub")
        self.resize(1180, 800)
        self._tab_editors: dict[str, QTextEdit] = {}
        self._tab_copy_mode: dict[str, str] = {}

        tokens = build_tokens_from_settings(getattr(parent, "settings", {}) if parent is not None else {})
        self.setStyleSheet(build_dialog_theme_qss_from_tokens(tokens))

        layout = QVBoxLayout(self)
        self.summary_label = QLabel("Developer diagnostics", self)
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs, 1)

        self._build_overview_tab()
        self._build_ai_tab()
        self._build_logs_tab()
        self._build_text_tab("Runtime")
        self._build_text_tab("Settings")
        self._build_text_tab("Startup")
        self._build_text_tab("Layout")
        self._build_text_tab("Updater")
        self._build_text_tab("Plugins")
        self._build_text_tab("Recovery")

        buttons = QDialogButtonBox(QDialogButtonBox.Close, Qt.Horizontal, self)
        self.refresh_btn = QPushButton("Refresh", self)
        self.copy_btn = QPushButton("Copy Current Tab", self)
        self.export_btn = QPushButton("Export Snapshot", self)
        buttons.addButton(self.refresh_btn, QDialogButtonBox.ActionRole)
        buttons.addButton(self.copy_btn, QDialogButtonBox.ActionRole)
        buttons.addButton(self.export_btn, QDialogButtonBox.ActionRole)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.refresh_btn.clicked.connect(self.refresh)
        self.copy_btn.clicked.connect(self.copy_current_tab)
        self.export_btn.clicked.connect(self.export_snapshot)
        self.tabs.currentChanged.connect(lambda _idx: self._update_summary())

        self.refresh()
        if initial_tab:
            self.focus_tab(initial_tab)

    def _build_text_tab(self, name: str) -> None:
        """Add a plain text diagnostics tab."""
        host = QWidget(self)
        host_layout = QVBoxLayout(host)
        editor = QTextEdit(host)
        editor.setReadOnly(True)
        editor.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        host_layout.addWidget(editor, 1)
        self.tabs.addTab(host, name)
        self._tab_editors[name] = editor
        self._tab_copy_mode[name] = "text"

    def _build_overview_tab(self) -> None:
        """Build the overview summary tab."""
        self._build_text_tab("Overview")

    def _build_logs_tab(self) -> None:
        """Build the log viewer tab with simple filtering controls."""
        host = QWidget(self)
        layout = QVBoxLayout(host)
        controls = QHBoxLayout()
        self.logs_level_combo = QComboBox(host)
        self.logs_level_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.logs_category_combo = QComboBox(host)
        self.logs_category_combo.addItems(["All", "Startup", "AI", "Updater", "Layout", "Security", "Plugins", "Terminal", "General"])
        self.logs_search_edit = QTextEdit(host)
        self.logs_search_edit.setMaximumHeight(34)
        self.logs_search_edit.setPlaceholderText("Search logs...")
        open_log_btn = QPushButton("Open Log File", host)
        open_crash_btn = QPushButton("Open Crash Log File", host)
        clear_view_btn = QPushButton("Clear View", host)
        controls.addWidget(QLabel("Level", host))
        controls.addWidget(self.logs_level_combo)
        controls.addWidget(QLabel("Category", host))
        controls.addWidget(self.logs_category_combo)
        controls.addWidget(self.logs_search_edit, 1)
        controls.addWidget(open_log_btn)
        controls.addWidget(open_crash_btn)
        controls.addWidget(clear_view_btn)
        layout.addLayout(controls)
        editor = QTextEdit(host)
        editor.setReadOnly(True)
        editor.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(editor, 1)
        self.tabs.addTab(host, "Logs")
        self._tab_editors["Logs"] = editor
        self._tab_copy_mode["Logs"] = "text"
        self.logs_level_combo.currentTextChanged.connect(lambda _v: self._refresh_logs())
        self.logs_category_combo.currentTextChanged.connect(lambda _v: self._refresh_logs())
        self.logs_search_edit.textChanged.connect(self._refresh_logs)
        clear_view_btn.clicked.connect(lambda: editor.clear())
        open_log_btn.clicked.connect(lambda: self._open_path(getattr(self._window, "_get_debug_logs_file_path")()))
        open_crash_btn.clicked.connect(lambda: self._open_path(getattr(self._window, "_get_crash_logs_file_path")()))

    def _build_ai_tab(self) -> None:
        """Build the AI payload inspection tab."""
        host = QWidget(self)
        layout = QVBoxLayout(host)
        summary = QLabel("Inspect the latest and recent AI payloads.", host)
        summary.setWordWrap(True)
        layout.addWidget(summary)
        splitter = QSplitter(Qt.Horizontal, host)
        self.ai_history_list = QListWidget(splitter)
        self.ai_history_list.setMinimumWidth(250)
        right = QWidget(splitter)
        right_layout = QVBoxLayout(right)
        self.ai_meta_view = QTextEdit(right)
        self.ai_meta_view.setReadOnly(True)
        self.ai_meta_view.setMaximumHeight(170)
        self.ai_payload_tabs = QTabWidget(right)
        self.ai_input_edit = QTextEdit(right)
        self.ai_input_edit.setReadOnly(True)
        self.ai_assembled_edit = QTextEdit(right)
        self.ai_assembled_edit.setReadOnly(True)
        self.ai_sent_edit = QTextEdit(right)
        self.ai_sent_edit.setReadOnly(True)
        self.ai_payload_tabs.addTab(self.ai_input_edit, "Input")
        self.ai_payload_tabs.addTab(self.ai_assembled_edit, "Assembled")
        self.ai_payload_tabs.addTab(self.ai_sent_edit, "Sent")
        right_layout.addWidget(self.ai_meta_view)
        right_layout.addWidget(self.ai_payload_tabs, 1)
        splitter.addWidget(self.ai_history_list)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)
        actions = QHBoxLayout()
        open_btn = QPushButton("Open Last Payload", host)
        copy_sent_btn = QPushButton("Copy Sent Prompt", host)
        copy_assembled_btn = QPushButton("Copy Assembled Prompt", host)
        copy_meta_btn = QPushButton("Copy Request Metadata", host)
        actions.addWidget(open_btn)
        actions.addWidget(copy_sent_btn)
        actions.addWidget(copy_assembled_btn)
        actions.addWidget(copy_meta_btn)
        actions.addStretch(1)
        layout.addLayout(actions)
        self.tabs.addTab(host, "AI")
        self._tab_copy_mode["AI"] = "ai_meta"
        self.ai_history_list.currentRowChanged.connect(self._refresh_ai_selection)
        open_btn.clicked.connect(lambda: self.ai_history_list.setCurrentRow(0) if self.ai_history_list.count() else None)
        copy_sent_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.ai_sent_edit.toPlainText()))
        copy_assembled_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.ai_assembled_edit.toPlainText()))
        copy_meta_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.ai_meta_view.toPlainText()))

    def focus_tab(self, name: str) -> None:
        """Focus one tab by name if it exists."""
        for idx in range(self.tabs.count()):
            if self.tabs.tabText(idx).lower() == str(name or "").strip().lower():
                self.tabs.setCurrentIndex(idx)
                return

    def refresh(self) -> None:
        """Refresh all diagnostics tabs from current window state."""
        builders = {
            "Overview": getattr(self._window, "build_developer_overview_snapshot", None),
            "Runtime": getattr(self._window, "build_runtime_state_snapshot", None),
            "Settings": getattr(self._window, "build_settings_resolution_snapshot", None),
            "Startup": getattr(self._window, "build_startup_state_snapshot", None),
            "Layout": getattr(self._window, "build_layout_state_snapshot", None),
            "Updater": getattr(self._window, "build_updater_state_snapshot", None),
            "Plugins": getattr(self._window, "build_plugin_state_snapshot", None),
            "Recovery": getattr(self._window, "build_recovery_state_snapshot", None),
        }
        for name, builder in builders.items():
            editor = self._tab_editors.get(name)
            if editor is None:
                continue
            data = builder() if callable(builder) else {"status": "Not ready yet"}
            editor.setPlainText(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))
        self._refresh_logs()
        self._refresh_ai()
        self._update_summary()

    def _refresh_logs(self) -> None:
        """Refresh the filtered logs tab."""
        editor = self._tab_editors.get("Logs")
        if editor is None:
            return
        lines = list(getattr(self._window, "_combined_debug_log_lines", lambda: [])())
        level = self.logs_level_combo.currentText().strip().upper()
        category = self.logs_category_combo.currentText().strip().lower()
        search = self.logs_search_edit.toPlainText().strip().lower()
        filtered: list[str] = []
        for line in lines:
            probe = line.lower()
            if level != "ALL" and f"[{level.lower()}]" not in probe:
                continue
            if category != "all":
                category_match = {
                    "startup": "[startup]",
                    "ai": "[ai",
                    "updater": "[updater]",
                    "layout": "[layout]",
                    "security": "security",
                    "plugins": "plugin",
                    "terminal": "[terminal]",
                    "general": "",
                }.get(category, "")
                if category_match and category_match not in probe:
                    continue
            if search and search not in probe:
                continue
            filtered.append(line)
        editor.setPlainText("\n".join(filtered))

    def _refresh_ai(self) -> None:
        """Populate the recent AI payload history list."""
        self.ai_history_list.clear()
        controller = getattr(self._window, "ai_controller", None)
        recent = controller.recent_prompt_payloads() if controller is not None and hasattr(controller, "recent_prompt_payloads") else []
        if not recent:
            self.ai_meta_view.setPlainText("No AI payload has been captured yet.")
            self.ai_input_edit.clear()
            self.ai_assembled_edit.clear()
            self.ai_sent_edit.clear()
            return
        for payload in reversed(recent):
            label = f"{payload.get('timestamp_iso', '')} | {payload.get('action_title', '')} | {payload.get('status', '')}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, payload)
            self.ai_history_list.addItem(item)
        self.ai_history_list.setCurrentRow(0)

    def _refresh_ai_selection(self, row: int) -> None:
        """Refresh the right-hand payload views for the selected AI request."""
        item = self.ai_history_list.item(row)
        if item is None:
            return
        payload = dict(item.data(Qt.ItemDataRole.UserRole) or {})
        meta = {
            "timestamp_iso": payload.get("timestamp_iso", ""),
            "action_title": payload.get("action_title", ""),
            "model": payload.get("model", ""),
            "api_key_source": payload.get("api_key_source", ""),
            "streaming": payload.get("streaming", False),
            "sent_chars": payload.get("sent_chars", 0),
            "redaction_changes": payload.get("redaction_changes", []),
            "correlation_id": payload.get("correlation_id", ""),
            "status": payload.get("status", ""),
            "error": payload.get("error", ""),
            "response_chars": payload.get("response_chars", 0),
        }
        self.ai_meta_view.setPlainText(json.dumps(meta, indent=2, sort_keys=True, ensure_ascii=False))
        self.ai_input_edit.setPlainText(str(payload.get("raw_prompt", "") or ""))
        self.ai_assembled_edit.setPlainText(str(payload.get("assembled_prompt", "") or ""))
        self.ai_sent_edit.setPlainText(str(payload.get("sent_prompt", "") or ""))

    def _current_tab_name(self) -> str:
        """Return the current tab label."""
        return self.tabs.tabText(self.tabs.currentIndex()) if self.tabs.currentIndex() >= 0 else "Overview"

    def _update_summary(self) -> None:
        """Refresh the summary label for the active tab."""
        self.summary_label.setText(f"Developer mode diagnostics hub. Current tab: {self._current_tab_name()}.")

    def copy_current_tab(self) -> None:
        """Copy the current tab's most relevant content to the clipboard."""
        tab_name = self._current_tab_name()
        mode = self._tab_copy_mode.get(tab_name, "text")
        if mode == "ai_meta":
            text = self.ai_meta_view.toPlainText()
        else:
            editor = self._tab_editors.get(tab_name)
            text = editor.toPlainText() if editor is not None else ""
        QApplication.clipboard().setText(text)

    def export_snapshot(self) -> None:
        """Delegate snapshot export to the main window when available."""
        if hasattr(self._window, "export_developer_snapshot"):
            self._window.export_developer_snapshot()

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
