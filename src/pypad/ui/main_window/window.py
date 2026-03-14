"""Define the main application window and coordinate the subsystems that make up the desktop editor.

This module belongs to the main-window orchestration layer that ties together menus, actions, state, and dialogs. It helps explain how `pypad.ui.main_window` is structured and where this file fits into the runtime workflow.
"""

import getpass
import base64
import hashlib
import json
import os
import random
import sys
import time
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal, Slot, QFileSystemWatcher
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QIcon,
    QKeySequence,
    QPainter,
    QPalette,
    QPdfWriter,
    QPixmap,
    QTextCursor,
    QTextCharFormat,
    QTextDocument,
) 
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFontDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QDockWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QStackedWidget,
    QStyle,
    QStyleFactory,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtPrintSupport import QPrintDialog, QPrintPreviewDialog, QPrinter

from pypad.ui.debug.debug_logs_dialog import DebugLogsDialog
from pypad.ui.editor.detachable_tab_bar import DetachableTabBar
from pypad.ui.editor.editor_tab import EditorTab, MarkdownPreviewPane
from pypad.ui.ai.ai_controller import AIController
from pypad.ui.ai.ai_chat_dock import AIChatDock
from pypad.ui.theme.asset_paths import resolve_asset_path
from pypad.ui.theme.theme_tokens import build_main_window_qss, build_tokens_from_settings, resolve_dark_mode_from_settings
from pypad.ui.system.autosave import AutoSaveRecoveryDialog, AutoSaveStore
from pypad.ui.system.session_recovery import RecoveryStateStore
from pypad.ui.system.reminders import ReminderStore, RemindersDialog
from pypad.ui.security.security_controller import SecurityController
from pypad.ui.editor.syntax_highlighter import CodeSyntaxHighlighter
from pypad.ui.system.updater_controller import UpdaterController
from pypad.ui.system.version_history import VersionHistoryDialog
from pypad.ui.workspace.workspace_controller import WorkspaceController
from pypad.ui.features.advanced_features import AdvancedFeaturesController
from pypad.ui.features.gamification_widgets import CompactGamificationWidget, GamificationToast, MomentumBannerWidget
from pypad.i18n.translator import AppTranslator

from .ui_setup import UiSetupMixin
from .file_ops import FileOpsMixin
from .edit_ops import EditOpsMixin
from .view_ops import ViewOpsMixin
from .misc import MiscMixin
class Notepad(UiSetupMixin, FileOpsMixin, EditOpsMixin, ViewOpsMixin, MiscMixin, QMainWindow):
    """Main application window that assembles controllers, docks, tabs, and startup flow."""
    windows_by_id: dict[int, "Notepad"] = {}
    system_style_name: str | None = None
    templates: dict[str, str] = {
        "Meeting Notes": "## Meeting Notes\n\nDate: \nAttendees:\n\n### Agenda\n- \n\n### Notes\n- \n\n### Action Items\n- [ ] ",
        "Daily Log": "## Daily Log\n\nDate: \n\n### Priorities\n- [ ] \n\n### Progress\n- \n\n### Blockers\n- \n\n### Wrap Up\n- ",
        "Checklist": "## Checklist\n\n- [ ] Item 1\n- [ ] Item 2\n- [ ] Item 3\n",
    }

    @staticmethod
    def _demo_templates_root() -> Path:
        """Return the packaged demo-template directory used by onboarding features."""
        return Path(__file__).resolve().parents[4] / "templates" / "demo_pack"

    @staticmethod
    def _demo_display_name(path: Path) -> str:
        """Convert a template filename into a readable menu label."""
        stem = path.stem.strip()
        stem = stem.lstrip("0123456789._- ").strip()
        cleaned = stem.replace("_", " ").replace("-", " ").strip()
        return " ".join(part.capitalize() for part in cleaned.split()) or "Demo"

    def _load_demo_templates(self) -> None:
        """Populate the template catalog with built-ins plus demo-pack Markdown files."""
        self.templates = dict(type(self).templates)
        root = self._demo_templates_root()
        if not root.exists() or not root.is_dir():
            return
        for path in sorted(root.glob("*.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            name = f"Demo: {self._demo_display_name(path)}"
            self.templates[name] = text

    def _apply_startup_preview_theme(self) -> None:
        """Apply a lightweight stylesheet early so startup UI matches the saved theme."""
        app = QApplication.instance()
        tokens = build_tokens_from_settings(self.settings)
        effective_dark = resolve_dark_mode_from_settings(self.settings)
        tab_close_icon_name = "tab-close-dark.svg" if effective_dark else "tab-close-light.svg"
        tab_close_icon_path = resolve_asset_path("icons", tab_close_icon_name) or resolve_asset_path("icons", "tab-close.svg")
        tab_close_icon_url = tab_close_icon_path.as_posix() if tab_close_icon_path else ""
        qss = build_main_window_qss(tokens=tokens, tab_close_icon_url=tab_close_icon_url, close_button_visibility_qss="")
        if app is not None:
            app.setStyleSheet(qss)
        else:
            self.setStyleSheet(qss)
        self._last_applied_main_qss = qss

    def __init__(self) -> None:
        """Initialize the main window, attach subsystems, and stage deferred startup work."""
        super().__init__()
        self.setUpdatesEnabled(False)
        self._startup_ui_ready = False
        self._startup_first_paint_ready = False
        self._startup_sequence_done = False
        self._startup_hold_main_window_visible = True
        startup_t0 = time.perf_counter()
        startup_stages: list[tuple[str, int]] = []

        def _mark_startup_stage(name: str) -> None:
            """Internal helper for `_mark_startup_stage`."""
            elapsed_ms = int((time.perf_counter() - startup_t0) * 1000)
            startup_stages.append((name, elapsed_ms))
            try:
                self.log_event("Info", f"[Startup] {name} at {elapsed_ms}ms")
            except Exception:
                pass

        app = QApplication.instance()
        if Notepad.system_style_name is None and app is not None:
            Notepad.system_style_name = app.style().objectName() or "Fusion"
        self.window_id = id(self)
        Notepad.windows_by_id[self.window_id] = self

        self.setWindowTitle("Untitled - Pypad")
        self.resize(800, 600)
        self._load_demo_templates()

        self.word_wrap_enabled = True
        self.last_search_text: str | None = None
        self.macro_recording = False
        self.macro_playing = False
        self._macro_events: list[tuple[str, str]] = []
        self._last_macro_events: list[tuple[str, str]] = []

        self._jump_history: list[dict[str, object]] = []
        self._jump_history_index = -1
        self._suspend_jump_recording = False
        self._quick_open_workspace_cache: list[object] = []
        self._quick_open_cache_root: str = ""
        self._quick_open_cache_built_at = 0.0
        self._quick_open_indexing = False
        self._quick_open_workspace_symbol_cache: list[object] = []
        self._quick_open_workspace_symbol_cache_root: str = ""
        self._quick_open_workspace_symbol_cache_built_at = 0.0
        self._quick_open_workspace_symbol_indexing = False
        self._search_results_query = ""
        self._search_results_items: list[dict[str, object]] = []
        self._search_results_index = -1
        self.closed_tabs_history: list[dict[str, object]] = []
        self.ai_usage_session = {
            "requests": 0,
            "tokens": 0,
            "estimated_cost": 0.0,
        }
        self.detached_windows: list["Notepad"] = []
        self.debug_logs: list[str] = []
        self.debug_logs_dialog: DebugLogsDialog | None = None
        self._icon_color: QColor | None = None

        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        tab_bar = DetachableTabBar(self.tab_widget)
        tab_bar.detach_requested.connect(self.detach_tab_to_window)
        tab_bar.setDrawBase(False)
        tab_bar.setMovable(True)
        self.tab_widget.setTabBar(tab_bar)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.empty_tabs_widget = self._build_empty_tabs_widget()
        self.central_stack = QStackedWidget(self)
        self.central_stack.addWidget(self.tab_widget)
        self.central_stack.addWidget(self.empty_tabs_widget)
        placeholder = QWidget(self)
        placeholder.setFixedSize(0, 0)
        placeholder.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setCentralWidget(placeholder)
        self.editor_dock = QDockWidget("Editor", self)
        self.editor_dock.setObjectName("editorDock")
        self.editor_dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.editor_dock.setFeatures(
            QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable
        )
        if hasattr(self, "_install_custom_dock_title_bar"):
            self._install_custom_dock_title_bar(self.editor_dock, "Editor", "editor_dock_title_bar")
        self.editor_dock.setWidget(self.central_stack)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.editor_dock)
        if hasattr(self, "_sync_layout_panel_actions"):
            self.editor_dock.visibilityChanged.connect(lambda _v: self._sync_layout_panel_actions())
        self.markdown_preview_dock = QDockWidget("Markdown Preview", self)
        self.markdown_preview_dock.setObjectName("markdownPreviewDock")
        self.markdown_preview_dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.markdown_preview_dock.setFeatures(
            QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable
        )
        if hasattr(self, "_install_custom_dock_title_bar"):
            self._install_custom_dock_title_bar(
                self.markdown_preview_dock,
                "Markdown Preview",
                "markdown_preview_dock_title_bar",
            )
        self.markdown_preview_pane = MarkdownPreviewPane(self.markdown_preview_dock)
        self.markdown_preview_dock.setWidget(self.markdown_preview_pane)
        self.markdown_preview_dock.setMinimumWidth(260)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.markdown_preview_dock)
        self.markdown_preview_dock.visibilityChanged.connect(self._on_markdown_preview_dock_visibility_changed)
        self.markdown_preview_dock.hide()
        self.setAcceptDrops(True)

        # Simple in-memory settings
        self.settings: dict = self._build_default_settings()
        if hasattr(self, "apply_logging_preferences"):
            self.apply_logging_preferences()
        self.log_event("Info", "[Startup] Default settings created")
        self._easter_egg_running = False
        self.settings_file = self._get_settings_file_path()
        self.load_settings_from_disk()
        if hasattr(self, "apply_logging_preferences"):
            self.apply_logging_preferences()
        self.log_event("Info", f"[Startup] Settings loaded from: {self.settings_file}")
        loaded_closed = self.settings.get("closed_tab_history", [])
        self.closed_tabs_history = list(loaded_closed) if isinstance(loaded_closed, list) else []
        self._page_layout_view_enabled = bool(self.settings.get("page_layout_view_enabled", False))
        self.line_numbers_enabled = bool(self.settings.get("npp_margin_line_numbers_enabled", True))
        _mark_startup_stage("settings_loaded")
        self.translator = AppTranslator(self._get_translation_cache_path())
        self.log_event("Info", "[Startup] Translator initialized")
        self.workspace_controller = WorkspaceController(self)
        self.log_event("Info", "[Startup] Workspace controller initialized")
        self.security_controller = SecurityController(self)
        self.log_event("Info", "[Startup] Security controller initialized")
        self.ai_controller = AIController(self)
        self.log_event("Info", "[Startup] AI controller initialized")
        self.ai_chat_dock = AIChatDock(self, self.ai_controller)
        self.ai_chat_dock.setObjectName("aiChatDock")
        self.ai_chat_dock.setMinimumWidth(180)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.ai_chat_dock)
        self.ai_chat_dock.visibilityChanged.connect(self.update_action_states)
        self.ai_chat_dock.hide()
        self.updater_controller = UpdaterController(self)
        self.updater_controller.update_availability_changed.connect(self._on_update_availability_changed)
        self.log_event("Info", "[Startup] Updater controller initialized")
        self.reminders_store = ReminderStore(self._get_reminders_file_path())
        self.reminders_store.load()
        self.log_event("Info", "[Startup] Reminders loaded")
        self.autosave_store = AutoSaveStore(self._get_autosave_dir_path())
        self.autosave_store.load()
        self.log_event("Info", "[Startup] Autosave store loaded")
        self.recovery_state_store = RecoveryStateStore(self._get_autosave_dir_path())
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self._run_autosave_cycle)
        self._editor_refresh_timer = QTimer(self)
        self._editor_refresh_timer.setSingleShot(True)
        self._editor_refresh_timer.setInterval(90)
        self._editor_refresh_timer.timeout.connect(self.update_status_bar)
        self._gamification_refresh_timer = QTimer(self)
        self._gamification_refresh_timer.setSingleShot(True)
        self._gamification_refresh_timer.setInterval(120)
        self._gamification_refresh_timer.timeout.connect(self._gamification_on_text_changed)
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self._check_reminders)
        self.file_watcher = QFileSystemWatcher(self)
        self.file_watcher.fileChanged.connect(self._on_file_changed)
        _mark_startup_stage("controllers_initialized")

        # Status bar
        self.status = QStatusBar(self)
        self.status.setSizeGripEnabled(False)
        self.status.setContentsMargins(0, 0, 0, 0)
        self.status.setFixedHeight(24)
        self.status.setStyleSheet(
            """
            QStatusBar {
                padding: 0px;
            }
            QStatusBar::item {
                border: none;
                margin: 0px;
                padding: 0px;
            }
            """
        )
        self.setStatusBar(self.status)
        self.log_event("Info", "[Startup] Status bar initialized")

        # Status bar widgets
        self.position_label = QLabel("Ln 1, Col 1", self)
        self.zoom_label = QLabel("100%", self)
        # End-of-line and encoding indicators (bottom-right by default)
        # Values are updated dynamically in update_status_bar()
        self.eol_label = QLabel("", self)
        self.encoding_label = QLabel("UTF-8", self)

        for label in (self.position_label, self.zoom_label, self.eol_label, self.encoding_label):
            label.setMargin(0)
            self.status.addPermanentWidget(label)

        self.syntax_label = QLabel("Lang", self)
        self.syntax_label.setMargin(1)
        self.syntax_combo = QComboBox(self)
        self.syntax_combo.addItems(["Auto", "Python", "JavaScript", "JSON", "Markdown", "Plain"])
        self.syntax_combo.setMinimumWidth(64)
        self.syntax_combo.setMaximumWidth(88)
        self.syntax_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        self.syntax_combo.currentTextChanged.connect(self._set_active_tab_language)
        self.status.addPermanentWidget(self.syntax_label)
        self.status.addPermanentWidget(self.syntax_combo)
        self.breadcrumb_label = QLabel("-", self)
        self.breadcrumb_label.setMargin(0)
        self.status.addPermanentWidget(self.breadcrumb_label)
        self.selection_stats_label = QLabel("W 0 | C 0", self)
        self.selection_stats_label.setMargin(0)
        self.status.addPermanentWidget(self.selection_stats_label)
        self.ruler_label = QLabel("", self)
        self.ruler_label.setMargin(0)
        self.ruler_label.setVisible(False)
        self.status.addPermanentWidget(self.ruler_label)
        self.ai_usage_label = QLabel("AI 0", self)
        self.ai_usage_label.setMargin(0)
        self.status.addPermanentWidget(self.ai_usage_label)
        self.autosave_status_label = QLabel("Save idle", self)
        self.autosave_status_label.setMargin(0)
        self.status.addPermanentWidget(self.autosave_status_label)
        self.gamification_status_widget = CompactGamificationWidget(self)
        self.gamification_status_widget.open_requested.connect(self.open_gamification_dashboard)
        self.status.addPermanentWidget(self.gamification_status_widget)
        self.momentum_banner_widget = MomentumBannerWidget(self)
        self.momentum_banner_widget.recommended_action_requested.connect(self.run_coach_recommendation)
        self.status.addPermanentWidget(self.momentum_banner_widget, 1)
        self.gamification_reward_toast = GamificationToast(self)
        self.quiz_quit_button = QPushButton("Quit", self)
        self.quiz_quit_button.setVisible(False)
        self.quiz_quit_button.clicked.connect(self.quit_quiz_mode)
        self.status.addPermanentWidget(self.quiz_quit_button)
        self.quiz_finish_button = QPushButton("Finish", self)
        self.quiz_finish_button.setVisible(False)
        self.quiz_finish_button.clicked.connect(self.finish_quiz_mode)
        self.status.addPermanentWidget(self.quiz_finish_button)
        self.typing_test_quit_button = QPushButton("Quit Test", self)
        self.typing_test_quit_button.setVisible(False)
        self.typing_test_quit_button.clicked.connect(self.quit_typing_speed_test)
        self.status.addPermanentWidget(self.typing_test_quit_button)
        self.log_event("Info", "[Startup] Status bar widgets attached")
        self.advanced_features = AdvancedFeaturesController(self)
        if hasattr(self, "_init_gamification_system"):
            self._init_gamification_system()
        _mark_startup_stage("advanced_features_ready")
        self.log_event("Info", "[Startup] Advanced features ready")
        self.setDockOptions(
            QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.AllowNestedDocks
        )
        self.log_event("Info", "[Startup] Dock options set")
        if hasattr(self, "_init_layout_docks"):
            self._init_layout_docks()
            self.log_event("Info", "[Startup] Layout docks initialized")

        self.add_new_tab(make_current=True)
        self.update_status_bar()
        self.log_event("Info", "[Startup] Initial tab created")

        self.create_actions()
        self.log_event("Info", "[Startup] Actions created")
        self._connect_action_debug_tracing()
        self.configure_action_tooltips()
        self.create_menus()
        self.log_event("Info", "[Startup] Menus created")
        self.configure_menu_tooltips()
        self.create_toolbars()
        self.log_event("Info", "[Startup] Toolbars created")
        try:
            self._apply_startup_preview_theme()
            self.log_event("Info", "[Startup] Preview theme applied")
        except Exception as exc:
            self.log_event("Error", f"[Startup] preview theme apply failed: {exc!r}")
        if bool(self.settings.get("simple_mode", False)):
            self.toggle_simple_mode(True, persist=False)
        _mark_startup_stage("ui_ready")
        self._startup_ui_ready = True
        self.ensurePolished()
        self.setUpdatesEnabled(True)
        self.log_event("Info", "[Startup] UI ready")

        # Finish startup on the next event-loop tick so the main window can appear sooner.
        def _finish_startup_sequence() -> None:
            """Internal helper for `_finish_startup_sequence`."""
            deferred_start = time.perf_counter()
            deferred_marks: list[tuple[str, int]] = []

            def _mark_deferred(name: str) -> None:
                """Internal helper for `_mark_deferred`."""
                deferred_marks.append((name, int((time.perf_counter() - deferred_start) * 1000)))

            if not self._startup_first_paint_ready:
                self._startup_first_paint_ready = True
                app = QApplication.instance()
                startup_ready_cb = app.property("startup_ready_callback") if app is not None else None
                if callable(startup_ready_cb):
                    try:
                        startup_ready_cb(self)
                    except Exception:
                        pass
            try:
                self._offer_crash_recovery()
                _mark_deferred("crash_recovery")
            except Exception as exc:  # noqa: BLE001
                self.log_event("Error", f"[Startup] crash recovery offer failed: {exc!r}")
            finally:
                self._startup_hold_main_window_visible = False
            try:
                self.apply_settings(startup_deferred=True)
                self.log_event("Info", "[Startup] Settings applied")
                _mark_deferred("apply_settings")
            except Exception as exc:  # noqa: BLE001
                self.log_event("Error", f"[Startup] apply_settings failed: {exc!r}")
                traceback_text = traceback.format_exc().strip()
                self.log_event("Error", traceback_text)
            startup_files, startup_folders = self._collect_startup_items()
            if startup_files or startup_folders:
                open_items_started = time.perf_counter()
                self._open_startup_items(startup_files, startup_folders)
                self.log_event(
                    "Info",
                    f"[Startup] _open_startup_items elapsed={int((time.perf_counter() - open_items_started) * 1000)}ms "
                    f"files={len(startup_files)} folders={len(startup_folders)}",
                )
                _mark_deferred("startup_items_opened")
            else:
                profile_handled = False
                if hasattr(self, "apply_workspace_profile_on_startup"):
                    try:
                        profile_started = time.perf_counter()
                        profile_handled = bool(self.apply_workspace_profile_on_startup())
                        profile_elapsed = int((time.perf_counter() - profile_started) * 1000)
                        self.log_event(
                            "Info",
                            f"[Startup] apply_workspace_profile_on_startup elapsed={profile_elapsed}ms handled={profile_handled}",
                        )
                        _mark_deferred("workspace_profile_checked")
                    except Exception as exc:  # noqa: BLE001
                        self.log_event("Error", f"[Startup] workspace profile startup failed: {exc!r}")
                if not profile_handled:
                    restore_started = time.perf_counter()
                    self.restore_last_session(startup_deferred=True)
                    self.log_event(
                        "Info",
                        f"[Startup] restore_last_session dispatch elapsed={int((time.perf_counter() - restore_started) * 1000)}ms",
                    )
                    _mark_deferred("session_restore_dispatched")
            self.log_event("Info", "[Startup] Session restore completed")
            self.update_action_states()
            self.log_event("Info", "Pypad initialized")
            _mark_startup_stage("session_restored")
            startup_total_ms = int((time.perf_counter() - startup_t0) * 1000)
            stage_summary = ", ".join(f"{name}={ms}ms" for name, ms in startup_stages)
            deferred_summary = ", ".join(f"{name}={ms}ms" for name, ms in deferred_marks)
            print(f"[startup] pypad_init_total={startup_total_ms}ms | {stage_summary}")
            self.log_event("Info", f"Startup timing: total={startup_total_ms}ms; {stage_summary}")
            if deferred_summary:
                self.log_event("Info", f"Startup deferred timing: {deferred_summary}")
            if self.settings.get("auto_check_updates", True):
                QTimer.singleShot(1500, lambda: self.check_for_updates(manual=False))
            QTimer.singleShot(300, self._maybe_show_welcome_tutorial)
            if hasattr(self, "_prewarm_settings_dialog_cache") and bool(
                self.settings.get("settings_dialog_prewarm_enabled", False)
            ):
                # Optional: prewarm can improve first-open latency, but can be heavy
                # on some systems. Keep it opt-in.
                QTimer.singleShot(800, self._prewarm_settings_dialog_cache)
            self._startup_sequence_done = True

        if bool(self.settings.get("fast_startup_mode", True)):
            self.log_event("Info", "[Startup] Fast startup mode enabled: scheduling deferred startup sequence")
            QTimer.singleShot(0, _finish_startup_sequence)
        else:
            self.log_event("Info", "[Startup] Fast startup mode disabled: running synchronous startup sequence")
            _finish_startup_sequence()

        # Lock screen enforcement is triggered from main() after the window is shown.

    @Slot(bool, str)
    def _on_update_availability_changed(self, available: bool, version: str) -> None:
        """Reflect updater state in the menu action that advertises available releases."""
        action = getattr(self, "update_available_menu_action", None)
        if action is None:
            return
        if available:
            pretty = str(version or "").strip()
            if pretty:
                action.setText(f"Update Available ({pretty}) - Check for &Updates...")
            else:
                action.setText("Update Available - Check for &Updates...")
            action.setVisible(True)
            return
        action.setVisible(False)

    def focusInEvent(self, event: QEvent) -> None:  # type: ignore[override]
        """Forward focus-gained notifications into the plugin event pipeline."""
        super().focusInEvent(event)
        if hasattr(self, "_emit_plugin_event"):
            self._emit_plugin_event("window_focus", tab=self.active_tab())

    def focusOutEvent(self, event: QEvent) -> None:  # type: ignore[override]
        """Forward focus-lost notifications into the plugin event pipeline."""
        super().focusOutEvent(event)
        if hasattr(self, "_emit_plugin_event"):
            self._emit_plugin_event("window_blur", tab=self.active_tab())

    def _collect_startup_items(self) -> tuple[list[str], list[str]]:
        """Parse process arguments into existing file and folder paths for startup opening."""
        app = QApplication.instance()
        if app is None:
            return [], []
        args = list(app.arguments())[1:]
        if not args:
            return [], []
        seen: set[str] = set()
        files: list[str] = []
        folders: list[str] = []
        for arg in args:
            if not arg:
                continue
            if arg.startswith("-") and not Path(arg).exists():
                continue
            candidate = Path(arg)
            if not candidate.is_absolute():
                candidate = Path.cwd() / candidate
            try:
                resolved = candidate.resolve()
            except Exception:
                resolved = candidate
            if not resolved.exists():
                continue
            path_str = str(resolved)
            if path_str in seen:
                continue
            seen.add(path_str)
            if resolved.is_dir():
                folders.append(path_str)
            elif resolved.is_file():
                files.append(path_str)
        return files, folders

    def _open_startup_items(self, files: list[str], folders: list[str]) -> None:
        """Open startup files and optionally adopt the first folder as the workspace root."""
        if folders:
            workspace_root = folders[0]
            self.settings["workspace_root"] = workspace_root
            self.settings["last_session_workspace_root"] = workspace_root
            if hasattr(self, "save_settings_to_disk"):
                self.save_settings_to_disk()
            self.show_status_message(f"Workspace: {workspace_root}", 3000)
            if hasattr(self, "_refresh_workspace_dock"):
                self._refresh_workspace_dock()

        opened: list[str] = []
        first_opened: str | None = None
        for path in files:
            if self._open_file_path(path):
                opened.append(path)
                if first_opened is None:
                    first_opened = path
        if first_opened:
            for index in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(index)
                if isinstance(tab, EditorTab) and tab.current_file == first_opened:
                    self.tab_widget.setCurrentIndex(index)
                    break
        if opened:
            self.log_event("Info", f"Opened on startup: {', '.join(opened)}")

