# Literally my biggest script ever
from __future__ import annotations
import getpass
import importlib.metadata as importlib_metadata
import base64
import hashlib
import json
import os
import random
import re
import shutil
import sys
import time
import webbrowser
import subprocess
import threading
import traceback
from typing import TYPE_CHECKING, Any
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
from html import escape as html_escape
from urllib.parse import quote as url_quote, unquote as url_unquote

from PySide6.QtCore import QByteArray, QEvent, QFileInfo, QObject, QPoint, QRect, QSize, Qt, QTimer, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QPainter,
    QPen,
    QPolygonF,
    QKeySequence,
    QShortcut,
    QPdfWriter,
    QTextCursor,
    QTextCharFormat,
    QTextDocument,
) 
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFileDialog,
    QFileIconProvider,
    QFileSystemModel,
    QFontDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
    QStyleFactory,
    QToolButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QTreeView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtPrintSupport import QPrintDialog, QPrintPreviewDialog, QPrinter
from pypad.logging_utils import get_logger

_LOGGER = get_logger(__name__)

THEME_SETTINGS_KEYS: tuple[str, ...] = (
    "theme",
    "app_style",
    "dark_mode",
    "follow_system_theme",
    "use_custom_colors",
    "custom_editor_bg",
    "custom_editor_fg",
    "custom_chrome_bg",
    "accent_color",
    "ui_density",
)

from pypad.ui.debug.debug_logs_dialog import DebugLogsDialog
from pypad.ui.editor.detachable_tab_bar import DetachableTabBar
from pypad.ui.editor.editor_tab import EditorTab
from ...app_settings import (
    normalize_ui_visibility_settings,
    migrate_settings,
)
from pypad.app_settings.defaults import DEFAULT_UPDATE_FEED_URL
from pypad.app_settings.scintilla_profile import ScintillaProfile
from pypad.ui.ai.ai_controller import AIController
from pypad.ui.ai.ai_edit_preview_dialog import AIEditPreviewDialog
from pypad.ui.theme.asset_paths import resolve_asset_path
from pypad.ui.system.autosave import AutoSaveRecoveryDialog, AutoSaveStore
from pypad.ui.system.reminders import ReminderStore, RemindersDialog
from pypad.ui.security.security_controller import SecurityController
from pypad.ui.editor.syntax_highlighter import CodeSyntaxHighlighter
from pypad.ui.system.updater_controller import UpdaterController
from pypad.ui.system.version_history import VersionEntry, VersionHistoryDialog
from pypad.ui.workspace.workspace_controller import WorkspaceController
from pypad.ui.theme.dialog_theme import apply_dialog_theme_from_window, ensure_dialog_theme_filter_installed
from pypad.ui.theme.theme_tokens import build_main_window_qss, build_tokens_from_settings, resolve_dark_mode_from_settings
from pypad.ui.system.session_recovery import local_history_key
from pypad.ui.editor.advanced_text_tools import build_line_refs, export_line_refs_text
from pypad.ui.document.document_fidelity import DocumentFidelityError, export_document_text, render_text_to_html
from pypad.ui.features.extensibility_ops import discover_window_actions
from pypad.ui.features.gamification_system import GamificationSystem, XPResult
from pypad.ui.features.gamification_dashboard_dialog import GamificationDashboardDialog
from pypad.ui.features.gamification_widgets import CompactGamificationWidget, ProductivityHubDialog, ProductivityHubWidget
from .notepadpp_pref_runtime import (
    apply_notepadpp_runtime_settings,
    apply_indentation_defaults_to_tab,
)
from pypad.ui.ai.ai_collaboration import (
    build_ai_conflict_merge_prompt,
    build_conflict_markers,
    build_project_qa_prompt,
    build_workspace_citation_snippets,
    build_collab_presence_text,
    paragraph_bounds,
    strip_model_fences,
)
from .settings_dialog import SettingsDialog as SidebarSettingsDialog
from pypad.ui.features.tutorial_dialog import InteractiveTutorialDialog
from pypad.ui.editor.shortcut_mapper import PRESET_SHORTCUTS, ShortcutActionRow, ShortcutMapperDialog, parse_shortcut_value, sequence_to_string
from pypad.ui.editor.command_palette import CommandPaletteDialog, PaletteItem
from pypad.ui.editor.quick_open_dialog import QuickOpenDialog, QuickOpenEntry, extract_symbol_rows
from pypad.ui.editor.spellcheck import spellcheck_available, suggestions_for_word, unknown_words, word_span_at
from pypad.i18n.translator import language_code_for
from .misc_settings_recent import MiscSettingsRecentMixin
from .misc_tab_metadata import MiscTabMetadataMixin
from .misc_window_tabs import MiscWindowTabsMixin
from .misc_file_state import MiscFileStateMixin
from .misc_tab_actions import MiscTabActionsMixin
from .misc_edit_utils import MiscEditUtilsMixin
from .misc_export import MiscExportMixin
from .misc_ai_usage import MiscAiUsageMixin
from .misc_ai_templates import MiscAiTemplatesMixin
from .misc_quick_open import MiscQuickOpenMixin
from .misc_settings_dialog import SettingsDialog

class MiscMixin(
    MiscSettingsRecentMixin,
    MiscTabMetadataMixin,
    MiscWindowTabsMixin,
    MiscFileStateMixin,
    MiscTabActionsMixin,
    MiscEditUtilsMixin,
    MiscExportMixin,
    MiscAiUsageMixin,
    MiscAiTemplatesMixin,
    MiscQuickOpenMixin,
):
    if TYPE_CHECKING:
        def __getattr__(self, name: str) -> Any: ...

    class _EasterEggBall(QWidget):
        class _BallPreview(QWidget):
            def __init__(self, color: QColor, parent: QWidget | None = None) -> None:
                super().__init__(parent)
                self._color = QColor(color)
                self.setFixedSize(86, 86)

            def set_color(self, color: QColor) -> None:
                self._color = QColor(color)
                self.update()

            def paintEvent(self, event) -> None:  # type: ignore[override]
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                painter.fillRect(self.rect(), QColor("#1f2329"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(self._color)
                painter.drawEllipse(10, 10, 66, 66)
                painter.setBrush(QColor(255, 255, 255, 80))
                painter.drawEllipse(24, 18, 18, 14)
                painter.end()
                super().paintEvent(event)

        def __init__(self, host: QWidget) -> None:
            super().__init__(host)
            self._host = host
            self._diameter = 56
            self._pos_x = 0.0
            self._pos_y = 0.0
            self._vel_x = 3.4
            self._vel_y = -2.0
            self._gravity = 0.42
            self._bounce = 0.86
            self._friction = 0.992
            self._drag_offset = QPoint()
            self._dragging = False
            self._ball_color = QColor("#ff8a00")
            self.setObjectName("pypadEasterEggBall")
            self.setFixedSize(self._diameter, self._diameter)
            self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.raise_()
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick)
            self._timer.start(16)

        def paintEvent(self, event) -> None:  # type: ignore[override]
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._ball_color)
            painter.drawEllipse(2, 2, self._diameter - 4, self._diameter - 4)
            painter.setBrush(QColor(255, 255, 255, 80))
            painter.drawEllipse(11, 9, 16, 12)
            painter.end()
            super().paintEvent(event)

        def mousePressEvent(self, event) -> None:  # type: ignore[override]
            if event.button() == Qt.MouseButton.LeftButton:
                self._dragging = True
                self._drag_offset = event.position().toPoint()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return
            super().mousePressEvent(event)

        def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
            if self._dragging:
                target = self.mapToParent(event.position().toPoint() - self._drag_offset)
                bounded = self._bounded_pos(target)
                self._set_float_pos(bounded.x(), bounded.y())
                event.accept()
                return
            super().mouseMoveEvent(event)

        def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
            if event.button() == Qt.MouseButton.LeftButton and self._dragging:
                self._dragging = False
                self.setCursor(Qt.CursorShape.OpenHandCursor)
                bounds = self._bounds_rect()
                center = bounds.center()
                ball_center = self.geometry().center()
                self._vel_x = -4.2 if ball_center.x() >= center.x() else 4.2
                self._vel_y = -6.5 if ball_center.y() >= center.y() else -4.8
                event.accept()
                return
            if event.button() == Qt.MouseButton.RightButton:
                self._open_color_picker()
                event.accept()
                return
            super().mouseReleaseEvent(event)

        def moveEvent(self, event) -> None:  # type: ignore[override]
            pos = self.pos()
            self._pos_x = float(pos.x())
            self._pos_y = float(pos.y())
            super().moveEvent(event)

        def _bounded_pos(self, pos: QPoint) -> QPoint:
            bounds = self._bounds_rect()
            min_x = bounds.left()
            min_y = bounds.top()
            max_x = max(min_x, bounds.right() - self.width() + 1)
            max_y = max(min_y, bounds.bottom() - self.height() + 1)
            return QPoint(max(min_x, min(pos.x(), max_x)), max(min_y, min(pos.y(), max_y)))

        def _bounds_rect(self) -> QRect:
            host = self.parentWidget()
            if host is None:
                return QRect(0, 0, 800, 600)
            return host.rect()

        def _open_color_picker(self) -> None:
            dlg = QDialog(self, Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
            dlg.setWindowTitle("Ball Color")
            dlg.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
            dlg.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, False)
            dlg.setWindowFlag(Qt.WindowType.MSWindowsFixedSizeDialogHint, True)
            dlg.setSizeGripEnabled(False)
            apply_dialog_theme_from_window(self._host, dlg)
            layout = QVBoxLayout(dlg)
            layout.setContentsMargins(12, 12, 12, 12)
            preview = self._BallPreview(self._ball_color, dlg)
            preview_label = QLabel("Preview", dlg)
            choose_btn = QPushButton("Choose Color...", dlg)
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Orientation.Horizontal, dlg)
            chosen = QColor(self._ball_color)

            def _choose() -> None:
                nonlocal chosen
                color = QColorDialog.getColor(chosen, dlg, "Choose Ball Color")
                if color.isValid():
                    chosen = QColor(color)
                    preview.set_color(chosen)

            choose_btn.clicked.connect(_choose)
            buttons.accepted.connect(dlg.accept)
            buttons.rejected.connect(dlg.reject)
            layout.addWidget(preview_label)
            layout.addWidget(preview, 0, Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(choose_btn)
            layout.addWidget(buttons)
            dlg.setFixedSize(dlg.sizeHint())
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self._ball_color = QColor(chosen)
                self.update()

        def _tick(self) -> None:
            if self._dragging:
                return
            bounds = self._bounds_rect()
            min_x = float(bounds.left())
            min_y = float(bounds.top())
            max_x = float(max(bounds.left(), bounds.right() - self.width() + 1))
            max_y = float(max(bounds.top(), bounds.bottom() - self.height() + 1))
            self._vel_y += self._gravity
            self._vel_x *= self._friction
            next_x = self._pos_x + self._vel_x
            next_y = self._pos_y + self._vel_y
            if next_x <= min_x:
                next_x = min_x
                self._vel_x = abs(self._vel_x) * self._bounce
            elif next_x >= max_x:
                next_x = max_x
                self._vel_x = -abs(self._vel_x) * self._bounce
            if next_y <= min_y:
                next_y = min_y
                self._vel_y = abs(self._vel_y) * self._bounce
            elif next_y >= max_y:
                next_y = max_y
                self._vel_y = -abs(self._vel_y) * self._bounce
                self._vel_x *= 0.985
                if abs(self._vel_y) < 1.2:
                    self._vel_y = -3.8
            self._set_float_pos(next_x, next_y)

        def _set_float_pos(self, x: float, y: float) -> None:
            self._pos_x = float(x)
            self._pos_y = float(y)
            self.move(int(round(self._pos_x)), int(round(self._pos_y)))

        def closeEvent(self, event) -> None:  # type: ignore[override]
            self._timer.stop()
            super().closeEvent(event)

    # ---------- Misc ----------
    class _ExplorerIconProvider(QFileIconProvider):
        def __init__(self, owner: "MiscMixin") -> None:
            super().__init__()
            self._owner = owner

        def icon(self, arg):  # type: ignore[override]
            if isinstance(arg, QFileInfo):
                info = arg
                name = self._owner._explorer_icon_name_for_info(info)
                if name:
                    icon = self._owner._svg_icon(name)
                    if not icon.isNull():
                        return icon
            return super().icon(arg)

    class _ExplorerItemDelegate(QStyledItemDelegate):
        def __init__(self, view: QTreeView, owner: "MiscMixin") -> None:
            super().__init__(view)
            self._view = view
            self._owner = owner
            self._chevron_w = 14

        def _chevron_rect(self, option: QStyleOptionViewItem) -> QRect:
            return QRect(option.rect.left() + 2, option.rect.top(), self._chevron_w, option.rect.height())

        def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:  # type: ignore[override]
            if index.column() != 0:
                super().paint(painter, option, index)
                return
            opt = QStyleOptionViewItem(option)
            self.initStyleOption(opt, index)
            has_children = bool(index.model().hasChildren(index))
            # Reserve a left gutter for VSCode-like chevrons.
            opt.rect = QRect(
                option.rect.left() + self._chevron_w,
                option.rect.top(),
                max(0, option.rect.width() - self._chevron_w),
                option.rect.height(),
            )
            super().paint(painter, opt, index)
            if not has_children:
                return
            color = QColor(getattr(self._owner, "_icon_color", QColor("#c9d1d9")))
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            pen = QPen(color, 1.6)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            rect = self._chevron_rect(option)
            cx = rect.left() + (rect.width() // 2)
            cy = rect.top() + (rect.height() // 2)
            expanded = self._view.isExpanded(index)
            if expanded:
                points = QPolygonF(
                    [
                        QPoint(cx - 3, cy - 1),
                        QPoint(cx, cy + 2),
                        QPoint(cx + 3, cy - 1),
                    ]
                )
            else:
                points = QPolygonF(
                    [
                        QPoint(cx - 1, cy - 3),
                        QPoint(cx + 2, cy),
                        QPoint(cx - 1, cy + 3),
                    ]
                )
            painter.drawPolyline(points)
            painter.restore()

        def editorEvent(self, event, model, option, index):  # type: ignore[override]
            if index.column() == 0 and bool(model.hasChildren(index)):
                if event.type() == QEvent.Type.MouseButtonRelease:
                    pos = event.pos()
                    if self._chevron_rect(option).contains(pos):
                        if self._view.isExpanded(index):
                            self._view.collapse(index)
                        else:
                            self._view.expand(index)
                        return True
            return super().editorEvent(event, model, option, index)

    @staticmethod
    def _normalize_tags(raw: list[str] | tuple[str, ...] | str) -> list[str]:
        if isinstance(raw, str):
            tokens = [part.strip() for part in raw.split(",")]
        else:
            tokens = [str(part).strip() for part in raw]
        deduped: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            if not token:
                continue
            key = token.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(token)
        return deduped

    def _init_gamification_system(self) -> None:
        self.gamification = GamificationSystem(self.settings)
        self.gamification.quests_snapshot()
        self._gamification_prev_text_len = 0
        self._focus_sprint_deadline_ts = 0.0
        self._session_shortcut_count = 0
        self._session_word_bursts = 0
        self._focus_sprint_timer = QTimer(self)
        self._focus_sprint_timer.setSingleShot(True)
        self._focus_sprint_timer.timeout.connect(self._finish_focus_sprint)
        self._sync_seasonal_events()
        self._update_gamification_status_labels()

    def _gamification_enabled(self) -> bool:
        return bool(self.settings.get("gamification_enabled", True))

    def _session_review_enabled(self) -> bool:
        return bool(self.settings.get("session_review_enabled", False))

    def _sync_seasonal_events(self) -> None:
        if not self._gamification_enabled():
            return
        if not self.gamification.active_events():
            return
        self.gamification.sync_active_event_progress()

    def _refresh_seasonal_event_state(self) -> None:
        if not self._gamification_enabled() or not hasattr(self, "gamification"):
            return
        unlocked = self.gamification.sync_active_event_progress()
        for badge in unlocked:
            self.gamification.push_activity(f"Event Badge: {badge}", "Seasonal quest complete.")
            toast = getattr(self, "gamification_reward_toast", None)
            if toast is not None:
                toast.show_reward(f"Event Badge: {badge}", "Seasonal quest complete.", 3400)
            self.show_status_message(f"Seasonal event unlocked: {badge}", 3400)
        self._refresh_productivity_hub()

    def _update_gamification_status_labels(self) -> None:
        if not hasattr(self, "gamification") or not self._gamification_enabled():
            return
        payload = self.gamification.progress_snapshot()
        if hasattr(self, "gamification_status_widget"):
            self.gamification_status_widget.update_payload(payload)
        if hasattr(self, "status_panel_gamification_widget"):
            self.status_panel_gamification_widget.update_payload(payload)

    def _show_gamification_progress(self, result: XPResult | None, notes: list[str] | None = None) -> None:
        if not self._gamification_enabled():
            return
        self._update_gamification_status_labels()
        milestone_notes = self.gamification.sync_milestones()
        if result is None:
            if milestone_notes:
                for note in milestone_notes:
                    self.gamification.push_activity("Milestone", note)
                self._refresh_productivity_hub()
            return
        msg = f"+{result.xp_added} XP"
        if result.leveled_up:
            msg += f" | Level {result.level_after}"
        fallback_detail = str(self.gamification.state().get("last_xp_reason", "") or "Progress updated")
        if notes:
            msg += f" | {notes[0]}"
        self.gamification.push_activity(
            f"+{result.xp_added} XP",
            notes[0] if notes else fallback_detail,
        )
        self.show_status_message(msg, 3000)
        toast = getattr(self, "gamification_reward_toast", None)
        if toast is not None:
            title = f"+{result.xp_added} XP"
            if result.leveled_up:
                title += f"  Level {result.level_after}"
            detail = notes[0] if notes else fallback_detail
            toast.show_reward(title, detail, 2800)
            if milestone_notes:
                for note in milestone_notes:
                    toast.show_reward("Milestone Reached", note, 3200)
        for note in milestone_notes:
            self.gamification.push_activity("Milestone", note)
            self.show_status_message(note, 3200)
        self._refresh_seasonal_event_state()
        self._refresh_productivity_hub()

    def _refresh_productivity_hub(self) -> None:
        if hasattr(self, "gamification") and hasattr(self, "momentum_banner_widget"):
            self.momentum_banner_widget.update_payload(self.gamification.productivity_snapshot())
        hub = getattr(self, "productivity_hub_widget", None)
        if hub is None or not hasattr(self, "gamification"):
            return
        hub.update_payload(self.gamification.productivity_snapshot())

    def _show_productivity_info_dialog(
        self,
        *,
        title: str,
        subtitle: str,
        sections: list[tuple[str, list[str]]],
        primary_label: str | None = None,
        primary_handler=None,
    ) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.resize(760, 560)
        apply_dialog_theme_from_window(self, dlg)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        title_label = QLabel(title, dlg)
        title_label.setStyleSheet("font-size: 18px; font-weight: 700;")
        subtitle_label = QLabel(subtitle, dlg)
        subtitle_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        for section_title, rows in sections:
            header = QLabel(section_title, dlg)
            header.setStyleSheet("font-weight: 600;")
            body = QTextEdit(dlg)
            body.setReadOnly(True)
            body.setMinimumHeight(96)
            body.setPlainText("\n".join(str(row) for row in rows if str(row).strip()) or "Nothing to show yet.")
            layout.addWidget(header)
            layout.addWidget(body)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, Qt.Horizontal, dlg)
        if primary_label and callable(primary_handler):
            primary_btn = buttons.addButton(primary_label, QDialogButtonBox.AcceptRole)
            primary_btn.clicked.connect(lambda: (primary_handler(), dlg.accept()))
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)
        layout.addWidget(buttons)
        dlg.exec()

    def show_daily_briefing(self) -> None:
        if not self._gamification_enabled() or not hasattr(self, "gamification"):
            return
        self.gamification.push_activity("Daily Briefing", "Opened today's quest and companion guidance.")
        self._refresh_productivity_hub()
        briefing = self.gamification.daily_briefing()
        companion_hint = self.gamification.companion_hint()
        self.show_status_message(companion_hint, 4200)
        self._show_productivity_info_dialog(
            title="Daily Briefing",
            subtitle=companion_hint,
            sections=[
                ("Today's Briefing", [str(item) for item in briefing]),
                ("Companion Guidance", [companion_hint]),
            ],
            primary_label="Coach Recommendation",
            primary_handler=self.run_coach_recommendation,
        )
        self._onboarding_mark_step("opened_daily_briefing")

    def show_seasonal_event_briefing(self) -> None:
        if not self._gamification_enabled() or not hasattr(self, "gamification"):
            return
        self.gamification.push_activity("Seasonal Event", "Checked the live seasonal event briefing.")
        self._refresh_seasonal_event_state()
        briefing = self.gamification.event_briefing()
        self.show_status_message(briefing[0] if briefing else "No active seasonal event.", 4200)
        self._show_productivity_info_dialog(
            title="Seasonal Event Briefing",
            subtitle="Live event progress and reward tracking.",
            sections=[("Seasonal Event", [str(item) for item in briefing])],
        )
        self._onboarding_mark_step("opened_seasonal_event_briefing")

    def show_session_review(self, *, auto: bool = False) -> None:
        if not self._gamification_enabled() or not hasattr(self, "gamification"):
            return
        review = self.gamification.record_session_review(
            open_tabs=int(self.tab_widget.count()),
            saved_session=bool(str(self.settings.get("last_session_file_path", "") or "").strip()),
        )
        self.gamification.push_activity(
            "Session Review",
            (
                f"{int(review.get('words_written', 0))} words, "
                f"{int(review.get('todo_fixed', 0))} TODOs, "
                f"{int(review.get('focus_sprints_completed', 0))} sprint(s)"
            ),
        )
        self._refresh_productivity_hub()
        summary = (
            f"Session review: {int(review.get('words_written', 0))} words | "
            f"{int(review.get('todo_fixed', 0))} TODOs fixed | "
            f"{int(review.get('focus_sprints_completed', 0))} focus sprint(s)"
        )
        self.show_status_message(summary, 4200)
        self._show_productivity_info_dialog(
            title="Session Review" if not auto else "Quick Session Review",
            subtitle=summary,
            sections=[
                ("Session Summary", [summary]),
                (
                    "Highlights",
                    [
                        f"Words written: {int(review.get('words_written', 0))}",
                        f"TODOs fixed: {int(review.get('todo_fixed', 0))}",
                        f"Focus sprints: {int(review.get('focus_sprints_completed', 0))}",
                        f"Open tabs: {int(review.get('open_tabs', 0) or self.tab_widget.count())}",
                    ],
                ),
            ],
        )
        if not auto:
            self._onboarding_mark_step("opened_session_review")

    def run_coach_recommendation(self) -> None:
        if not self._gamification_enabled() or not hasattr(self, "gamification"):
            return
        recommendation = self.gamification.recommended_action()
        action_id = str(recommendation.get("action_id", "") or "daily_briefing")
        label = str(recommendation.get("label", "") or "Recommended action")
        detail = str(recommendation.get("detail", "") or "Here is the next best action based on your current progress.")

        def _execute() -> None:
            if action_id == "focus_sprint":
                self.start_focus_sprint_mode()
            elif action_id == "workspace_search":
                self.search_workspace()
            elif action_id == "command_palette":
                self.open_command_palette()
            elif action_id == "quick_open":
                self.open_quick_open()
            else:
                self.show_daily_briefing()

        self._show_productivity_info_dialog(
            title="Coach Recommendation",
            subtitle=detail,
            sections=[
                ("Recommended Move", [label, detail]),
                ("Reasoning", [str(recommendation.get("reason", "") or "Based on your recent activity and progress.")]),
            ],
            primary_label="Run Recommendation",
            primary_handler=_execute,
        )
        self._onboarding_mark_step("used_coach_recommendation")

    def run_productivity_routine(self) -> None:
        if not self._gamification_enabled() or not hasattr(self, "gamification"):
            return
        routines = self.gamification.productivity_routines()
        if not routines:
            self.show_daily_briefing()
            return
        routine = routines[0]
        routine_id = str(routine.get("routine_id", "") or "daily_briefing")
        label = str(routine.get("label", "") or "Productivity routine")
        executed = False
        if routine_id == "focus_sprint":
            executed = bool(self.start_focus_sprint_mode())
        elif routine_id == "workspace_search":
            self.search_workspace()
            executed = True
        elif routine_id == "command_palette":
            self.open_command_palette()
            executed = True
        elif routine_id == "bug_hunt":
            executed = bool(self.start_bug_hunt_mode())
        else:
            self.show_daily_briefing()
            executed = True
        if not executed:
            return
        self.gamification.record_routine_run(routine_id)
        self.gamification.push_activity("Routine", label)
        self._refresh_productivity_hub()
        self.show_status_message(label, 3200)
        self._onboarding_mark_step("used_productivity_routine")

    def _unlock_easter_egg(self, title: str, detail: str) -> None:
        if not self._gamification_enabled():
            return
        if not self.gamification.add_achievement(title):
            return
        self.gamification.push_activity(f"Unlocked: {title}", detail)
        self._update_gamification_status_labels()
        self._refresh_productivity_hub()
        toast = getattr(self, "gamification_reward_toast", None)
        if toast is not None:
            toast.show_reward(f"Unlocked: {title}", detail, 3200)
        self.show_status_message(f"Unlocked: {title}", 3200)

    def _evaluate_easter_eggs(self, event_name: str, payload: dict[str, Any] | None = None) -> None:
        if not self._gamification_enabled() or not hasattr(self, "gamification"):
            return
        data = payload or {}
        state = self.gamification.state()
        stats = state.get("stats", {})
        now = datetime.now()
        if event_name == "words_written":
            words = int(data.get("words", 0) or 0)
            if words >= 80:
                self._session_word_bursts += 1
            self.gamification.record_activity_day("writing_days", now)
            if now.hour >= 23 and int(stats.get("words_written", 0) or 0) >= 250:
                self.gamification.set_secret_progress_max("night_owl_sessions", 1)
                self._unlock_easter_egg("Night Owl", "Late-night writing session logged.")
            if self._session_shortcut_count >= 50:
                self._unlock_easter_egg("Keyboard Only", "Fifty shortcut-driven actions in one session.")
        elif event_name == "todo_fixed":
            if int(stats.get("todo_fixed", 0) or 0) >= 25:
                self._unlock_easter_egg("Zero TODO Day", "Twenty-five TODO markers cleaned up.")
        elif event_name == "focus_sprint":
            self.gamification.record_activity_day("focus_days", now)
            if int(stats.get("focus_sprints_completed", 0) or 0) >= 7:
                self._unlock_easter_egg("Focus Beast", "Seven focus sprints completed.")
        elif event_name == "workspace_review":
            self.gamification.record_activity_day("review_days", now)
            if int(stats.get("workspace_reviews", 0) or 0) >= 5:
                self._unlock_easter_egg("Explorer", "Workspace review mastery unlocked.")
        elif event_name == "plugin_used":
            if int(stats.get("plugin_uses", 0) or 0) >= 5:
                self._unlock_easter_egg("Plugin Tinkerer", "Five plugin-powered actions completed.")
        elif event_name == "encryption_enabled":
            encrypted = int(data.get("encrypted_count", 0) or 0)
            self.gamification.set_secret_progress_max("vault_keeper_notes", encrypted)
            if encrypted >= 3:
                self._unlock_easter_egg("Vault Keeper", "Three encrypted-note moments discovered.")
        elif event_name == "shortcut_used":
            self._session_shortcut_count += 1
            self.gamification.set_secret_progress_max("keyboard_shortcuts", self._session_shortcut_count)
            if self._session_shortcut_count >= 50:
                self._unlock_easter_egg("Keyboard Only", "Fifty shortcut-driven actions in one session.")
        self._refresh_productivity_hub()

    @staticmethod
    def _gamification_word_count(text: str) -> int:
        return len([word for word in re.findall(r"\b\w+\b", text or "") if word.strip()])

    @staticmethod
    def _gamification_todo_count(text: str) -> int:
        return len(re.findall(r"TODO", text or "", flags=re.IGNORECASE))

    def _sync_gamification_tab_snapshot(self, tab: Any) -> None:
        if tab is None or not hasattr(tab, "text_edit"):
            return
        try:
            text = str(tab.text_edit.get_text() or "")
        except Exception:
            return
        tab._gamification_prev_text = text
        tab._gamification_prev_word_count = self._gamification_word_count(text)
        tab._gamification_prev_todo_count = self._gamification_todo_count(text)

    def _gamification_on_text_changed(self) -> None:
        if not self._gamification_enabled() or not hasattr(self, "gamification"):
            return
        tab = self.active_tab()
        if tab is None:
            return
        text = str(tab.text_edit.get_text() or "")
        if not hasattr(tab, "_gamification_prev_text"):
            self._sync_gamification_tab_snapshot(tab)
            return
        prev_text = str(getattr(tab, "_gamification_prev_text", "") or "")
        prev_word_count = int(getattr(tab, "_gamification_prev_word_count", self._gamification_word_count(prev_text)))
        prev_todo_count = int(getattr(tab, "_gamification_prev_todo_count", self._gamification_todo_count(prev_text)))
        curr_word_count = self._gamification_word_count(text)
        curr_todo_count = self._gamification_todo_count(text)
        if len(text) < len(prev_text):
            mode = self.gamification.state().get("challenge_modes", {}).get("no_backspace", {})
            if isinstance(mode, dict) and bool(mode.get("active", False)):
                self.gamification.set_challenge_state("no_backspace", False, {"failed": True})
                self.show_status_message("No-backspace challenge failed.", 2500)
        words_added = max(0, curr_word_count - prev_word_count)
        if words_added > 0:
            result, notes = self.gamification.add_written_words(words_added)
            self._show_gamification_progress(result, notes)
            self._evaluate_easter_eggs("words_written", {"words": words_added})
        todo_removed = max(0, prev_todo_count - curr_todo_count)
        if todo_removed > 0:
            result, notes = self.gamification.add_todo_fixed(todo_removed)
            self._show_gamification_progress(result, notes)
            self._evaluate_easter_eggs("todo_fixed", {"count": todo_removed})
        tab._gamification_prev_text = text
        tab._gamification_prev_word_count = curr_word_count
        tab._gamification_prev_todo_count = curr_todo_count

    def open_gamification_dashboard(self) -> None:
        if not self._gamification_enabled():
            QMessageBox.information(self, "Gamification", "Gamification is disabled in settings.")
            return
        self._onboarding_mark_step("opened_gamification_dashboard")
        dlg = GamificationDashboardDialog(self, self.gamification)
        dlg.exec()
        self._maybe_show_contextual_tip("after_gamification_dashboard")

    def start_focus_sprint_mode(self) -> bool:
        if not self._gamification_enabled():
            return False
        minutes, ok = QInputDialog.getInt(self, "Focus Sprint", "Minutes:", value=15, minValue=1, maxValue=120)
        if not ok:
            return False
        self.gamification.set_challenge_state("focus_sprint", True, {"minutes": int(minutes), "started_at": time.time()})
        self._focus_sprint_deadline_ts = time.time() + (int(minutes) * 60)
        self._focus_sprint_timer.start(int(minutes) * 60 * 1000)
        self.show_status_message(f"Focus sprint started: {minutes}m", 2500)
        return True

    def _finish_focus_sprint(self) -> None:
        mode = self.gamification.state().get("challenge_modes", {}).get("focus_sprint", {})
        if not isinstance(mode, dict) or not bool(mode.get("active", False)):
            return
        self.gamification.set_challenge_state("focus_sprint", False, {"completed": True})
        result, notes = self.gamification.mark_focus_sprint_completed()
        self._show_gamification_progress(result, notes)
        self._evaluate_easter_eggs("focus_sprint")

    def toggle_no_backspace_challenge(self) -> None:
        if not self._gamification_enabled():
            return
        state = self.gamification.state().get("challenge_modes", {}).get("no_backspace", {})
        active = bool(isinstance(state, dict) and state.get("active", False))
        next_state = not active
        self.gamification.set_challenge_state("no_backspace", next_state, {"failed": False, "started_at": time.time()})
        self.show_status_message("No-backspace challenge started." if next_state else "No-backspace challenge stopped.", 2500)

    def start_bug_hunt_mode(self) -> bool:
        if not self._gamification_enabled():
            return False
        root = self._workspace_root()
        if not root:
            QMessageBox.information(self, "Bug Hunt", "Set a workspace folder first.")
            return False
        files = self._workspace_files()
        issues = 0
        for path in files[:200]:
            try:
                text = Path(path).read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            issues += len(re.findall(r"TODO|FIXME|BUG", text, flags=re.IGNORECASE))
        self.gamification.set_challenge_state("bug_hunt", True, {"workspace_root": root, "found_markers": issues})
        self.show_status_message(f"Bug hunt mode ready: {issues} marker(s) found.", 3500)
        return True

    def craft_template_tool(self) -> None:
        if not self._gamification_enabled():
            return
        name, ok = QInputDialog.getText(self, "Craft Tool", "Tool name:")
        if not ok or not name.strip():
            return
        components, ok = QInputDialog.getMultiLineText(
            self,
            "Craft Tool",
            "Components (snippet/macro/prompt per line):",
            "snippet:Meeting Notes\nmacro:Trim Trailing Spaces\nprompt:Summarize section",
        )
        if not ok:
            return
        state = self.gamification.state()
        row = {
            "name": name.strip(),
            "components": [line.strip() for line in components.splitlines() if line.strip()],
            "starred": False,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        state["crafted_tools"].append(row)
        self.gamification.award_xp(20, "Crafted template tool", skill_branch="ai_workflow")
        self._update_gamification_status_labels()
        self.show_status_message(f'Crafted tool "{row["name"]}".', 2500)

    def export_crafted_tools_pack(self) -> None:
        if not self._gamification_enabled():
            return
        state = self.gamification.state()
        rows = state.get("crafted_tools", [])
        if not isinstance(rows, list) or not rows:
            QMessageBox.information(self, "Crafted Tools", "No crafted tools to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Crafted Tools Pack", "crafted_tools.pluginpack.json", "JSON (*.json)")
        if not path:
            return
        payload = {
            "pack_type": "pypad-crafted-tools",
            "version": 1,
            "tools": rows,
        }
        try:
            Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:
            QMessageBox.warning(self, "Crafted Tools", f"Failed to export pack:\n{exc}")
            return
        self.show_status_message(f"Crafted tool pack exported: {path}", 3000)

    def mark_plugin_feature_used(self) -> None:
        if not self._gamification_enabled():
            return
        result, notes = self.gamification.mark_plugin_used()
        self._show_gamification_progress(result, notes)
        self._evaluate_easter_eggs("plugin_used")

    def enable_note_encryption(self) -> None:
        self.security_controller.enable_note_encryption()
        encrypted_count = 0
        for index in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(index)
            if isinstance(tab, EditorTab) and bool(getattr(tab, "encryption_enabled", False)):
                encrypted_count += 1
        self._evaluate_easter_eggs("encryption_enabled", {"encrypted_count": encrypted_count})

    def disable_note_encryption(self) -> None:
        self.security_controller.disable_note_encryption()

    def change_note_password(self) -> None:
        self.security_controller.change_note_password()

    def insert_media_files(self) -> None:
        self.workspace_controller.insert_media_files()

    def _insert_media_paths(self, paths: list[str]) -> None:
        self.workspace_controller.insert_media_paths(paths)

    def open_workspace_folder(self) -> None:
        self.workspace_controller.open_workspace_folder()

    def _workspace_profiles(self) -> dict[str, dict[str, object]]:
        raw = self.settings.get("workspace_profiles", {})
        if not isinstance(raw, dict):
            return {}
        cleaned: dict[str, dict[str, object]] = {}
        for key, value in raw.items():
            name = str(key).strip()
            if not name or not isinstance(value, dict):
                continue
            root = str(value.get("root", "") or "").strip()
            if not root:
                continue
            cleaned[name] = {
                "root": root,
                "restore_session": bool(value.get("restore_session", True)),
            }
        return cleaned

    def save_workspace_profile(self) -> None:
        root = self._workspace_root()
        if not root:
            QMessageBox.information(self, "Workspace Profile", "Set a workspace folder first.")
            return
        profiles = self._workspace_profiles()
        suggested = str(self.settings.get("workspace_startup_last_profile", "") or "").strip() or Path(root).name or "Workspace"
        name, ok = QInputDialog.getText(self, "Save Workspace Profile", "Profile name:", text=suggested)
        if not ok or not name.strip():
            return
        profile_name = name.strip()
        restore = QMessageBox.question(
            self,
            "Save Workspace Profile",
            "Restore last session when this profile is selected?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        profiles[profile_name] = {
            "root": root,
            "restore_session": restore == QMessageBox.Yes,
        }
        self.settings["workspace_profiles"] = profiles
        self.settings["workspace_startup_last_profile"] = profile_name
        self.save_settings_to_disk()
        self.show_status_message(f'Workspace profile saved: "{profile_name}"', 2500)

    def load_workspace_profile(self) -> None:
        profiles = self._workspace_profiles()
        if not profiles:
            QMessageBox.information(self, "Workspace Profile", "No workspace profiles saved yet.")
            return
        names = sorted(profiles.keys(), key=str.lower)
        current = str(self.settings.get("workspace_startup_last_profile", "") or "").strip()
        default_idx = names.index(current) if current in names else 0
        chosen, ok = QInputDialog.getItem(self, "Load Workspace Profile", "Profile:", names, default_idx, False)
        if not ok or not chosen:
            return
        profile = profiles.get(chosen, {})
        root = str(profile.get("root", "") or "").strip()
        if not root or not Path(root).exists():
            QMessageBox.warning(self, "Workspace Profile", f"Workspace path not found:\n{root}")
            return
        self.settings["workspace_root"] = root
        self.settings["workspace_startup_last_profile"] = chosen
        self.save_settings_to_disk()
        if hasattr(self, "_refresh_workspace_dock"):
            self._refresh_workspace_dock()
        self.show_status_message(f"Workspace: {root}", 3000)
        if bool(profile.get("restore_session", True)):
            self.restore_last_session()

    def toggle_workspace_startup_picker(self, checked: bool) -> None:
        self.settings["workspace_startup_picker_enabled"] = bool(checked)
        self.save_settings_to_disk()
        self.show_status_message(
            "Workspace startup picker enabled." if checked else "Workspace startup picker disabled.",
            2200,
        )

    def apply_workspace_profile_on_startup(self) -> bool:
        if not bool(self.settings.get("workspace_startup_picker_enabled", False)):
            return False
        profiles = self._workspace_profiles()
        if not profiles:
            return False
        names = sorted(profiles.keys(), key=str.lower)
        last_name = str(self.settings.get("workspace_startup_last_profile", "") or "").strip()
        default_idx = names.index(last_name) if last_name in names else 0
        chosen, ok = QInputDialog.getItem(self, "Workspace Profile", "Select startup profile:", names, default_idx, False)
        if not ok or not chosen:
            return False
        profile = profiles.get(chosen, {})
        root = str(profile.get("root", "") or "").strip()
        if root and Path(root).exists():
            self.settings["workspace_root"] = root
            if hasattr(self, "_refresh_workspace_dock"):
                self._refresh_workspace_dock()
            self.show_status_message(f"Workspace: {root}", 3000)
        self.settings["workspace_startup_last_profile"] = chosen
        self.save_settings_to_disk()
        if bool(profile.get("restore_session", True)):
            self.restore_last_session()
        return True

    def _workspace_root(self) -> str | None:
        return self.workspace_controller.workspace_root()

    def _workspace_files(self) -> list[str]:
        return self.workspace_controller.workspace_files()

    def show_workspace_files(self) -> None:
        self.workspace_controller.show_workspace_files()

    def search_workspace(self) -> None:
        self.workspace_controller.search_workspace()

    def replace_in_files(self) -> None:
        self.workspace_controller.replace_in_files()

    def start_macro_recording(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        self.macro_recording = True
        self._macro_events = []
        self.show_status_message("Macro recording started", 3000)
        self.update_action_states()

    def stop_macro_recording(self) -> None:
        if not self.macro_recording:
            return
        self.macro_recording = False
        self._last_macro_events = list(self._macro_events)
        self._macro_events = []
        self.show_status_message(
            f"Macro recording stopped ({len(self._last_macro_events)} event(s))",
            3000,
        )
        self.update_action_states()

    def play_macro(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        events = list(getattr(self, "_last_macro_events", []))
        if not events:
            QMessageBox.information(self, "Playback Macro", "No recorded macro to replay.")
            return
        if tab.text_edit.is_read_only():
            QMessageBox.information(self, "Playback Macro", "Current tab is read-only.")
            return
        if self.macro_recording:
            self.stop_macro_recording()

        self.macro_playing = True
        try:
            self._apply_macro_events(tab, events)
            self.show_status_message("Macro playback completed", 3000)
        finally:
            self.macro_playing = False
            self.update_action_states()

    def _apply_macro_events(self, tab: EditorTab, events: list[tuple[str, str]]) -> None:
        for op, value in events:
            if op == "text":
                tab.text_edit.insert_text(value)
            elif op == "backspace":
                tab.text_edit.delete_backspace()
            elif op == "delete":
                tab.text_edit.delete_delete()

    def _normalized_saved_macros(self) -> dict[str, dict[str, Any]]:
        raw = self.settings.get("saved_macros", {})
        cleaned: dict[str, dict[str, Any]] = {}
        if not isinstance(raw, dict):
            return cleaned
        for key, entry in raw.items():
            name = str(key).strip()
            if not name or not isinstance(entry, dict):
                continue
            raw_events = entry.get("events", [])
            events: list[list[str]] = []
            if isinstance(raw_events, list):
                for item in raw_events:
                    if not isinstance(item, (list, tuple)) or len(item) != 2:
                        continue
                    op = str(item[0]).strip().lower()
                    value = str(item[1])
                    if op in {"text", "backspace", "delete"}:
                        events.append([op, value])
            if not events:
                continue
            shortcut = str(entry.get("shortcut", "") or "").strip()
            cleaned[name] = {"events": events, "shortcut": shortcut}
        return cleaned

    def _macro_events_from_saved_entry(self, entry: dict[str, Any]) -> list[tuple[str, str]]:
        raw_events = entry.get("events", [])
        parsed: list[tuple[str, str]] = []
        if not isinstance(raw_events, list):
            return parsed
        for item in raw_events:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                continue
            op = str(item[0]).strip().lower()
            value = str(item[1])
            if op in {"text", "backspace", "delete"}:
                parsed.append((op, value))
        return parsed

    def _save_saved_macros(self, macros: dict[str, dict[str, Any]]) -> None:
        self.settings["saved_macros"] = macros
        self.save_settings_to_disk()
        self._sync_saved_macro_actions()
        self.update_action_states()

    def _sync_saved_macro_actions(self) -> None:
        menu = getattr(self, "macros_menu", None)
        if menu is None:
            return
        for action in getattr(self, "_saved_macro_menu_actions", []):
            menu.removeAction(action)
        separator = getattr(self, "_saved_macro_menu_separator", None)
        if separator is not None:
            menu.removeAction(separator)
        self._saved_macro_menu_actions = []
        self._saved_macro_menu_separator = None

        saved = self._normalized_saved_macros()
        if not saved:
            return

        self._saved_macro_menu_separator = menu.addSeparator()
        for name in sorted(saved.keys(), key=str.lower):
            action = QAction(name, self)
            shortcut = str(saved[name].get("shortcut", "") or "").strip()
            if shortcut:
                seq = QKeySequence(shortcut)
                if not seq.isEmpty():
                    action.setShortcut(seq)
            action.triggered.connect(lambda _checked=False, macro_name=name: self.run_saved_macro(macro_name))
            menu.addAction(action)
            self._saved_macro_menu_actions.append(action)

    def save_current_recorded_macro(self) -> None:
        if self.macro_recording:
            self.stop_macro_recording()
        events = list(getattr(self, "_last_macro_events", []))
        if not events:
            QMessageBox.information(self, "Save Macro", "No recorded macro to save.")
            return
        saved = self._normalized_saved_macros()
        default_name = f"Macro {len(saved) + 1}"
        name, ok = QInputDialog.getText(self, "Save Current Recorded Macro", "Macro name:", text=default_name)
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        if name in saved:
            ret = QMessageBox.question(
                self,
                "Save Current Recorded Macro",
                f'A macro named "{name}" already exists. Overwrite it?',
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                return
        existing_shortcut = str(saved.get(name, {}).get("shortcut", "") or "")
        shortcut, ok = QInputDialog.getText(
            self,
            "Macro Shortcut",
            "Shortcut (optional):",
            text=existing_shortcut,
        )
        if not ok:
            return
        shortcut = shortcut.strip()
        if shortcut:
            seq = QKeySequence(shortcut)
            if seq.isEmpty():
                QMessageBox.warning(self, "Save Macro", "Invalid shortcut format.")
                return
            shortcut = seq.toString(QKeySequence.SequenceFormat.PortableText)

        saved[name] = {
            "events": [[str(op), str(value)] for op, value in events],
            "shortcut": shortcut,
        }
        self._save_saved_macros(saved)
        self.show_status_message(f'Saved macro "{name}".', 3000)

    def _macro_run_options(self) -> list[tuple[str, str, list[tuple[str, str]]]]:
        options: list[tuple[str, str, list[tuple[str, str]]]] = []
        events = list(getattr(self, "_last_macro_events", []))
        if events:
            options.append(("Current Recorded Macro", "events", events))
        saved = self._normalized_saved_macros()
        for name in sorted(saved.keys(), key=str.lower):
            parsed = self._macro_events_from_saved_entry(saved[name])
            if parsed:
                options.append((name, "events", parsed))
        options.append(("Trim Trailing Space and Save", "trim_save", []))
        return options

    def _execute_macro_mode(
        self,
        tab: EditorTab,
        mode: str,
        events: list[tuple[str, str]],
        *,
        repeat_count: int,
        until_end: bool,
    ) -> tuple[bool, int]:
        if mode == "trim_save":
            self.trim_trailing_spaces_and_save()
            return True, 1

        if not events:
            return False, 0

        runs = 0
        if until_end:
            max_loops = 50000
            while runs < max_loops:
                before = tab.text_edit.get_text()
                at_end_before = tab.text_edit.widget.textCursor().atEnd()
                if at_end_before:
                    break
                self._apply_macro_events(tab, events)
                runs += 1
                after = tab.text_edit.get_text()
                at_end_after = tab.text_edit.widget.textCursor().atEnd()
                if after == before:
                    break
                if at_end_after:
                    break
            return True, runs

        for _ in range(max(1, repeat_count)):
            self._apply_macro_events(tab, events)
            runs += 1
        return True, runs

    def run_macro_multiple_times(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        if tab.text_edit.is_read_only():
            QMessageBox.information(self, "Run Macro", "Current tab is read-only.")
            return
        options = self._macro_run_options()
        if not options:
            QMessageBox.information(self, "Run Macro", "No macro is available to run.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Run a Macro Multiple Times")
        dialog.setModal(True)
        apply_dialog_theme_from_window(self, dialog)

        root = QVBoxLayout(dialog)
        macro_group = QGroupBox("Macro to run", dialog)
        macro_layout = QVBoxLayout(macro_group)
        macro_combo = QComboBox(macro_group)
        for label, mode, events in options:
            macro_combo.addItem(label, (mode, events))
        trim_index = macro_combo.findText("Trim Trailing Space and Save")
        if trim_index >= 0:
            macro_combo.setCurrentIndex(trim_index)
        macro_layout.addWidget(macro_combo)
        root.addWidget(macro_group)

        count_row = QHBoxLayout()
        run_radio = QRadioButton("Run", dialog)
        run_radio.setChecked(True)
        count_spin = QSpinBox(dialog)
        count_spin.setRange(1, 100000)
        count_spin.setValue(1)
        times_label = QLabel("times", dialog)
        count_row.addWidget(run_radio)
        count_row.addWidget(count_spin)
        count_row.addWidget(times_label)
        count_row.addStretch(1)
        root.addLayout(count_row)

        until_eof_radio = QRadioButton("Run until the end of file", dialog)
        root.addWidget(until_eof_radio)

        def _sync_repeat_controls() -> None:
            enabled = run_radio.isChecked()
            count_spin.setEnabled(enabled)
            times_label.setEnabled(enabled)

        run_radio.toggled.connect(_sync_repeat_controls)
        _sync_repeat_controls()

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        run_btn = QPushButton("Run", dialog)
        cancel_btn = QPushButton("Cancel", dialog)
        run_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addWidget(run_btn)
        buttons.addWidget(cancel_btn)
        root.addLayout(buttons)

        if dialog.exec() != QDialog.Accepted:
            return

        selected = macro_combo.currentData()
        if not isinstance(selected, tuple) or len(selected) != 2:
            return
        mode = str(selected[0])
        selected_events = selected[1] if isinstance(selected[1], list) else []

        if self.macro_recording:
            self.stop_macro_recording()
        self.macro_playing = True
        try:
            ok, runs = self._execute_macro_mode(
                tab,
                mode,
                selected_events,
                repeat_count=int(count_spin.value()),
                until_end=until_eof_radio.isChecked(),
            )
            if ok:
                self.show_status_message(f"Macro playback completed ({runs} run(s)).", 3000)
        finally:
            self.macro_playing = False
            self.update_action_states()

    def trim_trailing_spaces_and_save(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        if tab.text_edit.is_read_only():
            QMessageBox.information(self, "Trim Trailing Spaces and Save", "Current tab is read-only.")
            return
        text = tab.text_edit.get_text()
        lines = text.splitlines()
        trimmed_lines = [re.sub(r"[ \t]+$", "", line) for line in lines]
        changed_count = sum(1 for old, new in zip(lines, trimmed_lines) if old != new)
        eol = "\r\n" if str(tab.eol_mode or "LF").upper() == "CRLF" else "\n"
        had_trailing_newline = text.endswith(("\r\n", "\n", "\r"))
        trimmed = eol.join(trimmed_lines)
        if lines and had_trailing_newline:
            trimmed += eol
        if trimmed != text:
            tab.text_edit.set_text(trimmed)
            tab.text_edit.set_modified(True)
        if self.file_save_tab(tab):
            self.show_status_message(f"Trimmed trailing spaces on {changed_count} line(s) and saved.", 3000)

    def run_saved_macro(self, macro_name: str) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        if tab.text_edit.is_read_only():
            QMessageBox.information(self, "Run Saved Macro", "Current tab is read-only.")
            return
        saved = self._normalized_saved_macros()
        entry = saved.get(macro_name)
        if not entry:
            QMessageBox.information(self, "Run Saved Macro", f'No saved macro named "{macro_name}".')
            return
        events = self._macro_events_from_saved_entry(entry)
        if not events:
            QMessageBox.information(self, "Run Saved Macro", "Saved macro has no executable events.")
            return
        if self.macro_recording:
            self.stop_macro_recording()
        self.macro_playing = True
        try:
            self._apply_macro_events(tab, events)
            self.show_status_message(f'Ran saved macro "{macro_name}".', 3000)
        finally:
            self.macro_playing = False
            self.update_action_states()

    def modify_macro_shortcut_or_delete(self) -> None:
        saved = self._normalized_saved_macros()
        if not saved:
            QMessageBox.information(self, "Modify Shortcut/Delete Macro", "No saved macros found.")
            return
        names = sorted(saved.keys(), key=str.lower)
        name, ok = QInputDialog.getItem(self, "Modify Shortcut/Delete Macro", "Macro:", names, 0, False)
        if not ok or not name:
            return
        options = ["Modify shortcut", "Delete macro"]
        choice, ok = QInputDialog.getItem(self, "Modify Shortcut/Delete Macro", "Action:", options, 0, False)
        if not ok or not choice:
            return

        if choice == "Delete macro":
            ret = QMessageBox.question(
                self,
                "Delete Macro",
                f'Delete macro "{name}"?',
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                return
            saved.pop(name, None)
            self._save_saved_macros(saved)
            self.show_status_message(f'Deleted macro "{name}".', 3000)
            return

        current_shortcut = str(saved.get(name, {}).get("shortcut", "") or "")
        shortcut, ok = QInputDialog.getText(
            self,
            "Modify Shortcut",
            f'Shortcut for "{name}" (leave empty to clear):',
            text=current_shortcut,
        )
        if not ok:
            return
        shortcut = shortcut.strip()
        if shortcut:
            seq = QKeySequence(shortcut)
            if seq.isEmpty():
                QMessageBox.warning(self, "Modify Shortcut", "Invalid shortcut format.")
                return
            shortcut = seq.toString(QKeySequence.SequenceFormat.PortableText)
        saved[name]["shortcut"] = shortcut
        self._save_saved_macros(saved)
        self.show_status_message(f'Updated shortcut for "{name}".', 3000)

    def ask_ai(self) -> None:
        self.ai_controller.ask_ai()

    def _open_ai_chat_panel(self) -> bool:
        if hasattr(self, "toggle_ai_chat_panel"):
            self.toggle_ai_chat_panel(True)
        return bool(hasattr(self, "ai_chat_dock") and self.ai_chat_dock is not None)

    def _send_ai_chat_prompt(self, *, prompt: str, visible_prompt: str | None = None, on_done=None) -> bool:
        if not self._open_ai_chat_panel():
            return False
        self.ai_chat_dock.send_prompt(prompt=prompt, visible_prompt=visible_prompt, on_done=on_done)
        return True

    def _log_ai_feature(self, message: str) -> None:
        if not bool(self.settings.get("ai_verbose_logging", False)):
            return
        logger = getattr(self, "log_event", None)
        if callable(logger):
            logger("Info", f"[AI Feature] {message}")

    def _with_ai_chat_dock(self):
        if not self._open_ai_chat_panel():
            QMessageBox.information(self, "AI Chat", "AI Chat panel is not available.")
            return None
        return getattr(self, "ai_chat_dock", None)

    def _ensure_ai_chat_apply_signal_connected(self) -> None:
        dock = self._with_ai_chat_dock()
        if dock is None:
            return
        if bool(getattr(self, "_ai_batch_apply_signal_connected", False)):
            return
        sig = getattr(dock, "apply_completed", None)
        if sig is None:
            return
        try:
            sig.connect(self._on_ai_chat_apply_completed)
            self._ai_batch_apply_signal_connected = True
            self._log_ai_feature("connected ai_chat_dock.apply_completed signal")
        except Exception as exc:
            self._log_ai_feature(f"failed to connect ai_chat_dock.apply_completed signal: {exc!r}")

    def _on_ai_chat_apply_completed(self, kind: str, success: bool, detail: str) -> None:
        self._log_ai_feature(f"apply_completed signal kind={kind!r} success={success} detail={detail!r}")
        state = getattr(self, "_ai_batch_refactor_state", None)
        if not isinstance(state, dict):
            return
        if not bool(state.get("active", False)):
            return
        kind_s = str(kind or "")
        if kind_s not in {"set_file", "patch"}:
            return
        if not bool(state.get("awaiting_apply", False)):
            return
        if not bool(success):
            if str(detail or "") == "declined":
                state["active"] = False
                state["awaiting_apply"] = False
                self.show_status_message("Batch AI refactor queue canceled after declined apply.", 4500)
                self._log_ai_feature("batch refactor queue canceled by explicit no/decline")
            return
        rows = state.get("rows", [])
        instruction = str(state.get("instruction", "") or "")
        idx = int(state.get("index", 0) or 0)
        if not isinstance(rows, list):
            return
        state["awaiting_apply"] = False
        next_idx = idx + 1
        if next_idx >= len(rows):
            self.show_status_message("Batch AI refactor queue finished.", 5000)
            state["active"] = False
            self._log_ai_feature("batch refactor queue finished after apply confirmation")
            return
        current_path = str(state.get("path", "") or "")
        ans = QMessageBox.question(
            self,
            "Batch Refactor",
            (
                f"Applied AI result for:\n{current_path}\n\n"
                "Continue to the next file in the batch?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if ans == QMessageBox.Yes:
            self._log_ai_feature(f"batch refactor continuing to index={next_idx}")
            self._run_batch_refactor_queue(rows, instruction, next_idx)
            return
        state["active"] = False
        self._log_ai_feature("batch refactor paused/stopped by user after apply")

    def ai_attach_current_file_to_chat(self) -> None:
        dock = self._with_ai_chat_dock()
        if dock is not None and hasattr(dock, "_attach_current_file_to_chat"):
            dock._attach_current_file_to_chat()

    def ai_attach_selection_to_chat(self) -> None:
        dock = self._with_ai_chat_dock()
        if dock is not None and hasattr(dock, "_attach_selection_to_chat"):
            dock._attach_selection_to_chat()

    def ai_attach_workspace_search_to_chat(self) -> None:
        dock = self._with_ai_chat_dock()
        if dock is not None and hasattr(dock, "_attach_workspace_search_results_to_chat"):
            dock._attach_workspace_search_results_to_chat()

    @staticmethod
    def _ai_set_file_command_instructions() -> str:
        return (
            "Return a short visible summary first, then emit the hidden full-file replace command outside code fences exactly in this format:\n"
            "[PYPAD_CMD_SET_FILE_BEGIN]\n"
            "base64:<UTF-8 full file text encoded in base64>\n"
            "[PYPAD_CMD_SET_FILE_END]\n"
            "Then ask: Should I replace your current tab with this result?"
        )

    def _ai_regression_guard_block(self) -> str:
        if not bool(self.settings.get("ai_enable_regression_guard_prompts", True)):
            return ""
        return (
            "Regression guard requirements:\n"
            "- Preserve unrelated code/content exactly.\n"
            "- Preserve imports/usings unless required by the requested change.\n"
            "- Preserve existing formatting/style unless the user asked to reformat.\n"
            "- Return only the requested output format plus hidden command blocks when requested.\n"
            "- Do not place commentary inside hidden command payloads.\n"
            "- If the request is ambiguous, ask a clarifying question instead of broad rewrites."
        )

    def _send_ai_file_replace_request(
        self,
        *,
        action_label: str,
        user_visible_prompt: str,
        task_instructions: str,
        file_text: str,
        extra_context: str = "",
        on_done=None,
    ) -> None:
        tab = self.active_tab()
        if tab is None:
            QMessageBox.information(self, action_label, "Open a tab first.")
            return
        if tab.text_edit.is_read_only():
            QMessageBox.information(self, action_label, "Current tab is read-only.")
            return
        file_name = str(tab.current_file or "Untitled")
        prompt = "\n\n".join(
            part
            for part in [
                "You are editing the current file in PyPad.",
                "Produce the updated full file contents (not a patch).",
                self._ai_regression_guard_block(),
                self._ai_set_file_command_instructions(),
                f"Action: {action_label}",
                f"File: {file_name}",
                extra_context.strip(),
                f"Task:\n{task_instructions.strip()}",
                "Current file contents:",
                file_text,
            ]
            if str(part or "").strip()
        )
        self._send_ai_chat_prompt(prompt=prompt, visible_prompt=user_visible_prompt, on_done=on_done)

    def _capture_clipboard_history(self) -> None:
        clip = QApplication.clipboard()
        if clip is None:
            return
        text = (clip.text() or "").strip()
        if not text:
            return
        history = getattr(self, "_clipboard_history", None)
        if not isinstance(history, list):
            history = []
        if history and history[0] == text:
            return
        history.insert(0, text)
        self._clipboard_history = history[:100]

    def show_clipboard_history(self) -> None:
        history = getattr(self, "_clipboard_history", [])
        if not isinstance(history, list):
            history = []
        dlg = QDialog(self)
        dlg.setWindowTitle("Clipboard History")
        dlg.resize(760, 420)
        apply_dialog_theme_from_window(self, dlg)
        lay = QVBoxLayout(dlg)
        table = QTableWidget(dlg)
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["#", "Text"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setRowCount(len(history))
        for idx, value in enumerate(history):
            table.setItem(idx, 0, QTableWidgetItem(str(idx + 1)))
            preview = value if len(value) <= 500 else (value[:497] + "...")
            table.setItem(idx, 1, QTableWidgetItem(preview))
        table.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(table, 1)
        buttons = QDialogButtonBox(dlg)
        paste_btn = buttons.addButton("Paste Selected", QDialogButtonBox.AcceptRole)
        copy_btn = buttons.addButton("Copy Selected", QDialogButtonBox.ActionRole)
        clear_btn = buttons.addButton("Clear History", QDialogButtonBox.DestructiveRole)
        close_btn = buttons.addButton(QDialogButtonBox.Close)
        lay.addWidget(buttons)

        def _selected_text() -> str:
            row = table.currentRow()
            if row < 0 or row >= len(history):
                return ""
            return str(history[row])

        def _paste() -> None:
            text = _selected_text()
            if not text:
                return
            tab = self.active_tab()
            if tab is None or tab.text_edit.is_read_only():
                return
            tab.text_edit.insert_text(text)
            dlg.accept()

        def _copy() -> None:
            text = _selected_text()
            if text:
                QApplication.clipboard().setText(text)

        def _clear() -> None:
            self._clipboard_history = []
            table.setRowCount(0)

        paste_btn.clicked.connect(_paste)
        copy_btn.clicked.connect(_copy)
        clear_btn.clicked.connect(_clear)
        close_btn.clicked.connect(dlg.reject)
        dlg.exec()

    def _set_breadcrumb_text(self, text: str) -> None:
        if hasattr(self, "breadcrumb_label") and self.breadcrumb_label is not None:
            self.breadcrumb_label.setText(text)

    def open_plugin_manager(self) -> None:
        self.advanced_features.open_plugin_manager()

    def open_online_plugins(self) -> None:
        self.advanced_features.open_online_plugins()

    def open_plugins_folder(self) -> None:
        plugins_dir = Path(getattr(self.advanced_features.plugin_host, "plugins_dir", Path(__file__).resolve().parents[4] / "plugins"))
        plugins_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(plugins_dir))  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Open Plugins Folder", f"Could not open folder:\n{exc}")

    def open_mime_tools(self) -> None:
        tab = self.active_tab()
        if tab is None:
            QMessageBox.information(self, "MIME Tools", "Open a tab first.")
            return
        source = tab.text_edit.selected_text() or tab.text_edit.get_text()
        if not source:
            QMessageBox.information(self, "MIME Tools", "Nothing to process.")
            return
        options = [
            "Base64 Encode",
            "Base64 Decode",
            "URL Encode",
            "URL Decode",
            "Hex Encode",
            "Hex Decode",
        ]
        choice, ok = QInputDialog.getItem(self, "MIME Tools", "Operation:", options, 0, False)
        if not ok or not choice:
            return
        try:
            if choice == "Base64 Encode":
                result = base64.b64encode(source.encode("utf-8")).decode("ascii")
            elif choice == "Base64 Decode":
                result = base64.b64decode(source.encode("ascii"), validate=False).decode("utf-8", errors="replace")
            elif choice == "URL Encode":
                result = url_quote(source)
            elif choice == "URL Decode":
                result = url_unquote(source)
            elif choice == "Hex Encode":
                result = source.encode("utf-8").hex()
            else:  # Hex Decode
                result = bytes.fromhex(source.strip()).decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "MIME Tools", f"Conversion failed:\n{exc}")
            return
        if tab.text_edit.has_selection():
            tab.text_edit.replace_selection(result)
        else:
            tab.text_edit.set_text(result)
            tab.text_edit.set_modified(True)
        self.show_status_message("MIME tools conversion applied.", 2500)

    def open_converter_tools(self) -> None:
        tab = self.active_tab()
        if tab is None:
            QMessageBox.information(self, "Converter", "Open a tab first.")
            return
        source = tab.text_edit.selected_text() or tab.text_edit.get_text()
        if not source:
            QMessageBox.information(self, "Converter", "Nothing to convert.")
            return
        options = [
            "UPPERCASE",
            "lowercase",
            "Title Case",
            "Indent JSON (Pretty)",
            "Compact JSON",
            "Convert EOL to LF",
            "Convert EOL to CRLF",
        ]
        choice, ok = QInputDialog.getItem(self, "Converter", "Operation:", options, 0, False)
        if not ok or not choice:
            return
        try:
            if choice == "UPPERCASE":
                result = source.upper()
            elif choice == "lowercase":
                result = source.lower()
            elif choice == "Title Case":
                result = source.title()
            elif choice == "Indent JSON (Pretty)":
                result = json.dumps(json.loads(source), indent=2, ensure_ascii=False)
            elif choice == "Compact JSON":
                result = json.dumps(json.loads(source), separators=(",", ":"), ensure_ascii=False)
            elif choice == "Convert EOL to LF":
                result = source.replace("\r\n", "\n").replace("\r", "\n")
            else:  # Convert EOL to CRLF
                result = source.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Converter", f"Conversion failed:\n{exc}")
            return
        if tab.text_edit.has_selection():
            tab.text_edit.replace_selection(result)
        else:
            tab.text_edit.set_text(result)
            tab.text_edit.set_modified(True)
        self.show_status_message("Converter operation applied.", 2500)

    def open_npp_export_tools(self) -> None:
        tab = self.active_tab()
        if tab is None:
            QMessageBox.information(self, "NPP Export", "Open a tab first.")
            return
        text = tab.text_edit.get_text()
        if not text:
            QMessageBox.information(self, "NPP Export", "Nothing to export.")
            return
        options = [
            "Export as HTML (with line numbers)",
            "Copy HTML to Clipboard",
            "Export as TXT (line numbers)",
        ]
        choice, ok = QInputDialog.getItem(self, "NPP Export", "Export mode:", options, 0, False)
        if not ok or not choice:
            return

        lines = text.splitlines()
        html_lines = "\n".join(
            f'<span style="color:#888">{i + 1:4d}</span>  {html_escape(line)}'
            for i, line in enumerate(lines)
        )
        html_doc = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<style>body{font-family:Consolas,monospace;background:#fff;color:#111;white-space:pre;}</style>"
            "</head><body>"
            f"{html_lines}"
            "</body></html>"
        )
        txt_num = "\n".join(f"{i + 1:4d}  {line}" for i, line in enumerate(lines))

        if choice == "Copy HTML to Clipboard":
            QApplication.clipboard().setText(html_doc)
            self.show_status_message("HTML copied to clipboard.", 2500)
            return

        if choice == "Export as HTML (with line numbers)":
            default_name = (Path(tab.current_file).stem if tab.current_file else "note") + "_npp_export.html"
            path, _ = QFileDialog.getSaveFileName(self, "NPP Export HTML", default_name, "HTML Files (*.html)")
            if not path:
                return
            try:
                Path(path).write_text(html_doc, encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "NPP Export", f"Export failed:\n{exc}")
                return
            self.show_status_message(f"NPP HTML export saved: {path}", 3000)
            return

        default_name = (Path(tab.current_file).stem if tab.current_file else "note") + "_npp_export.txt"
        path, _ = QFileDialog.getSaveFileName(self, "NPP Export TXT", default_name, "Text Files (*.txt)")
        if not path:
            return
        try:
            Path(path).write_text(txt_num, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "NPP Export", f"Export failed:\n{exc}")
            return
        self.show_status_message(f"NPP TXT export saved: {path}", 3000)

    def toggle_minimap_panel(self, checked: bool) -> None:
        self.advanced_features.toggle_minimap(checked)

    def toggle_symbol_outline_panel(self, checked: bool) -> None:
        self.advanced_features.toggle_outline(checked)

    def goto_definition_basic(self) -> None:
        self.advanced_features.go_to_definition()

    def open_side_by_side_diff(self) -> None:
        self.advanced_features.open_diff()

    def open_three_way_merge(self) -> None:
        self.advanced_features.open_merge_helper()

    def apply_patch_file_to_active_tab(self) -> None:
        self.advanced_features.apply_patch_file_to_active()

    def load_full_large_file(self) -> None:
        self.load_full_large_file_current_tab()

    def open_snippet_engine(self) -> None:
        self.advanced_features.open_snippets()

    def install_template_packs(self) -> None:
        self.advanced_features.ensure_template_packs()

    def show_task_workflow_panel(self) -> None:
        self.advanced_features.show_tasks()

    def configure_backup_scheduler(self) -> None:
        self.advanced_features.configure_backup()

    def run_backup_now(self) -> None:
        self.advanced_features.backup_now()

    def export_diagnostics_bundle(self) -> None:
        self.advanced_features.export_diagnostics()

    def toggle_keyboard_only_mode(self, checked: bool) -> None:
        self.advanced_features.toggle_keyboard_only(checked)

    def apply_accessibility_high_contrast(self) -> None:
        self.advanced_features.apply_accessibility_high_contrast()

    def apply_accessibility_dyslexic_font(self) -> None:
        self.advanced_features.apply_accessibility_dyslexic()

    def open_lan_collaboration(self) -> None:
        self.advanced_features.open_collaboration()

    def open_annotation_layer(self) -> None:
        self.advanced_features.open_annotations()

    def _sync_quiz_controls(self) -> None:
        tab = self.active_tab()
        enabled = bool(tab and getattr(tab, "quiz_mode_enabled", False))
        if hasattr(self, "quiz_quit_button"):
            self.quiz_quit_button.setVisible(enabled)
        if hasattr(self, "quiz_finish_button"):
            self.quiz_finish_button.setVisible(enabled)
        if hasattr(self, "quiz_action"):
            self.quiz_action.setText("Restart Quiz" if enabled else "Quiz Mode")

    def show_quiz_format_help(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Quiz Format Help")
        root = QVBoxLayout(dlg)
        root.addWidget(
            QLabel(
                "Accepted formats (v1): MCQ, True/False, and Short Answer.\n"
                "You can mix these in one document.",
                dlg,
            )
        )
        details = QTextEdit(dlg)
        details.setReadOnly(True)
        details.setPlainText(
            "1) Multiple Choice (MCQ)\n"
            "- Question can start with: 1.  / Q1: / -\n"
            "- Options can be: A. / B. / C. ... or A) / B)\n"
            "- Answer metadata accepted:\n"
            "  {answer:A}\n"
            "  [answer=B]\n"
            "  (correct: C)\n\n"
            "Example:\n"
            "1. What is the capital of France? {answer:B}\n"
            "A. Berlin\n"
            "B. Paris\n"
            "C. Rome\n\n"
            "2) True / False\n"
            "- Accepted tokens (case-insensitive): T / F / True / False\n"
            "- Metadata accepted:\n"
            "  {answer:true}\n"
            "  [answer=F]\n"
            "  (correct: T)\n"
            "- Options may be explicit or implicit.\n\n"
            "Example:\n"
            "Q2: The sky is blue. [answer=true]\n"
            "A) True\n"
            "B) False\n\n"
            "3) Short Answer\n"
            "- Single exact answer:\n"
            "  {answer:photosynthesis}\n"
            "- Keyword grading (partial credit):\n"
            "  {keywords: chlorophyll|sunlight|glucose}\n\n"
            "User anchor (optional):\n"
            "- Place {user} or [user] where answer should be typed.\n"
            "- Can be above or below the question text.\n\n"
            "Anchor examples:\n"
            "{user}\n"
            "Q3: Explain photosynthesis {keywords: chlorophyll|sunlight|glucose}\n\n"
            "Q4: Define inertia {answer:resistance to change in motion}\n"
            "[user]\n\n"
            "Example:\n"
            "- Explain photosynthesis {keywords: chlorophyll|sunlight|glucose}\n\n"
            "Scoring defaults:\n"
            "- MCQ = 1 point\n"
            "- True/False = 1 point\n"
            "- Short Answer = 2 points (keyword partial credit)\n\n"
            "Quiz mode behavior:\n"
            "- Metadata markers ({answer:...}, [answer=...], etc.) are hidden while quizzing.\n"
            "- They are restored after Finish or Quit.\n"
            "- Save/autosave is disabled during active quiz mode."
        )
        root.addWidget(details, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok, Qt.Horizontal, dlg)
        buttons.accepted.connect(dlg.accept)
        root.addWidget(buttons)
        dlg.resize(760, 620)
        dlg.exec()

    @staticmethod
    def _quiz_strip_metadata_text(text: str) -> str:
        out = re.sub(r"\{(?:answer|keywords|user)\s*:[^{}]*\}", "", text, flags=re.IGNORECASE)
        out = re.sub(r"\[(?:answer|keywords|user)\s*=[^\[\]]*\]", "", out, flags=re.IGNORECASE)
        out = re.sub(r"\{user\}|\[user\]", "", out, flags=re.IGNORECASE)
        out = re.sub(r"\((?:correct)\s*:\s*[^()]*\)", "", out, flags=re.IGNORECASE)
        out = re.sub(r"[ \t]{2,}", " ", out)
        out = re.sub(r" +\n", "\n", out)
        return out

    def _parse_quiz_blocks(self, text: str) -> list[dict[str, Any]]:
        lines = text.splitlines()
        start_re = re.compile(r"^\s*(?:\d+[\.\)]|Q\d+\s*:|-|\*)\s+")
        option_re = re.compile(r"^\s*([A-Z])[\.\)]\s+(.+)\s*$")
        meta_re = re.compile(r"\{(?:answer|keywords)\s*:[^{}]+\}|\[(?:answer|keywords)\s*=[^\[\]]+\]|\(correct\s*:\s*[^)]+\)", re.IGNORECASE)
        marker_only_re = re.compile(
            r"^\s*(?:\{(?:answer|keywords)\s*:[^{}]+\}|\[(?:answer|keywords)\s*=[^\[\]]+\]|\(correct\s*:\s*[^)]+\)|\{user\}|\[user\])\s*$",
            re.IGNORECASE,
        )
        user_anchor_re = re.compile(r"\{user\}|\[user\]", re.IGNORECASE)
        answer_curly = re.compile(r"\{answer\s*:\s*([^{}]+)\}", re.IGNORECASE)
        answer_square = re.compile(r"\[answer\s*=\s*([^\[\]]+)\]", re.IGNORECASE)
        answer_paren = re.compile(r"\(correct\s*:\s*([^)]+)\)", re.IGNORECASE)
        keywords_re = re.compile(r"\{keywords\s*:\s*([^{}]+)\}", re.IGNORECASE)
        starts: list[int] = []
        for idx, line in enumerate(lines):
            if start_re.match(line):
                starts.append(idx)
                continue
            if meta_re.search(line) and not option_re.match(line) and not marker_only_re.match(line):
                starts.append(idx)
        if not starts:
            return []
        items: list[dict[str, Any]] = []
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(lines)
            block_lines = lines[start:end]
            block_text = "\n".join(block_lines)
            options: list[tuple[str, str, int]] = []
            option_lines: list[int] = []
            user_anchor_line = -1
            for offset, row in enumerate(block_lines):
                m = option_re.match(row)
                if not m:
                    if user_anchor_line < 0 and user_anchor_re.search(row):
                        user_anchor_line = start + offset
                    continue
                options.append((m.group(1).upper(), m.group(2).strip(), start + offset))
                option_lines.append(start + offset)
            answer = ""
            for pattern in (answer_curly, answer_square, answer_paren):
                m = pattern.search(block_text)
                if m:
                    answer = str(m.group(1) or "").strip()
                    break
            keywords: list[str] = []
            m_keywords = keywords_re.search(block_text)
            if m_keywords:
                keywords = [p.strip().lower() for p in str(m_keywords.group(1)).split("|") if p.strip()]
            has_answer_meta = bool(answer.strip()) or bool(keywords)
            has_structured_options = len(options) >= 2
            # Avoid treating generic bullet-list help text as quiz questions.
            # v1 quiz blocks are expected to be gradable via metadata or option structure.
            first_line = block_lines[0] if block_lines else ""
            prompt_text = self._quiz_strip_metadata_text(first_line).strip()
            has_prompt_words = len(re.findall(r"[A-Za-z]{2,}", prompt_text)) >= 2
            if not (has_answer_meta or has_structured_options):
                continue
            if not has_structured_options and not has_prompt_words:
                # Reject marker-only/reference lines in help docs.
                continue
            prompt = self._quiz_strip_metadata_text(block_lines[0]).strip()
            qtype = "short"
            answer_norm = answer.strip().lower()
            if options:
                qtype = "mcq"
                if answer_norm in {"t", "f", "true", "false"}:
                    qtype = "tf"
                elif len(options) == 2:
                    optset = {o[1].strip().lower() for o in options}
                    if optset <= {"true", "false"}:
                        qtype = "tf"
            elif answer_norm in {"t", "f", "true", "false"}:
                qtype = "tf"
            points = 2.0 if qtype == "short" else 1.0
            items.append(
                {
                    "number": len(items) + 1,
                    "type": qtype,
                    "prompt": prompt,
                    "block_start": start,
                    "block_end": end,
                    "option_lines": option_lines,
                    "user_anchor_line": user_anchor_line,
                    "options": options,
                    "answer": answer,
                    "keywords": keywords,
                    "points": points,
                }
            )
        return items

    def _collect_user_answers(self, tab: EditorTab) -> dict[int, str]:
        text = tab.text_edit.get_text()
        lines = text.splitlines()
        out: dict[int, str] = {}
        prompt_prefix_re = re.compile(r"^\s*(?:\d+[\.\)]|Q\d+\s*:|-|\*)\s*")
        for item in getattr(tab, "quiz_items", []):
            idx = int(item.get("number", 0))
            start = int(item.get("block_start", 0))
            end = int(item.get("block_end", start + 1))
            option_lines = set(int(x) for x in item.get("option_lines", []))
            user_anchor_line = int(item.get("user_anchor_line", -1))
            qtype = str(item.get("type", "short"))
            if start >= len(lines):
                out[idx] = ""
                continue
            if 0 <= user_anchor_line < len(lines):
                anchored = self._quiz_strip_metadata_text(lines[user_anchor_line]).strip()
                out[idx] = anchored
                continue
            answer_parts: list[str] = []
            line_start = start
            line_end = min(end, len(lines))
            for ln in range(line_start, line_end):
                if ln in option_lines:
                    continue
                line_text = lines[ln]
                if ln == start:
                    clean = re.sub(r"^\s*(?:\d+[\.\)]|Q\d+\s*:|-|\*)\s*", "", line_text).strip()
                    prompt = str(item.get("prompt", "")).strip()
                    prompt_norm = prompt_prefix_re.sub("", self._quiz_strip_metadata_text(prompt)).strip()
                    if prompt_norm and clean.lower().startswith(prompt_norm.lower()):
                        clean = clean[len(prompt_norm):].strip(" :-\t")
                    line_text = clean
                line_text = self._quiz_strip_metadata_text(line_text).strip()
                if line_text:
                    answer_parts.append(line_text)
            candidate = " ".join(answer_parts).strip()
            out[idx] = candidate
        return out

    @staticmethod
    def _normalize_tf(value: str) -> str:
        v = str(value or "").strip().lower()
        if v in {"t", "true"}:
            return "true"
        if v in {"f", "false"}:
            return "false"
        return v

    def _score_quiz_items(self, items: list[dict[str, Any]], user_answers: dict[int, str]) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        total = 0.0
        earned = 0.0
        counts = {"correct": 0, "incorrect": 0, "partial": 0, "unanswered": 0}
        type_totals: dict[str, dict[str, float]] = {
            "mcq": {"earned": 0.0, "max": 0.0},
            "tf": {"earned": 0.0, "max": 0.0},
            "short": {"earned": 0.0, "max": 0.0},
        }
        for item in items:
            num = int(item.get("number", 0))
            qtype = str(item.get("type", "short"))
            max_points = float(item.get("points", 1.0))
            expected = str(item.get("answer", "")).strip()
            options = item.get("options", []) if isinstance(item.get("options", []), list) else []
            keywords = [str(k).strip().lower() for k in item.get("keywords", []) if str(k).strip()]
            user = str(user_answers.get(num, "") or "").strip()
            got = 0.0
            status = "Incorrect"
            if not user:
                status = "Unanswered"
                counts["unanswered"] += 1
            elif qtype == "mcq":
                expected_letter = expected.strip().upper()
                user_token_match = re.search(r"\b([A-Za-z])\b", user)
                user_letter = user_token_match.group(1).upper() if user_token_match else ""
                expected_text = ""
                for opt in options:
                    if not isinstance(opt, (tuple, list)) or len(opt) < 2:
                        continue
                    if str(opt[0]).strip().upper() == expected_letter:
                        expected_text = str(opt[1]).strip().lower()
                        break
                user_text = user.strip().lower()
                if user_letter == expected_letter or (expected_text and user_text == expected_text):
                    got = max_points
                    status = "Correct"
                    counts["correct"] += 1
                else:
                    counts["incorrect"] += 1
            elif qtype == "tf":
                expected_tf = self._normalize_tf(expected)
                if expected_tf not in {"true", "false"} and options:
                    for opt in options:
                        if not isinstance(opt, (tuple, list)) or len(opt) < 2:
                            continue
                        if str(opt[0]).strip().upper() == str(expected).strip().upper():
                            expected_tf = self._normalize_tf(str(opt[1]))
                            break
                user_tf = self._normalize_tf(user)
                if user_tf not in {"true", "false"} and options:
                    m = re.search(r"\b([A-Za-z])\b", user)
                    user_letter = m.group(1).upper() if m else ""
                    for opt in options:
                        if not isinstance(opt, (tuple, list)) or len(opt) < 2:
                            continue
                        if str(opt[0]).strip().upper() == user_letter:
                            user_tf = self._normalize_tf(str(opt[1]))
                            break
                if user_tf == expected_tf:
                    got = max_points
                    status = "Correct"
                    counts["correct"] += 1
                else:
                    counts["incorrect"] += 1
            else:
                user_l = user.lower()
                expected_l = expected.lower()
                if expected_l and user_l == expected_l:
                    got = max_points
                    status = "Correct"
                    counts["correct"] += 1
                elif keywords:
                    hit = sum(1 for k in keywords if k and k in user_l)
                    ratio = hit / max(1, len(keywords))
                    if ratio >= 0.6:
                        got = max_points
                        status = "Correct"
                        counts["correct"] += 1
                    elif ratio >= 0.3:
                        got = round(max_points * 0.5, 2)
                        status = "Partial"
                        counts["partial"] += 1
                    else:
                        counts["incorrect"] += 1
                else:
                    counts["incorrect"] += 1
            total += max_points
            earned += got
            t = type_totals.setdefault(qtype, {"earned": 0.0, "max": 0.0})
            t["earned"] += got
            t["max"] += max_points
            expected_display = expected if expected else ("|".join(keywords) if keywords else "")
            rows.append(
                {
                    "number": num,
                    "type": qtype,
                    "user": user,
                    "expected": expected_display,
                    "earned": got,
                    "max": max_points,
                    "status": status,
                }
            )
        percent = (earned / total * 100.0) if total > 0 else 0.0
        return {
            "earned": round(earned, 2),
            "max": round(total, 2),
            "percent": round(percent, 2),
            "type_totals": type_totals,
            "counts": counts,
            "rows": rows,
        }

    def _show_quiz_score_dialog(self, result: dict[str, Any]) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Quiz Score")
        layout = QVBoxLayout(dlg)
        summary = QLabel(
            f"Score: {result.get('earned', 0)}/{result.get('max', 0)} ({result.get('percent', 0)}%)",
            dlg,
        )
        layout.addWidget(summary)
        counts = result.get("counts", {})
        layout.addWidget(
            QLabel(
                f"Correct: {counts.get('correct', 0)} | Partial: {counts.get('partial', 0)} | "
                f"Incorrect: {counts.get('incorrect', 0)} | Unanswered: {counts.get('unanswered', 0)}",
                dlg,
            )
        )
        type_totals = result.get("type_totals", {})
        mcq = type_totals.get("mcq", {})
        tf = type_totals.get("tf", {})
        short = type_totals.get("short", {})
        layout.addWidget(
            QLabel(
                f"MCQ {mcq.get('earned', 0)}/{mcq.get('max', 0)} | "
                f"TF {tf.get('earned', 0)}/{tf.get('max', 0)} | "
                f"Short {short.get('earned', 0)}/{short.get('max', 0)}",
                dlg,
            )
        )
        layout.addWidget(QLabel("Manual review may be needed for ambiguous free-text answers.", dlg))
        table = QTableWidget(dlg)
        headers = ["#", "Type", "Your Answer", "Expected", "Points", "Status"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        rows = result.get("rows", [])
        table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(str(row.get("number", ""))))
            table.setItem(r, 1, QTableWidgetItem(str(row.get("type", ""))))
            table.setItem(r, 2, QTableWidgetItem(str(row.get("user", ""))))
            table.setItem(r, 3, QTableWidgetItem(str(row.get("expected", ""))))
            table.setItem(r, 4, QTableWidgetItem(f"{row.get('earned', 0)}/{row.get('max', 0)}"))
            table.setItem(r, 5, QTableWidgetItem(str(row.get("status", ""))))
        table.resizeColumnsToContents()
        layout.addWidget(table)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok, Qt.Horizontal, dlg)
        buttons.accepted.connect(dlg.accept)
        layout.addWidget(buttons)
        dlg.resize(920, 520)
        dlg.exec()

    def _apply_quiz_placeholders(self, tab: EditorTab, user_answers: dict[int, str] | None = None) -> None:
        widget = getattr(tab.text_edit, "widget", None)
        if widget is None or not hasattr(widget, "annotationClearAll"):
            return
        try:
            widget.annotationClearAll()
        except Exception:
            return
        answer_map = user_answers or {}
        lines = tab.text_edit.get_text().splitlines()
        for item in getattr(tab, "quiz_items", []):
            number = int(item.get("number", 0))
            if str(answer_map.get(number, "")).strip():
                continue
            anchor = int(item.get("user_anchor_line", -1))
            start = int(item.get("block_start", -1))
            end = int(item.get("block_end", start + 1))
            option_lines = set(int(x) for x in item.get("option_lines", []))
            line = -1
            # Only place placeholders on empty lines to avoid drawing over question text.
            if 0 <= anchor < len(lines) and anchor not in option_lines and not str(lines[anchor]).strip():
                line = anchor
            for ln in range(start + 1, min(end, len(lines))):
                if line >= 0:
                    break
                if ln in option_lines:
                    continue
                if not str(lines[ln]).strip():
                    line = ln
                    break
            if line < 0:
                continue
            try:
                widget.annotationSetText(line, "Your answer...")
            except Exception:
                continue

    def _refresh_quiz_placeholders_for_tab(self, tab: EditorTab) -> None:
        if tab is None or not bool(getattr(tab, "quiz_mode_enabled", False)):
            return
        tab.quiz_user_answers = self._collect_user_answers(tab)
        self._apply_quiz_placeholders(tab, tab.quiz_user_answers)

    def start_quiz_mode(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        was_active = bool(getattr(tab, "quiz_mode_enabled", False))
        # Restarting quiz mode should always rebuild from the true source text,
        # not from the already-stripped quiz view.
        original = (
            str(getattr(tab, "quiz_original_text", ""))
            if was_active and isinstance(getattr(tab, "quiz_original_text", None), str)
            else tab.text_edit.get_text()
        )
        items = self._parse_quiz_blocks(original)
        if not items:
            QMessageBox.information(self, "Quiz Mode", "No quiz blocks detected in this document.")
            return
        tab.quiz_original_text = original
        tab.quiz_items = items
        tab.quiz_user_answers = {}
        tab.quiz_score_result = None
        tab.quiz_mode_enabled = True
        quiz_text = self._quiz_strip_metadata_text(original)
        tab.text_edit.set_text(quiz_text)
        tab.text_edit.set_modified(False)
        self._refresh_quiz_placeholders_for_tab(tab)
        self._sync_quiz_controls()
        self.update_action_states()
        self.show_status_message("Quiz mode restarted." if was_active else "Quiz mode started.", 2500)

    def quit_quiz_mode(self) -> None:
        tab = self.active_tab()
        if tab is None or not bool(getattr(tab, "quiz_mode_enabled", False)):
            return
        if isinstance(tab.quiz_original_text, str):
            tab.text_edit.set_text(tab.quiz_original_text)
            tab.text_edit.set_modified(False)
        widget = getattr(tab.text_edit, "widget", None)
        if widget is not None and hasattr(widget, "annotationClearAll"):
            try:
                widget.annotationClearAll()
            except Exception:
                pass
        tab.quiz_mode_enabled = False
        tab.quiz_items = []
        tab.quiz_user_answers = {}
        tab.quiz_score_result = None
        tab.quiz_original_text = None
        self._sync_quiz_controls()
        self.update_action_states()
        self.show_status_message("Quiz mode exited.", 2500)

    def finish_quiz_mode(self) -> None:
        tab = self.active_tab()
        if tab is None or not bool(getattr(tab, "quiz_mode_enabled", False)):
            return
        tab.quiz_user_answers = self._collect_user_answers(tab)
        result = self._score_quiz_items(tab.quiz_items, tab.quiz_user_answers)
        tab.quiz_score_result = result
        self._show_quiz_score_dialog(result)
        if hasattr(self, "gamification") and self._gamification_enabled():
            xp_result, notes = self.gamification.mark_quiz_finished()
            self._show_gamification_progress(xp_result, notes)
            self._evaluate_easter_eggs("shortcut_used")
        self.quit_quiz_mode()

    def ai_commit_message_generator(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        prompt = (
            "Write a concise commit message and a changelog entry for this file update.\n\n"
            f"File: {tab.current_file or 'Untitled'}\n\n"
            + tab.text_edit.get_text()[:20000]
        )
        self._send_ai_chat_prompt(prompt=prompt, visible_prompt="Generate Commit/Changelog Draft")

    def ai_batch_refactor_preview(self) -> None:
        root = self._workspace_root()
        if not root:
            QMessageBox.information(self, "Batch Refactor", "Set a workspace folder first.")
            return
        files = self._workspace_files()[:80]
        if not files:
            QMessageBox.information(self, "Batch Refactor", "No workspace files found.")
            return
        instruction, ok = QInputDialog.getMultiLineText(
            self,
            "Batch AI Refactor",
            "Refactor instruction to apply across files:",
        )
        if not ok or not instruction.strip():
            return
        self._run_batch_ai_refactor_planner(instruction.strip(), files)

    def _run_batch_ai_refactor_planner(self, instruction: str, candidate_files: list[str]) -> None:
        max_files = int(self.settings.get("ai_batch_refactor_max_selected_files", 20) or 20)
        self._log_ai_feature(
            f"batch planner start instruction_chars={len(instruction)} candidate_files={len(candidate_files)} max_files={max_files}"
        )
        planner_prompt = (
            "You are planning a batch refactor across a workspace.\n"
            "Return a JSON object only (no prose, no code fences) using this schema:\n"
            "{"
            "\"files\":[{\"path\":\"...\",\"reason\":\"...\",\"priority\":1}],"
            "\"global_risks\":[\"...\"],"
            "\"suggested_order\":[\"...\"]"
            "}\n"
            f"Pick at most {max_files} files from the candidate list. Use exact paths from the list.\n"
            "Prioritize files most relevant to the requested refactor.\n\n"
            f"Refactor instruction:\n{instruction}\n\n"
            "Candidate files:\n" + "\n".join(candidate_files[:300])
        )

        def _on_done(text: str) -> None:
            plan = self._parse_batch_refactor_plan(text, candidate_files, max_files=max_files)
            self._log_ai_feature(
                "batch planner parsed "
                f"planned_files={len(plan.get('files', [])) if isinstance(plan, dict) else 0}"
            )
            if not plan["files"]:
                QMessageBox.information(
                    self,
                    "Batch Refactor Plan",
                    "AI plan did not contain a valid file list. Try again with a narrower instruction.",
                )
                return
            selected = self._choose_batch_refactor_files_dialog(
                instruction=instruction,
                plan=plan,
                max_files=max_files,
            )
            if not selected:
                self._log_ai_feature("batch planner selection canceled/empty")
                return
            self._ensure_ai_chat_apply_signal_connected()
            self._ai_batch_refactor_state = {
                "active": True,
                "awaiting_apply": False,
                "rows": list(selected),
                "instruction": instruction,
                "index": 0,
                "path": "",
            }
            self._log_ai_feature(f"batch refactor queue initialized selected_files={len(selected)}")
            self._run_batch_refactor_queue(selected, instruction, 0)

        self._send_ai_chat_prompt(
            prompt=planner_prompt,
            visible_prompt=f"Batch AI Refactor Plan: {instruction}",
            on_done=_on_done,
        )

    @staticmethod
    def _parse_batch_refactor_plan(raw_text: str, candidate_files: list[str], *, max_files: int) -> dict[str, object]:
        text = strip_model_fences(raw_text or "").strip()
        if "```" in (raw_text or ""):
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text or "", re.DOTALL | re.IGNORECASE)
            if m:
                text = m.group(1).strip()
        try:
            data = json.loads(text)
        except Exception:
            # Fallback: try extracting the first object block.
            m = re.search(r"\{[\s\S]*\}", text)
            if not m:
                return {"files": [], "global_risks": [], "suggested_order": [], "_parse_error": "no_json_object"}
            try:
                data = json.loads(m.group(0))
            except Exception:
                return {"files": [], "global_risks": [], "suggested_order": [], "_parse_error": "json_decode_failed"}
        if not isinstance(data, dict):
            return {"files": [], "global_risks": [], "suggested_order": [], "_parse_error": "not_object"}
        candidate_set = {str(p) for p in candidate_files}
        file_rows: list[dict[str, object]] = []
        raw_rows = data.get("files", [])
        if isinstance(raw_rows, list):
            for row in raw_rows:
                if not isinstance(row, dict):
                    continue
                path = str(row.get("path", "") or "").strip()
                if path not in candidate_set:
                    continue
                reason = str(row.get("reason", "") or "").strip()
                try:
                    priority = int(row.get("priority", 999) or 999)
                except Exception:
                    priority = 999
                file_rows.append({"path": path, "reason": reason, "priority": priority})
        # Dedup preserve order, then sort by priority.
        seen: set[str] = set()
        dedup: list[dict[str, object]] = []
        for row in sorted(file_rows, key=lambda r: (int(r.get("priority", 999)), str(r.get("path", "")))):
            p = str(row.get("path", ""))
            if p in seen:
                continue
            seen.add(p)
            dedup.append(row)
            if len(dedup) >= max_files:
                break
        risks = [str(x).strip() for x in data.get("global_risks", [])] if isinstance(data.get("global_risks", []), list) else []
        order = [str(x).strip() for x in data.get("suggested_order", [])] if isinstance(data.get("suggested_order", []), list) else []
        return {
            "files": dedup,
            "global_risks": [r for r in risks if r][:20],
            "suggested_order": [o for o in order if o][:100],
        }

    def _choose_batch_refactor_files_dialog(self, *, instruction: str, plan: dict[str, object], max_files: int) -> list[dict[str, object]]:
        rows = plan.get("files", [])
        if not isinstance(rows, list) or not rows:
            return []
        dlg = QDialog(self)
        dlg.setWindowTitle("Batch AI Refactor Plan")
        dlg.resize(920, 620)
        apply_dialog_theme_from_window(self, dlg)
        layout = QVBoxLayout(dlg)
        top = QLabel(f"Instruction: {instruction}", dlg)
        top.setWordWrap(True)
        layout.addWidget(top)
        split = QSplitter(Qt.Horizontal, dlg)
        layout.addWidget(split, 1)
        list_widget = QListWidget(split)
        details = QTextEdit(split)
        details.setReadOnly(True)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)
        for i, row in enumerate(rows[:max_files]):
            if not isinstance(row, dict):
                continue
            path = str(row.get("path", "") or "")
            reason = str(row.get("reason", "") or "")
            label = f"{Path(path).name} :: {path}"
            item = QListWidgetItem(label, list_widget)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, i)
            item.setToolTip(reason or path)

        def _refresh_details() -> None:
            item = list_widget.currentItem()
            if item is None:
                details.clear()
                return
            idx = item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(idx, int) or not (0 <= idx < len(rows)):
                details.clear()
                return
            row = rows[idx]
            if not isinstance(row, dict):
                details.clear()
                return
            path = str(row.get("path", "") or "")
            reason = str(row.get("reason", "") or "")
            priority = int(row.get("priority", 999) or 999)
            file_preview = ""
            try:
                file_preview = Path(path).read_text(encoding="utf-8", errors="replace")[:3000]
            except Exception as exc:
                file_preview = f"(Could not read file: {exc})"
            risks = plan.get("global_risks", [])
            risk_lines = []
            if isinstance(risks, list):
                risk_lines = [f"- {str(r)}" for r in risks[:8]]
            details.setPlainText(
                f"Path: {path}\nPriority: {priority}\nReason: {reason or '(none)'}\n\n"
                + ("Global risks:\n" + "\n".join(risk_lines) + "\n\n" if risk_lines else "")
                + "Preview:\n"
                + file_preview
            )

        list_widget.currentItemChanged.connect(lambda _c, _p: _refresh_details())
        if list_widget.count():
            list_widget.setCurrentRow(0)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, dlg)
        select_all_btn = btns.addButton("Select All", QDialogButtonBox.ButtonRole.ActionRole)
        select_none_btn = btns.addButton("Select None", QDialogButtonBox.ButtonRole.ActionRole)
        layout.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        select_all_btn.clicked.connect(lambda: [list_widget.item(i).setCheckState(Qt.CheckState.Checked) for i in range(list_widget.count())])
        select_none_btn.clicked.connect(lambda: [list_widget.item(i).setCheckState(Qt.CheckState.Unchecked) for i in range(list_widget.count())])
        if dlg.exec() != QDialog.Accepted:
            return []
        selected: list[dict[str, object]] = []
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.checkState() != Qt.CheckState.Checked:
                continue
            idx = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(idx, int) and 0 <= idx < len(rows) and isinstance(rows[idx], dict):
                selected.append(dict(rows[idx]))
        return selected[:max_files]

    def _run_batch_refactor_queue(self, selected_rows: list[dict[str, object]], instruction: str, index: int) -> None:
        if index >= len(selected_rows):
            state = getattr(self, "_ai_batch_refactor_state", None)
            if isinstance(state, dict):
                state["active"] = False
                state["awaiting_apply"] = False
            self.show_status_message("Batch AI refactor queue finished.", 4000)
            self._log_ai_feature("batch refactor queue reached end")
            return
        row = selected_rows[index]
        path = str(row.get("path", "") or "")
        reason = str(row.get("reason", "") or "")
        self._log_ai_feature(f"batch refactor queue send index={index} path={path!r}")
        state = getattr(self, "_ai_batch_refactor_state", None)
        if isinstance(state, dict):
            state.update({"active": True, "awaiting_apply": False, "rows": list(selected_rows), "instruction": instruction, "index": index, "path": path})
        if not path:
            self._run_batch_refactor_queue(selected_rows, instruction, index + 1)
            return
        try:
            file_text = Path(path).read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            ans = QMessageBox.question(
                self,
                "Batch Refactor",
                f"Could not read file:\n{path}\n\n{exc}\n\nContinue to next file?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if ans == QMessageBox.Yes:
                self._run_batch_refactor_queue(selected_rows, instruction, index + 1)
            else:
                if isinstance(state, dict):
                    state["active"] = False
            return
        if len(file_text) > 30000:
            file_text = file_text[:30000]
        file_name = Path(path).name

        def _after_ai_response(_text: str) -> None:
            st = getattr(self, "_ai_batch_refactor_state", None)
            if isinstance(st, dict):
                st["awaiting_apply"] = True
                st["index"] = index
                st["path"] = path
            self._log_ai_feature(f"batch refactor awaiting apply confirmation path={path!r}")
            self.show_status_message(
                f"Batch refactor draft ready for {file_name}. Review and confirm in AI Chat to continue.",
                5000,
            )

        self._send_ai_file_replace_request(
            action_label="Batch AI Refactor",
            user_visible_prompt=f"Batch Refactor: {file_name}",
            task_instructions=(
                f"Apply the batch refactor instruction to this file only.\n\n"
                f"Global instruction:\n{instruction}\n\n"
                f"Why this file was selected:\n{reason or '(no reason provided)'}"
            ),
            file_text=file_text,
            extra_context=(
                f"File path: {path}\n"
                "Return the entire updated file contents via the hidden set-file command. "
                "Keep unrelated content unchanged."
            ),
            on_done=_after_ai_response,
        )

    def ai_ask_file_with_citations(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        question, ok = QInputDialog.getMultiLineText(self, "Ask About This File (Citations)", "Question:")
        if not ok or not question.strip():
            return
        numbered = []
        for idx, line in enumerate(tab.text_edit.get_text().splitlines(), start=1):
            numbered.append(f"{idx:04d}: {line}")
        payload = "\n".join(numbered[:1200])
        prompt = (
            "Explain about the file and include citations like [line:123].\n\n"
            f"File:\n{payload}\n\nUser question:\n{question.strip()}"
        )
        if hasattr(self, "toggle_ai_chat_panel"):
            self.toggle_ai_chat_panel(True)
        if hasattr(self, "ai_chat_dock"):
            self.ai_chat_dock.send_prompt(prompt=prompt, visible_prompt=question.strip())

    def ai_inline_edit_with_preview(self) -> None:
        tab = self.active_tab()
        if tab is None or tab.text_edit.is_read_only():
            return
        source = tab.text_edit.get_text()
        if not source.strip():
            QMessageBox.information(self, "AI Inline Edit", "Current document is empty.")
            return
        selection = tab.text_edit.selected_text()
        if selection.strip():
            sel = tab.text_edit.selection_range()
            if not sel:
                return
            start = tab.text_edit.index_from_line_col(sel[0], sel[1])
            end = tab.text_edit.index_from_line_col(sel[2], sel[3])
            target_text = source[start:end]
            target_label = "selection"
        else:
            start, end = paragraph_bounds(source, tab.text_edit.cursor_index())
            target_text = source[start:end]
            target_label = "current paragraph"
        if not target_text.strip():
            QMessageBox.information(self, "AI Inline Edit", "Select some text or place cursor in a non-empty paragraph.")
            return
        instruction, ok = QInputDialog.getMultiLineText(
            self,
            "AI Inline Edit",
            f"Instruction for {target_label}:",
        )
        if not ok or not instruction.strip():
            return
        self._send_ai_file_replace_request(
            action_label="AI Inline Edit",
            user_visible_prompt=f"AI Inline Edit: {instruction.strip()}",
            task_instructions=(
                f"Apply the instruction to the target {target_label}. Only change what is necessary.\n\n"
                f"Instruction:\n{instruction.strip()}\n\n"
                f"Target text:\n{target_text}"
            ),
            file_text=source,
            extra_context=(
                f"Target label: {target_label}\n"
                f"Target start index: {start}\n"
                f"Target end index: {end}\n"
                "Return the entire updated file contents."
            ),
        )

    def ai_ask_workspace_with_citations(self) -> None:
        root = self._workspace_root()
        if not root:
            QMessageBox.information(self, "Workspace Q&A", "Set a workspace folder first.")
            return
        files = self._workspace_files()
        if not files:
            QMessageBox.information(self, "Workspace Q&A", "No workspace files found.")
            return
        question, ok = QInputDialog.getMultiLineText(self, "Ask Workspace (Citations)", "Question:")
        if not ok or not question.strip():
            return
        snippets = build_workspace_citation_snippets(
            question.strip(),
            files,
            max_files=int(self.settings.get("ai_workspace_qa_max_files", 10) or 10),
            max_lines_per_file=int(self.settings.get("ai_workspace_qa_max_lines_per_file", 60) or 60),
            max_total_chars=30000,
        )
        if not snippets:
            QMessageBox.information(self, "Workspace Q&A", "No matching file excerpts found for this question.")
            return
        prompt = build_project_qa_prompt(question.strip(), snippets)
        if hasattr(self, "toggle_ai_chat_panel"):
            self.toggle_ai_chat_panel(True)
        if hasattr(self, "ai_chat_dock"):
            self.ai_chat_dock.send_prompt(prompt=prompt, visible_prompt=f"Ask Workspace (Citations): {question.strip()}")

    def show_collaboration_presence(self) -> None:
        snapshot = self.advanced_features.collaboration_snapshot()
        QMessageBox.information(self, "Collaboration Presence", build_collab_presence_text(snapshot))

    def resolve_collaboration_conflict(self) -> None:
        tab = self.active_tab()
        if tab is None or tab.text_edit.is_read_only():
            return
        snapshot = self.advanced_features.collaboration_snapshot()
        if not bool(snapshot.get("running", False)):
            QMessageBox.information(self, "Collaboration Conflict", "Collaboration server is not running.")
            return
        local_text = tab.text_edit.get_text()
        shared_text = self.advanced_features.collaboration_shared_text()
        if local_text == shared_text:
            QMessageBox.information(self, "Collaboration Conflict", "Local and shared text are already in sync.")
            return
        options = [
            "Open Merge Markers Preview",
            "Use Shared Version",
            "Push Local Version to Shared",
            "AI Merge Draft (Preview)",
        ]
        choice, ok = QInputDialog.getItem(self, "Resolve Collaboration Conflict", "Strategy:", options, 0, False)
        if not ok or not choice:
            return

        def _apply_and_optionally_push(merged_text: str, push: bool = False) -> None:
            tab.text_edit.set_text(merged_text)
            tab.text_edit.set_modified(True)
            if push:
                self.advanced_features.collaboration_set_shared_text(merged_text, source="host-local")
            self.show_status_message("Collaboration conflict resolution applied.", 3200)

        if choice == "Use Shared Version":
            _apply_and_optionally_push(shared_text, push=False)
            return
        if choice == "Push Local Version to Shared":
            _apply_and_optionally_push(local_text, push=True)
            return
        if choice == "Open Merge Markers Preview":
            merged = build_conflict_markers(local_text, shared_text)
            dlg = AIEditPreviewDialog(self, local_text, merged, title="Collaboration Merge Markers Preview")
            if dlg.exec() == QDialog.Accepted:
                _apply_and_optionally_push(dlg.final_text, push=False)
            return
        if choice == "AI Merge Draft (Preview)":
            self._send_ai_file_replace_request(
                action_label="AI Collaboration Merge",
                user_visible_prompt="AI Collaboration Merge Draft",
                task_instructions=(
                    "Merge the local and shared versions into a single clean final file. "
                    "Preserve user content and avoid conflict markers in the final result."
                ),
                file_text=local_text,
                extra_context=(
                    "Shared collaboration version contents:\n"
                    f"{shared_text}\n\n"
                    "Return the merged result as the full file contents via the hidden set-file command."
                ),
            )
            self.show_status_message(
                "AI merge draft sent to AI Chat. Confirm in chat to apply; push-to-shared can be done afterward.",
                5000,
            )

    def ai_review_current_file_with_citations(self) -> None:
        tab = self.active_tab()
        if tab is None:
            QMessageBox.information(self, "AI Code Review", "Open a tab first.")
            return
        numbered = [f"{idx:04d}: {line}" for idx, line in enumerate(tab.text_edit.get_text().splitlines(), start=1)]
        prompt = (
            "Review this file for bugs, regressions, and risks.\n"
            "Return findings first. For each finding include severity (High/Medium/Low) and a citation like [line:123].\n"
            "If evidence is insufficient, say what is missing.\n\n"
            f"FILE: {tab.current_file or 'Untitled'}\n\n"
            + "\n".join(numbered[:1500])
        )
        self._send_ai_chat_prompt(prompt=prompt, visible_prompt="Review Current File (Citations)")

    def ai_review_workspace_snippets_with_citations(self) -> None:
        root = self._workspace_root()
        if not root:
            QMessageBox.information(self, "Workspace Code Review", "Set a workspace folder first.")
            return
        files = self._workspace_files()
        if not files:
            QMessageBox.information(self, "Workspace Code Review", "No workspace files found.")
            return
        focus, ok = QInputDialog.getMultiLineText(
            self,
            "Review Workspace Snippets (Citations)",
            "Focus / area to review (optional):",
            "bugs regressions risky patterns",
        )
        if not ok:
            return
        focus = (focus or "").strip() or "bugs regressions risky patterns"
        snippets = build_workspace_citation_snippets(
            focus,
            files,
            max_files=int(self.settings.get("ai_workspace_qa_max_files", 10) or 10),
            max_lines_per_file=int(self.settings.get("ai_workspace_qa_max_lines_per_file", 60) or 60),
            max_total_chars=30000,
        )
        if not snippets:
            QMessageBox.information(self, "Workspace Code Review", "No matching excerpts found.")
            return
        prompt = (
            "Review the provided workspace excerpts for bugs, regressions, and risks.\n"
            "Return findings first. Include severity and evidence citations in the form [file:<path>#line:<line>].\n"
            "If evidence is insufficient, say what is missing.\n\n"
            f"FOCUS:\n{focus}\n\n"
            + "\n\n".join(f"FILE: {s.path}\n{s.excerpt}" for s in snippets)
        )
        self._send_ai_chat_prompt(prompt=prompt, visible_prompt="Review Workspace Snippets (Citations)")
        if hasattr(self, "gamification") and self._gamification_enabled():
            xp_result, notes = self.gamification.mark_workspace_review()
            self._show_gamification_progress(xp_result, notes)
            self._evaluate_easter_eggs("workspace_review")

    def ai_rewrite_selection(self, mode: str) -> None:
        tab = self.active_tab()
        if tab is None or tab.text_edit.is_read_only():
            return
        selected = (tab.text_edit.selected_text() or "").strip()
        if not selected:
            QMessageBox.information(self, "AI Rewrite", "Select text first.")
            return
        prompts = {
            "shorten": "Rewrite the selected text to be concise while preserving meaning.",
            "formal": "Rewrite the selected text in a formal professional tone.",
            "fix_grammar": "Fix grammar and punctuation in the selected text while preserving tone.",
            "summarize": "Summarize the selected text into a concise version.",
        }
        instruction = prompts.get(mode, "Rewrite the selected text.")
        source = tab.text_edit.get_text()
        sel = tab.text_edit.selection_range()
        if not sel:
            QMessageBox.information(self, "AI Rewrite", "Could not read the selection range.")
            return
        start = tab.text_edit.index_from_line_col(sel[0], sel[1])
        end = tab.text_edit.index_from_line_col(sel[2], sel[3])
        target_text = source[start:end]
        self._send_ai_file_replace_request(
            action_label=f"AI Rewrite ({mode})",
            user_visible_prompt=f"Rewrite Selection ({mode})",
            task_instructions=f"{instruction}\n\nSelected text:\n{target_text}",
            file_text=source,
            extra_context=(
                f"Rewrite mode: {mode}\n"
                f"Selection start index: {start}\n"
                f"Selection end index: {end}\n"
                "Only rewrite the selected text and preserve the rest exactly. Return the entire updated file contents."
            ),
        )

    def ask_ai_about_current_context(self) -> None:
        tab = self.active_tab()
        if tab is None:
            QMessageBox.information(self, "Ask About File", "Open a tab first.")
            return
        contents = tab.text_edit.get_text()
        prompt = f"Explain about the file:\n\n{contents}"
        self._send_ai_chat_prompt(prompt=prompt, visible_prompt="")

    def toggle_simple_mode(self, checked: bool, *, persist: bool = True) -> None:
        self.settings["simple_mode"] = bool(checked)
        if checked:
            self.menuBar().setVisible(True)
            if hasattr(self, "markdown_menu"):
                try:
                    self.markdown_menu.menuAction().setVisible(False)
                except RuntimeError:
                    pass
            if hasattr(self, "macros_menu"):
                try:
                    self.macros_menu.menuAction().setVisible(False)
                except RuntimeError:
                    pass
            if hasattr(self, "search_toolbar"):
                self.search_toolbar.hide()
            self.settings["show_find_panel"] = False
            self.settings["show_markdown_toolbar"] = False
        else:
            if hasattr(self, "markdown_menu"):
                try:
                    self.markdown_menu.menuAction().setVisible(True)
                except RuntimeError:
                    pass
            if hasattr(self, "macros_menu"):
                try:
                    self.macros_menu.menuAction().setVisible(True)
                except RuntimeError:
                    pass
        self._layout_top_toolbars()
        if persist:
            self.save_settings_to_disk()

    def apply_reading_preset(self) -> None:
        self.settings["font_size"] = 15
        self.settings["word_wrap"] = True
        self.word_wrap_enabled = True
        self.word_wrap_action.setChecked(True)
        self.apply_settings()
        self.show_status_message("Applied Reading preset.", 2500)

    def apply_writing_preset(self) -> None:
        self.settings["font_size"] = 15
        self.settings["word_wrap"] = True
        self.word_wrap_enabled = True
        self.word_wrap_action.setChecked(True)
        self.settings["show_main_toolbar"] = False
        self.settings["show_markdown_toolbar"] = False
        self.settings["status_show_breadcrumb"] = False
        self.settings["status_show_selection_stats"] = True
        if hasattr(self, "editor_dock"):
            self.editor_dock.show()
        for name in ("ai_chat_dock", "markdown_preview_dock", "search_results_dock", "minimap_dock", "outline_dock"):
            dock = getattr(self, name, None)
            if dock is not None:
                dock.hide()
        self.apply_settings()
        self.show_status_message("Applied Writing preset.", 2500)

    def apply_coding_preset(self) -> None:
        self.settings["font_size"] = 12
        self.settings["tab_width"] = 4
        self.word_wrap_enabled = False
        self.word_wrap_action.setChecked(False)
        self.settings["show_main_toolbar"] = True
        self.settings["status_show_breadcrumb"] = True
        self.settings["status_show_selection_stats"] = True
        if hasattr(self, "outline_dock"):
            self.outline_dock.show()
        self.apply_settings()
        self.show_status_message("Applied Coding preset.", 2500)

    def apply_focus_preset(self) -> None:
        self.focus_mode_action.setChecked(True)
        self.toggle_focus_mode(True)
        self.show_status_message("Applied Focus preset.", 2500)

    def apply_review_preset(self) -> None:
        self.settings["show_main_toolbar"] = True
        self.settings["status_show_breadcrumb"] = True
        self.settings["status_show_selection_stats"] = True
        self.word_wrap_enabled = True
        self.word_wrap_action.setChecked(True)
        if hasattr(self, "search_results_dock"):
            self.search_results_dock.show()
        if hasattr(self, "outline_dock"):
            self.outline_dock.show()
        if hasattr(self, "markdown_preview_dock") and bool(self.active_tab() and self.active_tab().markdown_mode_enabled):
            self.markdown_preview_dock.show()
        self.apply_settings()
        self.show_status_message("Applied Review preset.", 2500)

    def toggle_ai_chat_panel(self, checked: bool | None = None) -> None:
        if not hasattr(self, "ai_chat_dock"):
            return
        desired = not self.ai_chat_dock.isVisible() if checked is None else bool(checked)
        self.ai_chat_dock.setVisible(desired)
        if desired:
            self.ai_chat_dock.raise_()
            self.ai_chat_dock.focus_prompt()
        if hasattr(self, "ai_chat_panel_action"):
            self.ai_chat_panel_action.blockSignals(True)
            self.ai_chat_panel_action.setChecked(desired)
            self.ai_chat_panel_action.blockSignals(False)

    def explain_selection_with_ai(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        selected = tab.text_edit.selected_text().strip()
        if not selected:
            QMessageBox.information(self, "Explain Selection", "Select text first.")
            return
        prompt = f"Explain this: {selected}"
        if hasattr(self, "toggle_ai_chat_panel"):
            self.toggle_ai_chat_panel(True)
        if hasattr(self, "ai_chat_dock"):
            self.ai_chat_dock.send_prompt(prompt=prompt, visible_prompt=prompt)

    def _selected_math_text_for_homework(self) -> str:
        tab = self.active_tab()
        if tab is None:
            return ""
        selected = str(tab.text_edit.selected_text() or "").strip()
        return selected

    def homework_solve_with_ai(self) -> None:
        selected = self._selected_math_text_for_homework()
        if not selected:
            QMessageBox.information(self, "Homework: Solve with AI", "Select a math expression or problem first.")
            return
        prompt = (
            "Solve this homework math problem.\n"
            "Use standard school math notation by default. "
            "Do NOT use Peano notation (S(0), S(S(0)), etc.) unless the user explicitly asks for it.\n"
            "Return STRICTLY in this Markdown format:\n"
            "## Solution\n"
            "1. ...\n"
            "## Final Answer\n"
            "... \n"
            "## Formats\n"
            "- LaTeX (inline): `$...$`\n"
            "- LaTeX (block): `$$...$$`\n"
            "- Markdown: `...`\n"
            "- Plain text: `...`\n"
            "Use valid LaTeX delimiters ($...$ and $$...$$). Do not use unicode bullets.\n\n"
            f"Problem:\n{selected}"
        )
        self._send_ai_chat_prompt(prompt=prompt, visible_prompt="Homework: Solve with AI")

    def homework_solve_with_solutions_with_ai(self) -> None:
        selected = self._selected_math_text_for_homework()
        if not selected:
            QMessageBox.information(self, "Homework: Solve with Solutions with AI", "Select a math expression or problem first.")
            return
        prompt = (
            "Solve this homework problem and provide full worked solutions.\n"
            "Use standard school math notation by default. "
            "Do NOT use Peano notation (S(0), S(S(0)), etc.) unless the user explicitly asks for it.\n"
            "Return STRICTLY in this Markdown format:\n"
            "## Detailed Solution\n"
            "1. ...\n"
            "## Alternative Method\n"
            "1. ...\n"
            "## Final Answer\n"
            "... \n"
            "## Formats\n"
            "- LaTeX (inline): `$...$`\n"
            "- LaTeX (block): `$$...$$`\n"
            "- Markdown: `...`\n"
            "- Plain text: `...`\n"
            "Use valid LaTeX delimiters ($...$ and $$...$$). Do not use unicode bullets.\n\n"
            f"Problem:\n{selected}"
        )
        self._send_ai_chat_prompt(prompt=prompt, visible_prompt="Homework: Solve with Solutions with AI")

    def homework_answer_with_ai(self) -> None:
        selected = self._selected_math_text_for_homework()
        if not selected:
            QMessageBox.information(self, "Homework: Answer with AI", "Select a math expression or problem first.")
            return
        prompt = (
            "Provide only the final answer for this homework problem.\n"
            "Use standard school math notation by default. "
            "Do NOT use Peano notation (S(0), S(S(0)), etc.) unless the user explicitly asks for it.\n"
            "Return STRICTLY in this Markdown format:\n"
            "## Final Answer\n"
            "... \n"
            "## Formats\n"
            "- LaTeX (inline): `$...$`\n"
            "- LaTeX (block): `$$...$$`\n"
            "- Markdown: `...`\n"
            "- Plain text: `...`\n"
            "Use valid LaTeX delimiters ($...$ and $$...$$). Do not use unicode bullets.\n\n"
            f"Problem:\n{selected}"
        )
        self._send_ai_chat_prompt(prompt=prompt, visible_prompt="Homework: Answer with AI")

    def generate_text_to_tab_with_ai(self) -> None:
        tab = self.active_tab()
        if tab is None:
            QMessageBox.information(self, "Generate Text", "Open a tab first.")
            return
        if tab.text_edit.is_read_only():
            QMessageBox.information(self, "Generate Text", "Current tab is read-only.")
            return
        user_request, ok = QInputDialog.getMultiLineText(self, "Generate Text", "Prompt:")
        if not ok or not user_request.strip():
            return
        self._send_ai_file_replace_request(
            action_label="Generate Text",
            user_visible_prompt=user_request.strip(),
            task_instructions=(
                "Generate or revise the document to satisfy the user's request and return the complete final file contents.\n\n"
                f"User request:\n{user_request.strip()}"
            ),
            file_text=tab.text_edit.get_text(),
        )

    def check_for_updates(self, manual: bool = True) -> None:
        self.updater_controller.check_for_updates(manual=manual)

    def _sort_tabs_by_pinned(self) -> None:
        tabs: list[EditorTab] = []
        for index in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(index)
            if isinstance(widget, EditorTab):
                tabs.append(widget)
        if len(tabs) < 2:
            return
        current = self.active_tab()
        ordered = sorted(tabs, key=lambda t: (not t.pinned, not t.favorite, self._tab_display_name(t).lower()))
        if ordered == tabs:
            return
        while self.tab_widget.count():
            self.tab_widget.removeTab(0)
        for tab in ordered:
            self.tab_widget.addTab(tab, self._tab_display_name(tab))
            self._refresh_tab_title(tab)
        if current is not None:
            self.tab_widget.setCurrentWidget(current)

    def _ensure_tab_autosave_meta(self, tab: EditorTab) -> None:
        if tab.autosave_id:
            return
        tab.autosave_id = self.autosave_store.new_id()
        tab.autosave_path = str(self.autosave_store.autosave_file(tab.autosave_id))

    def _local_history_cache(self) -> dict[str, list[dict[str, str]]]:
        if not self.settings.get("local_history_persist_enabled", True):
            return {}
        cache = getattr(self, "_local_history_index_cache", None)
        if isinstance(cache, dict):
            return cache
        store = getattr(self, "recovery_state_store", None)
        if store is None:
            cache = {}
        else:
            cache = store.load_local_history()
        self._local_history_index_cache = cache
        return cache

    def _restore_tab_local_history(self, tab: EditorTab) -> None:
        if not self.settings.get("local_history_persist_enabled", True):
            return
        try:
            key = local_history_key(tab.current_file, tab.autosave_id, self._tab_display_name(tab))
            rows = self._local_history_cache().get(key, [])
            if not rows:
                return
            max_entries = int(self.settings.get("version_history_max_entries", 50))
            rebuilt: list[VersionEntry] = []
            for row in rows[-max_entries:]:
                rebuilt.append(
                    VersionEntry(
                        timestamp=str(row.get("timestamp", "")),
                        label=str(row.get("label", "Snapshot")),
                        text=str(row.get("text", "")),
                    )
                )
            if rebuilt:
                tab.version_history.entries = rebuilt
        except Exception:
            return

    def _persist_tab_local_history(self, tab: EditorTab) -> None:
        if not self.settings.get("local_history_persist_enabled", True):
            return
        entries = getattr(tab.version_history, "entries", [])
        if not entries:
            return
        key = local_history_key(tab.current_file, tab.autosave_id, self._tab_display_name(tab))
        payload: list[dict[str, str]] = []
        max_entries = int(self.settings.get("version_history_max_entries", 50))
        for entry in entries[-max_entries:]:
            payload.append(
                {
                    "timestamp": str(getattr(entry, "timestamp", "")),
                    "label": str(getattr(entry, "label", "Snapshot")),
                    "text": str(getattr(entry, "text", "")),
                }
            )
        if not payload:
            return
        cache = self._local_history_cache()
        cache[key] = payload
        store = getattr(self, "recovery_state_store", None)
        if store is not None:
            store.save_local_history(cache)

    def _capture_crash_snapshot(self) -> None:
        store = getattr(self, "recovery_state_store", None)
        if not self.settings.get("crash_snapshot_enabled", True):
            if store is not None:
                store.clear_crash_snapshot()
            return
        if store is None:
            return
        tabs_payload: list[dict[str, str]] = []
        for index in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(index)
            if not isinstance(tab, EditorTab):
                continue
            if not tab.text_edit.is_modified():
                continue
            tabs_payload.append(
                {
                    "title": self._tab_display_name(tab),
                    "original_path": str(tab.current_file or ""),
                    "text": tab.text_edit.get_text(),
                    "autosave_id": str(tab.autosave_id or ""),
                }
            )
        if not tabs_payload:
            store.clear_crash_snapshot()
            return
        active = self.active_tab()
        active_file = str(active.current_file if active is not None and active.current_file else "")
        store.save_crash_snapshot(
            tabs=tabs_payload,
            active_file=active_file,
            workspace_root=str(self.settings.get("workspace_root", "") or ""),
        )

    def _restore_from_snapshot_payload(self, payload: dict[str, object]) -> int:
        raw_tabs = payload.get("tabs", [])
        if not isinstance(raw_tabs, list):
            return 0
        restored = 0
        selected_active_path = str(payload.get("active_file", "") or "")
        for row in raw_tabs:
            if not isinstance(row, dict):
                continue
            text = str(row.get("text", ""))
            if not text:
                continue
            original_path = str(row.get("original_path", "") or "")
            path_for_tab = original_path if original_path else None
            tab = self.add_new_tab(text=text, file_path=path_for_tab, make_current=False)
            tab.text_edit.set_modified(True)
            tab.autosave_id = str(row.get("autosave_id", "") or "") or tab.autosave_id
            if tab.autosave_id:
                tab.autosave_path = str(self.autosave_store.autosave_file(tab.autosave_id))
            self._seed_version_history(tab, label="Recovered Snapshot")
            self._apply_file_metadata_to_tab(tab)
            restored += 1
        if restored:
            workspace_root = str(payload.get("workspace_root", "") or "")
            if workspace_root and Path(workspace_root).exists():
                self.settings["workspace_root"] = workspace_root
            if selected_active_path:
                for index in range(self.tab_widget.count()):
                    tab = self.tab_widget.widget(index)
                    if isinstance(tab, EditorTab) and tab.current_file == selected_active_path:
                        self.tab_widget.setCurrentIndex(index)
                        break
            self.update_window_title()
            self.update_status_bar()
        return restored

    def _run_autosave_cycle(self) -> None:
        if not self.settings.get("autosave_enabled", True):
            if hasattr(self, "autosave_status_label"):
                self.autosave_status_label.setText("Save off")
            return
        saved_count = 0
        draft_count = 0
        autosave_marked_saved = False
        for index in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(index)
            if not isinstance(tab, EditorTab):
                continue
            if bool(getattr(tab, "quiz_mode_enabled", False)):
                continue
            if tab.large_file:
                continue
            if not tab.text_edit.is_modified():
                if tab.autosave_id:
                    self._clear_tab_autosave(tab)
                continue
            # For real files, autosave should persist to the file on disk.
            if tab.current_file and not tab.text_edit.is_read_only() and not getattr(tab, "partial_large_preview", False):
                try:
                    if self.file_save_tab(tab):
                        autosave_marked_saved = True
                        saved_count += 1
                        continue
                except Exception:
                    pass
                # If direct save fails, fall back to draft snapshot below.
            self._ensure_tab_autosave_meta(tab)
            if not tab.autosave_id or not tab.autosave_path:
                continue
            try:
                autosave_file = Path(tab.autosave_path)
                autosave_file.parent.mkdir(parents=True, exist_ok=True)
                autosave_file.write_text(tab.text_edit.get_text(), encoding="utf-8")
                self.autosave_store.upsert(
                    autosave_id=tab.autosave_id,
                    autosave_path=tab.autosave_path,
                    original_path=tab.current_file or "",
                    title=self._tab_display_name(tab),
                )
                draft_count += 1
                if hasattr(self, "_persist_tab_local_history"):
                    self._persist_tab_local_history(tab)
            except Exception:
                continue
        self.autosave_store.save()
        self._capture_crash_snapshot()
        if hasattr(self, "autosave_status_label"):
            if saved_count > 0:
                self.autosave_status_label.setText(f"Saved {saved_count}")
            elif draft_count > 0:
                self.autosave_status_label.setText(f"Draft {draft_count}")
        if autosave_marked_saved:
            self.update_action_states()
            self.update_window_title()
            self.update_status_bar()

    def _clear_tab_autosave(self, tab: EditorTab) -> None:
        if not tab.autosave_id:
            return
        if tab.autosave_path:
            try:
                path = Path(tab.autosave_path)
                if path.exists():
                    path.unlink()
            except Exception:
                pass
        self.autosave_store.remove(tab.autosave_id)
        self.autosave_store.save()
        tab.autosave_id = None
        tab.autosave_path = None

    def _offer_crash_recovery(self) -> None:
        def _consume_placeholder_tab() -> None:
            tab = self.active_tab()
            if tab is None:
                return
            if tab.current_file:
                return
            if tab.text_edit.is_modified():
                return
            if tab.text_edit.get_text().strip():
                return
            idx = self.tab_widget.indexOf(tab)
            if idx >= 0:
                self.close_tab(idx)

        discard_days = int(self.settings.get("recovery_discard_after_days", 14))
        try:
            self.autosave_store.prune_older_than_days(discard_days)
            self.autosave_store.save()
        except Exception:
            pass
        store = getattr(self, "recovery_state_store", None)
        if store is not None and self.settings.get("local_history_persist_enabled", True):
            try:
                store.prune_local_history(800, int(self.settings.get("version_history_max_entries", 50)))
            except Exception:
                pass
        mode = str(self.settings.get("recovery_mode", "ask") or "ask")
        entries = list(self.autosave_store.entries.values())
        snapshot_payload = (
            store.load_crash_snapshot()
            if (store is not None and self.settings.get("crash_snapshot_enabled", True))
            else None
        )
        has_snapshot_tabs = bool(snapshot_payload and isinstance(snapshot_payload.get("tabs", []), list) and snapshot_payload.get("tabs"))
        if not entries and not has_snapshot_tabs:
            return
        if mode == "auto_discard":
            for entry in entries:
                try:
                    path = Path(entry.autosave_path)
                    if path.exists():
                        path.unlink()
                except Exception:
                    pass
                self.autosave_store.remove(entry.autosave_id)
            self.autosave_store.save()
            if store is not None:
                store.clear_crash_snapshot()
            return
        if mode == "auto_restore":
            restored_any = False
            for entry in entries:
                try:
                    text = Path(entry.autosave_path).read_text(encoding="utf-8")
                except Exception:
                    text = ""
                if not restored_any:
                    _consume_placeholder_tab()
                tab = self.add_new_tab(text=text, file_path=entry.original_path or None, make_current=True)
                tab.autosave_id = entry.autosave_id
                tab.autosave_path = entry.autosave_path
                self._seed_version_history(tab, label="Recovered")
                self._apply_file_metadata_to_tab(tab)
                tab.text_edit.set_modified(True)
                restored_any = True
            if not entries and snapshot_payload:
                _consume_placeholder_tab()
                self._restore_from_snapshot_payload(snapshot_payload)
            self.autosave_store.save()
            if store is not None:
                store.clear_crash_snapshot()
            return
        startup_ready_cb = QApplication.instance().property("startup_ready_callback")
        if callable(startup_ready_cb):
            startup_ready_cb(self)
        app = QApplication.instance()
        prior_quit_on_last = bool(app.quitOnLastWindowClosed()) if app is not None else True
        if entries:
            try:
                if app is not None and not self.isVisible():
                    app.setQuitOnLastWindowClosed(False)
                dlg = AutoSaveRecoveryDialog(self, entries)
                if dlg.exec() != QDialog.Accepted:
                    return
                if dlg.selected_action == "discard" and dlg.selected_ids:
                    _consume_placeholder_tab()
                restored_any = False
                for autosave_id in dlg.selected_ids:
                    entry = self.autosave_store.entries.get(autosave_id)
                    if entry is None:
                        continue
                    if dlg.selected_action == "discard":
                        try:
                            path = Path(entry.autosave_path)
                            if path.exists():
                                path.unlink()
                        except Exception:
                            pass
                        self.autosave_store.remove(autosave_id)
                        continue
                    try:
                        text = Path(entry.autosave_path).read_text(encoding="utf-8")
                    except Exception:
                        text = ""
                    if not restored_any:
                        _consume_placeholder_tab()
                    tab = self.add_new_tab(text=text, file_path=entry.original_path or None, make_current=True)
                    tab.autosave_id = entry.autosave_id
                    tab.autosave_path = entry.autosave_path
                    self._seed_version_history(tab, label="Recovered")
                    self._apply_file_metadata_to_tab(tab)
                    tab.text_edit.set_modified(True)
                    restored_any = True
            finally:
                if app is not None:
                    app.setQuitOnLastWindowClosed(prior_quit_on_last)
        elif snapshot_payload:
            try:
                if app is not None and not self.isVisible():
                    app.setQuitOnLastWindowClosed(False)
                answer = QMessageBox.question(
                    self,
                    "Recover Last Crash Snapshot",
                    "Restore recovered tabs from the last crash snapshot?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
            finally:
                if app is not None:
                    app.setQuitOnLastWindowClosed(prior_quit_on_last)
            if answer == QMessageBox.Yes:
                _consume_placeholder_tab()
                self._restore_from_snapshot_payload(snapshot_payload)
            else:
                if store is not None:
                    store.clear_crash_snapshot()
        self.autosave_store.save()
        if store is not None:
            store.clear_crash_snapshot()

    def load_settings_from_disk(self) -> None:
        path = self.settings_file
        _LOGGER.debug("Loading settings from %s", path)
        if not path.exists():
            legacy_path = self._get_legacy_settings_file_path()
            if legacy_path.exists():
                path = legacy_path
                _LOGGER.info("Using legacy settings file: %s", legacy_path)
        if not path.exists():
            _LOGGER.info("No settings file found; using defaults")
            return
        try:
            loaded = json.loads(path.read_bytes().decode("utf-8"))
        except Exception:
            _LOGGER.exception("Failed to read settings from %s", path)
            return
        if not isinstance(loaded, dict):
            _LOGGER.warning("Settings file did not contain a JSON object: %s", path)
            return
        self.settings.update(loaded)
        themes_path = self._get_themes_file_path()
        if themes_path.exists():
            try:
                themes_loaded = json.loads(themes_path.read_bytes().decode("utf-8"))
                if isinstance(themes_loaded, dict):
                    self.settings.update(themes_loaded)
            except Exception:
                _LOGGER.exception("Failed to read themes from %s", themes_path)
        self.settings = migrate_settings(self.settings)
        normalize_ui_visibility_settings(self.settings)
        if hasattr(self, "apply_logging_preferences"):
            try:
                self.apply_logging_preferences()
            except Exception:
                _LOGGER.exception("Failed to apply logging preferences after settings load")
        if str(self.settings.get("app_style", "")).strip() in {"", "System Default"}:
            self.settings["app_style"] = self._default_style_name()
        password_data = self._load_password_data_from_disk()
        if not self.settings.get("lock_password"):
            from_bin = self._unprotect_settings_secret(str(password_data.get("lock_password_enc", "")))
            from_legacy = self._unprotect_settings_secret(str(loaded.get("lock_password_enc", "")))
            self.settings["lock_password"] = from_bin or from_legacy
        if not self.settings.get("lock_pin"):
            from_bin = self._unprotect_settings_secret(str(password_data.get("lock_pin_enc", "")))
            from_legacy = self._unprotect_settings_secret(str(loaded.get("lock_pin_enc", "")))
            self.settings["lock_pin"] = from_bin or from_legacy
        _LOGGER.info("Settings loaded and migrated from %s", path)

    def save_settings_to_disk(self, *, synchronous: bool = False) -> None:
        if bool(getattr(self, "_saving_settings_to_disk", False)):
            return
        self._saving_settings_to_disk = True
        started_at = time.perf_counter()
        caller = "unknown"
        try:
            frame = sys._getframe(1)
            caller = f"{Path(frame.f_code.co_filename).name}:{frame.f_lineno}:{frame.f_code.co_name}"
        except Exception:
            caller = "unknown"
        try:
            payload = migrate_settings(dict(self.settings))
            self.settings = dict(payload)
            # Reconfigure logging only when level actually changes; doing this on
            # every settings save can stall the UI.
            if hasattr(self, "apply_logging_preferences"):
                desired_level = str(payload.get("logging_level", "INFO") or "INFO").strip().upper() or "INFO"
                last_level = str(getattr(self, "_last_applied_logging_level", "") or "").strip().upper()
                if desired_level != last_level:
                    self.apply_logging_preferences()
                    self._last_applied_logging_level = desired_level
            if synchronous:
                self._write_settings_payload(self._prepare_settings_write_payload(payload, caller=caller))
            else:
                self._enqueue_settings_save(
                    {
                        "settings_snapshot": dict(payload),
                        "caller": caller,
                    }
                )
        except Exception:
            _LOGGER.exception("Failed to prepare settings save (caller=%s)", caller)
            pass
        finally:
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            if elapsed_ms >= 150 and synchronous:
                _LOGGER.warning(
                    "Slow settings save prepare: %sms caller=%s tabs=%s quitting=%s",
                    elapsed_ms,
                    caller,
                    self.tab_widget.count() if hasattr(self, "tab_widget") else "?",
                    bool(getattr(QApplication.instance(), "closingDown", lambda: False)())
                    if QApplication.instance() is not None
                    else False,
                )
            self._saving_settings_to_disk = False

    def _prepare_settings_write_payload(self, payload: dict[str, Any], *, caller: str) -> dict[str, Any]:
        lock_password = str(payload.get("lock_password", "") or "")
        lock_pin = str(payload.get("lock_pin", "") or "")
        password_bytes = self._build_password_payload_bytes(lock_password, lock_pin)
        theme_payload: dict[str, Any] = {}
        for key in THEME_SETTINGS_KEYS:
            if key in payload:
                theme_payload[key] = payload.get(key)
        # Keep plaintext values only in-memory.
        clean_payload = dict(payload)
        clean_payload["lock_password"] = ""
        clean_payload["lock_pin"] = ""
        clean_payload.pop("lock_password_enc", None)
        clean_payload.pop("lock_pin_enc", None)
        clean_payload.pop("focus_mode_enabled", None)
        clean_payload.pop("ai_chat_sessions", None)
        clean_payload.pop("ai_chat_history", None)
        clean_payload.pop("ai_chat_session_files", None)
        for key in THEME_SETTINGS_KEYS:
            clean_payload.pop(key, None)
        payload_bytes = json.dumps(clean_payload, indent=2).encode("utf-8")
        themes_bytes = json.dumps(theme_payload, indent=2).encode("utf-8")
        return {
            "settings_path": self.settings_file,
            "settings_bytes": payload_bytes,
            "themes_path": self._get_themes_file_path(),
            "themes_bytes": themes_bytes,
            "password_path": self._get_password_file_path(),
            "password_bytes": password_bytes,
            "caller": caller,
        }

    def _load_password_data_from_disk(self) -> dict:
        path = self._get_password_file_path()
        if not path.exists():
            return {}
        try:
            loaded = json.loads(path.read_bytes().decode("utf-8"))
            if isinstance(loaded, dict):
                return loaded
        except Exception:
            return {}
        return {}

    def _save_password_data_to_disk(self, lock_password: str, lock_pin: str) -> None:
        path = self._get_password_file_path()
        payload_bytes = self._build_password_payload_bytes(lock_password, lock_pin)
        existing_payload = path.read_bytes() if path.exists() else None
        if existing_payload != payload_bytes:
            self._atomic_write_bytes(path, payload_bytes)

    def _build_password_payload_bytes(self, lock_password: str, lock_pin: str) -> bytes:
        payload = {
            "lock_password_enc": self._protect_settings_secret(lock_password) if lock_password else "",
            "lock_pin_enc": self._protect_settings_secret(lock_pin) if lock_pin else "",
        }
        return json.dumps(payload, indent=2).encode("utf-8")

    def _enqueue_settings_save(self, payload: dict[str, Any]) -> None:
        lock = getattr(self, "_settings_save_lock", None)
        if lock is None:
            lock = threading.Lock()
            self._settings_save_lock = lock
        event = getattr(self, "_settings_save_event", None)
        if event is None:
            event = threading.Event()
            self._settings_save_event = event
        with lock:
            self._settings_save_pending = payload
            worker = getattr(self, "_settings_save_worker", None)
            if worker is None or not worker.is_alive():
                worker = threading.Thread(target=self._settings_save_worker_loop, name="settings-save-worker", daemon=True)
                self._settings_save_worker = worker
                worker.start()
        event.set()

    def _settings_save_worker_loop(self) -> None:
        lock = getattr(self, "_settings_save_lock", None)
        event = getattr(self, "_settings_save_event", None)
        if lock is None or event is None:
            return
        while True:
            event.wait()
            payload = None
            with lock:
                payload = getattr(self, "_settings_save_pending", None)
                self._settings_save_pending = None
                if payload is None:
                    event.clear()
            if payload is None:
                continue
            try:
                if "settings_snapshot" in payload:
                    payload = self._prepare_settings_write_payload(
                        dict(payload.get("settings_snapshot", {})),
                        caller=str(payload.get("caller", "unknown")),
                    )
                self._write_settings_payload(payload)
            except Exception:
                _LOGGER.exception("Settings worker failed while writing payload")

    def _write_settings_payload(self, payload: dict[str, Any]) -> None:
        settings_path = payload["settings_path"]
        settings_bytes = payload["settings_bytes"]
        themes_path = payload["themes_path"]
        themes_bytes = payload["themes_bytes"]
        password_path = payload["password_path"]
        password_bytes = payload["password_bytes"]
        caller = str(payload.get("caller", "unknown"))

        try:
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            existing_settings = settings_path.read_bytes() if settings_path.exists() else None
            if existing_settings != settings_bytes:
                self._atomic_write_bytes(settings_path, settings_bytes)

            themes_path.parent.mkdir(parents=True, exist_ok=True)
            existing_themes = themes_path.read_bytes() if themes_path.exists() else None
            if existing_themes != themes_bytes:
                self._atomic_write_bytes(themes_path, themes_bytes)

            password_path.parent.mkdir(parents=True, exist_ok=True)
            existing_password = password_path.read_bytes() if password_path.exists() else None
            if existing_password != password_bytes:
                self._atomic_write_bytes(password_path, password_bytes)

            _LOGGER.info("Settings saved to %s", settings_path)
        except Exception:
            _LOGGER.exception("Failed to write settings payload (caller=%s)", caller)

    @staticmethod
    def _atomic_write_bytes(path: Path, data: bytes) -> None:
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_bytes(data)
        os.replace(temp_path, path)

    @staticmethod
    def _normalize_hex_color(value: str) -> str | None:
        text = (value or "").strip()
        if not text:
            return None
        if not text.startswith("#"):
            text = f"#{text}"
        if len(text) not in (4, 7):
            return None
        hex_part = text[1:]
        if not all(ch in "0123456789abcdefABCDEF" for ch in hex_part):
            return None
        return text

    def _apply_status_layout_visibility(self) -> None:
        if hasattr(self, "position_label"):
            self.position_label.setVisible(bool(self.settings.get("status_show_position", True)))
        if hasattr(self, "zoom_label"):
            self.zoom_label.setVisible(bool(self.settings.get("status_show_zoom", True)))
        if hasattr(self, "eol_label"):
            self.eol_label.setVisible(bool(self.settings.get("status_show_eol", True)))
        if hasattr(self, "encoding_label"):
            self.encoding_label.setVisible(bool(self.settings.get("status_show_encoding", True)))
        show_syntax = bool(self.settings.get("status_show_syntax", True))
        if hasattr(self, "syntax_label"):
            self.syntax_label.setVisible(show_syntax)
        if hasattr(self, "syntax_combo"):
            self.syntax_combo.setVisible(show_syntax)
        if hasattr(self, "breadcrumb_label"):
            self.breadcrumb_label.setVisible(bool(self.settings.get("status_show_breadcrumb", True)))
        if hasattr(self, "selection_stats_label"):
            self.selection_stats_label.setVisible(bool(self.settings.get("status_show_selection_stats", True)))
        if hasattr(self, "ruler_label"):
            allow_ruler = bool(self.settings.get("status_show_ruler", True))
            show_ruler = bool(
                allow_ruler
                and getattr(self, "_page_layout_view_enabled", False)
                and self.settings.get("page_layout_show_ruler", True)
            )
            self.ruler_label.setVisible(show_ruler)
        if hasattr(self, "ai_usage_label"):
            self.ai_usage_label.setVisible(bool(self.settings.get("status_show_ai_usage", True)))
        if hasattr(self, "autosave_status_label"):
            self.autosave_status_label.setVisible(bool(self.settings.get("status_show_autosave", True)))
        if hasattr(self, "gamification_status_widget"):
            self.gamification_status_widget.setVisible(bool(self.settings.get("status_show_gamification", False)))
        if hasattr(self, "momentum_banner_widget"):
            self.momentum_banner_widget.setVisible(bool(self.settings.get("status_show_momentum", False)))
        if hasattr(self, "status_panel_position_label"):
            self.status_panel_position_label.setVisible(bool(self.settings.get("status_show_position", True)))
        if hasattr(self, "status_panel_zoom_label"):
            self.status_panel_zoom_label.setVisible(bool(self.settings.get("status_show_zoom", True)))
        if hasattr(self, "status_panel_eol_label"):
            self.status_panel_eol_label.setVisible(bool(self.settings.get("status_show_eol", True)))
        if hasattr(self, "status_panel_encoding_label"):
            self.status_panel_encoding_label.setVisible(bool(self.settings.get("status_show_encoding", True)))
        if hasattr(self, "status_panel_syntax_label"):
            self.status_panel_syntax_label.setVisible(bool(self.settings.get("status_show_syntax", True)))
        if hasattr(self, "status_panel_breadcrumb_label"):
            self.status_panel_breadcrumb_label.setVisible(bool(self.settings.get("status_show_breadcrumb", True)))
        if hasattr(self, "status_panel_selection_stats_label"):
            self.status_panel_selection_stats_label.setVisible(bool(self.settings.get("status_show_selection_stats", True)))
        if hasattr(self, "status_panel_ruler_label"):
            allow_ruler = bool(self.settings.get("status_show_ruler", True))
            show_ruler = bool(
                allow_ruler
                and getattr(self, "_page_layout_view_enabled", False)
                and self.settings.get("page_layout_show_ruler", True)
            )
            self.status_panel_ruler_label.setVisible(show_ruler)
        if hasattr(self, "status_panel_ai_usage_label"):
            self.status_panel_ai_usage_label.setVisible(bool(self.settings.get("status_show_ai_usage", True)))
        if hasattr(self, "status_panel_gamification_widget"):
            self.status_panel_gamification_widget.setVisible(bool(self.settings.get("status_show_gamification", False)))

    def apply_settings(self) -> None:
        _perf_start = time.perf_counter()
        _perf_marks: list[tuple[str, int]] = []

        def _mark(stage: str) -> None:
            _perf_marks.append((stage, int((time.perf_counter() - _perf_start) * 1000)))

        self.settings = migrate_settings(dict(self.settings))
        profile = ScintillaProfile.from_settings(self.settings)
        _mark("migrate_profile")
        if hasattr(self, "apply_logging_preferences"):
            self.apply_logging_preferences()
        _LOGGER.debug("Applying runtime settings (logging level=%s)", self.settings.get("logging_level", "INFO"))
        if hasattr(self, "apply_shortcut_settings"):
            self.apply_shortcut_settings()
        _mark("logging_shortcuts")
        app = QApplication.instance()
        if app is not None:
            ensure_dialog_theme_filter_installed()
            requested_style = str(self.settings.get("app_style", "System Default") or "System Default")
            last_style_request = str(getattr(self, "_last_applied_style_request", "") or "")
            if requested_style != last_style_request:
                if requested_style == "System Default":
                    default_name = type(self).system_style_name or ""
                    default_style = QStyleFactory.create(default_name) if default_name else None
                    if default_style is not None:
                        app.setStyle(default_style)
                else:
                    style_obj = QStyleFactory.create(requested_style)
                    if style_obj is not None:
                        app.setStyle(style_obj)
                self._last_applied_style_request = requested_style
            desired_cursor_flash = (
                int(self.settings.get("accessibility_cursor_blink_rate_ms", 1000))
                if bool(self.settings.get("accessibility_cursor_blink", True))
                else 0
            )
            if int(getattr(self, "_last_applied_cursor_flash_time", -1)) != desired_cursor_flash:
                app.setCursorFlashTime(desired_cursor_flash)
                self._last_applied_cursor_flash_time = desired_cursor_flash
        _mark("app_style_cursor")

        dock_options = QMainWindow.DockOption.AllowTabbedDocks | QMainWindow.DockOption.AllowNestedDocks
        if not bool(self.settings.get("accessibility_reduce_motion", False)):
            dock_options |= QMainWindow.DockOption.AnimatedDocks
        self.setDockOptions(dock_options)

        # Font size & family
        font = QFont()
        font.setPointSize(self.settings.get("font_size", 11))
        font_family = self.settings.get("font_family")
        if font_family:
            font.setFamily(font_family)
        for index in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(index)
            if isinstance(tab, EditorTab):
                tab.text_edit.set_font(font)
        _mark("font_per_tab")

        if hasattr(self, "snap_dock_left_action"):
            enable_snap = bool(self.settings.get("snap_dock_shortcuts_enabled", True))
            self.snap_dock_left_action.setShortcut(QKeySequence("Ctrl+Alt+Left") if enable_snap else QKeySequence())
            self.snap_dock_right_action.setShortcut(QKeySequence("Ctrl+Alt+Right") if enable_snap else QKeySequence())
            self.snap_dock_bottom_action.setShortcut(QKeySequence("Ctrl+Alt+Down") if enable_snap else QKeySequence())

        # Theming: token-driven soft modern chrome while preserving existing settings.
        effective_dark = resolve_dark_mode_from_settings(self.settings)
        tokens = build_tokens_from_settings(self.settings)
        density = str(self.settings.get("ui_density", "comfortable"))
        tab_close_icon_name = "tab-close-dark.svg" if effective_dark else "tab-close-light.svg"
        tab_close_icon_path = resolve_asset_path("icons", tab_close_icon_name) or resolve_asset_path("icons", "tab-close.svg")
        tab_close_icon_url = tab_close_icon_path.as_posix() if tab_close_icon_path else ""

        close_button_visibility_qss = ""
        if str(self.settings.get("tab_close_button_mode", "always")) == "hover":
            close_button_visibility_qss = f"""
            QTabBar::close-button {{
                image: none;
                background: transparent;
                border: none;
            }}
            QTabBar::tab:hover QTabBar::close-button {{
                image: url("{tab_close_icon_url}");
                background: #d13438;
                border: 1px solid #b72b2f;
                border-radius: {tokens.radius_sm}px;
            }}
            """
        chrome_color = QColor(tokens.chrome_bg)
        if chrome_color.isValid():
            self._icon_color = QColor(tokens.icon_fg)
        else:
            self._icon_color = QColor("#ffffff" if effective_dark else "#000000")

        qss = build_main_window_qss(
            tokens=tokens,
            tab_close_icon_url=tab_close_icon_url,
            close_button_visibility_qss=close_button_visibility_qss,
        )
        qss_changed = qss != str(getattr(self, "_last_applied_main_qss", "") or "")
        icon_signature = (
            tokens.icon_fg,
            tab_close_icon_url,
            int(self.settings.get("icon_size_px", 18)),
            str(self.settings.get("toolbar_label_mode", "icons_only")),
            bool(effective_dark),
        )
        icons_changed = icon_signature != getattr(self, "_last_applied_icon_signature", None)
        if qss_changed:
            if app is not None:
                app.setStyleSheet(qss)
            else:
                self.setStyleSheet(qss)
            self._last_applied_main_qss = qss
        if qss_changed or icons_changed:
            self._apply_main_toolbar_icons()
            self._apply_markdown_icons()
            self._apply_format_icons()
            if hasattr(self, "_apply_search_panel_theme"):
                self._apply_search_panel_theme()
            if hasattr(self, "_apply_custom_dock_title_bars_theme"):
                self._apply_custom_dock_title_bars_theme()
            if hasattr(self, "_refresh_empty_tabs_widget"):
                self._refresh_empty_tabs_widget()
            if hasattr(self, "_apply_ai_feature_icons"):
                self._apply_ai_feature_icons()
            if hasattr(self, "_refresh_explorer_dock"):
                self._refresh_explorer_dock()
            if hasattr(self, "gamification_status_widget"):
                self.gamification_status_widget.apply_theme(tokens)
            if hasattr(self, "status_panel_gamification_widget"):
                self.status_panel_gamification_widget.apply_theme(tokens)
            if hasattr(self, "momentum_banner_widget"):
                self.momentum_banner_widget.apply_theme(tokens)
            if hasattr(self, "productivity_hub_widget"):
                self.productivity_hub_widget.apply_theme(tokens)
            if hasattr(self, "gamification_reward_toast"):
                self.gamification_reward_toast.apply_theme(tokens)
            # Re-render tab file icons with the current theme icon color.
            if hasattr(self, "_refresh_tab_title"):
                for index in range(self.tab_widget.count()):
                    tab = self.tab_widget.widget(index)
                    if isinstance(tab, EditorTab):
                        try:
                            self._refresh_tab_title(tab)
                        except Exception:
                            pass
            if hasattr(self, "show_symbol_toolbar_button") and self.show_symbol_toolbar_button is not None:
                self.show_symbol_toolbar_button.setIcon(self._svg_icon("show-symbol"))
            if hasattr(self, "_schedule_main_toolbar_overflow_update"):
                self._schedule_main_toolbar_overflow_update()
            self._last_applied_icon_signature = icon_signature
        _mark("qss_icons")
        icon_px = int(self.settings.get("icon_size_px", 18))
        label_mode = str(self.settings.get("toolbar_label_mode", "icons_only"))
        style_map = {
            "icons_only": Qt.ToolButtonStyle.ToolButtonIconOnly,
            "text_only": Qt.ToolButtonStyle.ToolButtonTextOnly,
            "icons_text": Qt.ToolButtonStyle.ToolButtonTextBesideIcon,
        }
        tool_style = style_map.get(label_mode, Qt.ToolButtonStyle.ToolButtonIconOnly)
        for toolbar_name in ("main_toolbar", "markdown_toolbar", "search_toolbar"):
            toolbar = getattr(self, toolbar_name, None)
            if toolbar is None:
                continue
            toolbar.setIconSize(QSize(icon_px, icon_px))
            toolbar.setToolButtonStyle(tool_style)

        show_main_toolbar = bool(self.settings.get("show_main_toolbar", True))
        if hasattr(self, "main_toolbar") and self.main_toolbar is not None:
            self.main_toolbar.setVisible(show_main_toolbar)
        show_md_toolbar = bool(self.settings.get("show_markdown_toolbar", False))
        if hasattr(self, "md_toolbar_visible_action"):
            self.md_toolbar_visible_action.blockSignals(True)
            self.md_toolbar_visible_action.setChecked(show_md_toolbar)
            self.md_toolbar_visible_action.blockSignals(False)
        show_find_panel = bool(self.settings.get("show_find_panel", False))
        if hasattr(self, "search_panel_action"):
            self.search_panel_action.blockSignals(True)
            self.search_panel_action.setChecked(show_find_panel)
            self.search_panel_action.blockSignals(False)
        if hasattr(self, "workspace_startup_picker_action"):
            self.workspace_startup_picker_action.blockSignals(True)
            self.workspace_startup_picker_action.setChecked(bool(self.settings.get("workspace_startup_picker_enabled", False)))
            self.workspace_startup_picker_action.blockSignals(False)
        if hasattr(self, "_layout_top_toolbars"):
            self._layout_top_toolbars()
        if hasattr(self, "_restore_layout_from_settings") and not getattr(self, "_layout_restored_once", False):
            self._layout_restored_once = True
            if self.isVisible():
                self._restore_layout_from_settings()
            else:
                self._layout_restore_pending_after_show = True
        if hasattr(self, "_apply_layout_lock"):
            self._apply_layout_lock()
        focus_checked = bool(self.focus_mode_action.isChecked()) if hasattr(self, "focus_mode_action") else False
        self._apply_focus_mode(focus_checked)
        self._page_layout_view_enabled = bool(self.settings.get("page_layout_view_enabled", False))
        if hasattr(self, "page_layout_view_action"):
            self.page_layout_view_action.blockSignals(True)
            self.page_layout_view_action.setChecked(self._page_layout_view_enabled)
            self.page_layout_view_action.blockSignals(False)
        self.line_numbers_enabled = bool(self.settings.get("npp_margin_line_numbers_enabled", True))
        self.word_wrap_enabled = bool(profile.wrap_mode == "word")
        if hasattr(self, "word_wrap_action"):
            self.word_wrap_action.blockSignals(True)
            self.word_wrap_action.setChecked(self.word_wrap_enabled)
            self.word_wrap_action.blockSignals(False)
        if hasattr(self, "column_mode_action"):
            self.column_mode_action.blockSignals(True)
            self.column_mode_action.setChecked(bool(profile.column_mode))
            self.column_mode_action.blockSignals(False)
        if hasattr(self, "multi_caret_action"):
            self.multi_caret_action.blockSignals(True)
            self.multi_caret_action.setChecked(bool(profile.multi_caret))
            self.multi_caret_action.blockSignals(False)
        if hasattr(self, "code_folding_action"):
            self.code_folding_action.blockSignals(True)
            self.code_folding_action.setChecked(bool(profile.code_folding))
            self.code_folding_action.blockSignals(False)
        if hasattr(self, "show_line_numbers_action"):
            self.show_line_numbers_action.blockSignals(True)
            self.show_line_numbers_action.setChecked(self.line_numbers_enabled)
            self.show_line_numbers_action.blockSignals(False)
        if hasattr(self, "_set_editor_print_view_styles"):
            self._set_editor_print_view_styles(bool(self._page_layout_view_enabled and not getattr(self, "_print_view_enabled", False)))
        _mark("layout_toggle_actions")

        reminder_interval = int(self.settings.get("reminder_check_interval_sec", 30))
        if self.settings.get("reminders_enabled", True) and reminder_interval > 0:
            self.reminder_timer.start(reminder_interval * 1000)
        else:
            self.reminder_timer.stop()

        autosave_interval = int(self.settings.get("autosave_interval_sec", 30))
        if self.settings.get("autosave_enabled", True) and autosave_interval > 0:
            self.autosave_timer.start(autosave_interval * 1000)
            if hasattr(self, "autosave_status_label"):
                self.autosave_status_label.setText("Save on")
        else:
            self.autosave_timer.stop()
            if hasattr(self, "autosave_status_label"):
                self.autosave_status_label.setText("Save off")

        if hasattr(self, "syntax_combo"):
            self.syntax_combo.setEnabled(self.settings.get("syntax_highlighting_enabled", True))
            self.syntax_label.setEnabled(self.settings.get("syntax_highlighting_enabled", True))
        self._apply_status_layout_visibility()
        self._refresh_recent_files_menu()
        self._refresh_favorite_files_menu()
        if hasattr(self, "advanced_features"):
            self.advanced_features.apply_backup_schedule()
            self.advanced_features.toggle_keyboard_only(
                bool(self.settings.get("keyboard_only_mode", False)),
                persist=False,
            )
        _mark("timers_menus_advanced")

        for index in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(index)
            if isinstance(tab, EditorTab):
                if hasattr(tab.text_edit, "set_theme_colors"):
                    tab.text_edit.set_theme_colors(
                        background=tokens.editor_bg,
                        foreground=tokens.text,
                        selection_bg=tokens.selection_bg,
                        selection_fg=tokens.selection_fg,
                        caret_line_bg=tokens.tab_hover_bg,
                        gutter_bg=tokens.chrome_bg,
                        gutter_fg=tokens.text_muted,
                    )
                self._apply_syntax_highlighting(tab)
                tab.version_history.max_entries = int(self.settings.get("version_history_max_entries", 50))
                self._apply_tab_color(tab)
                tab.column_mode = bool(profile.column_mode)
                tab.multi_caret = bool(profile.multi_caret)
                tab.code_folding = bool(profile.code_folding)
                tab.auto_completion_mode = str(profile.auto_completion_mode or "all").lower()
                tab.show_space_tab = bool(profile.show_space_tab)
                tab.show_eol = bool(profile.show_eol)
                tab.show_non_printing = bool(profile.show_non_printing)
                tab.show_control_chars = bool(profile.show_control_chars)
                tab.show_all_chars = bool(profile.show_all_chars)
                tab.show_indent_guides = bool(profile.show_indent_guides)
                tab.show_wrap_symbol = bool(profile.show_wrap_symbol)
                tab.show_line_numbers = bool(profile.line_numbers_visible)
                tab.text_edit.set_wrap_enabled(profile.wrap_mode == "word")
                tab.text_edit.configure_indentation(tab_width=profile.tab_width, use_tabs=profile.use_tabs)
                if hasattr(self, "_apply_scintilla_modes"):
                    self._apply_scintilla_modes(tab)
                apply_indentation_defaults_to_tab(self, tab)
        _mark("tab_theme_syntax_modes")
        if hasattr(self, "ai_chat_dock") and self.ai_chat_dock is not None:
            self.ai_chat_dock.refresh_theme()
        if bool(self.settings.get("simple_mode", False)):
            self.toggle_simple_mode(True, persist=False)
        else:
            self.toggle_simple_mode(False, persist=False)
        desired_on_top = bool(self.settings.get("always_on_top", False))
        desired_tool = bool(self.settings.get("post_it_mode", False))
        current_flags = self.windowFlags()
        current_on_top = bool(current_flags & Qt.WindowType.WindowStaysOnTopHint)
        current_tool = bool(current_flags & Qt.WindowType.Tool)
        if current_on_top != desired_on_top or current_tool != desired_tool:
            # Updating top-level window flags can transiently hide the main window.
            # Avoid accidental app quit from QApplication.quitOnLastWindowClosed during this transition.
            prev_quit_on_last = None
            if app is not None:
                prev_quit_on_last = app.quitOnLastWindowClosed()
                app.setQuitOnLastWindowClosed(False)
            self.setWindowFlag(Qt.WindowStaysOnTopHint, desired_on_top)
            self.setWindowFlag(Qt.Tool, desired_tool)
            if self.isVisible():
                self.show()
            if app is not None and prev_quit_on_last is not None:
                app.setQuitOnLastWindowClosed(prev_quit_on_last)
        self._refresh_ai_usage_label()
        self.apply_language()
        apply_notepadpp_runtime_settings(self)
        _mark("finalize")
        _LOGGER.info(
            "apply_settings breakdown(ms): %s",
            ", ".join(f"{name}={ms}" for name, ms in _perf_marks),
        )

    def apply_language(self, *, force: bool = False) -> None:
        lang_label = str(self.settings.get("language", "English") or "English")
        lang_code = language_code_for(lang_label)
        if not force and str(getattr(self, "_ui_language_code", "") or "") == lang_code:
            return
        self._ui_language_code = lang_code
        self._translate_actions(lang_code)
        self._translate_widgets(lang_code)

    def clear_translation_cache(self) -> None:
        translator = getattr(self, "translator", None)
        if translator is None:
            return
        translator.clear_cache()
        self.log_event("Info", "Translation cache cleared")

    def show_status_message(self, text: str, timeout_ms: int = 0) -> None:
        lang_code = getattr(self, "_ui_language_code", "en")
        self.status.showMessage(self._translate_text(text, lang_code), timeout_ms)

    def _record_jump_history(self, *, reason: str = "cursor") -> None:
        if getattr(self, "_suspend_jump_recording", False):
            return
        tab = self.active_tab()
        if tab is None:
            return
        line, col = tab.text_edit.cursor_position()
        entry = {
            "tab_id": id(tab),
            "file": tab.current_file or "",
            "line": int(line),
            "col": int(col),
            "reason": reason,
        }
        history = getattr(self, "_jump_history", [])
        if history:
            last = history[-1]
            if (
                int(last.get("tab_id", -1)) == entry["tab_id"]
                and int(last.get("line", -1)) == entry["line"]
                and int(last.get("col", -1)) == entry["col"]
            ):
                return
        idx = int(getattr(self, "_jump_history_index", -1))
        if idx < len(history) - 1:
            history = history[: idx + 1]
        history.append(entry)
        if len(history) > 600:
            history = history[-600:]
        self._jump_history = history
        self._jump_history_index = len(history) - 1

    def _on_cursor_position_changed_for_jump_history(self) -> None:
        self._record_jump_history(reason="cursor")

    def can_jump_history_back(self) -> bool:
        return int(getattr(self, "_jump_history_index", -1)) > 0

    def can_jump_history_forward(self) -> bool:
        history = getattr(self, "_jump_history", [])
        return 0 <= int(getattr(self, "_jump_history_index", -1)) < len(history) - 1

    def _jump_history_move(self, direction: int) -> None:
        history = getattr(self, "_jump_history", [])
        if not history:
            return
        idx = int(getattr(self, "_jump_history_index", len(history) - 1))
        target = idx + direction
        if target < 0 or target >= len(history):
            return
        entry = history[target]
        tab_id = int(entry.get("tab_id", -1))
        target_tab = None
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if widget is not None and id(widget) == tab_id:
                target_tab = widget
                self.tab_widget.setCurrentIndex(i)
                break
        if target_tab is None:
            target_file = str(entry.get("file", "")).strip()
            if target_file and Path(target_file).exists():
                self._open_file_path(target_file)
                target_tab = self.active_tab()
        if target_tab is None:
            return
        line = max(0, int(entry.get("line", 0)))
        col = max(0, int(entry.get("col", 0)))
        self._suspend_jump_recording = True
        try:
            self.active_tab().text_edit.set_cursor_position(line, col)
        finally:
            self._suspend_jump_recording = False
        self._jump_history_index = target
        self.update_action_states()

    def jump_history_back(self) -> None:
        self._jump_history_move(-1)

    def jump_history_forward(self) -> None:
        self._jump_history_move(1)

    def show_jump_history(self) -> None:
        history = list(getattr(self, "_jump_history", []))
        if not history:
            QMessageBox.information(self, "Jump History", "No jump history yet.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Jump History")
        dlg.resize(700, 420)
        apply_dialog_theme_from_window(self, dlg)
        layout = QVBoxLayout(dlg)
        list_widget = QListWidget(dlg)
        for idx, entry in enumerate(history):
            name = Path(str(entry.get("file", "") or "Untitled")).name
            line = int(entry.get("line", 0)) + 1
            col = int(entry.get("col", 0)) + 1
            reason = str(entry.get("reason", "cursor"))
            item = QListWidgetItem(f"{name}  Ln {line}, Col {col}  ({reason})", list_widget)
            item.setData(Qt.UserRole, idx)
        layout.addWidget(list_widget, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close, Qt.Horizontal, dlg)
        jump_btn = QPushButton("Jump", dlg)
        buttons.addButton(jump_btn, QDialogButtonBox.ActionRole)
        layout.addWidget(buttons)
        buttons.rejected.connect(dlg.reject)

        def _jump_selected() -> None:
            current = list_widget.currentItem()
            if current is None:
                return
            idx = current.data(Qt.UserRole)
            if not isinstance(idx, int):
                return
            self._jump_history_index = idx
            self._jump_history_move(0)
            dlg.accept()

        list_widget.itemDoubleClicked.connect(lambda _item: _jump_selected())
        jump_btn.clicked.connect(_jump_selected)
        list_widget.setCurrentRow(len(history) - 1)
        dlg.exec()

    def _translate_text(self, text: str, lang_code: str) -> str:
        if not text:
            return text
        if not lang_code or lang_code == "en":
            return text
        translator = getattr(self, "translator", None)
        if translator is None:
            return text
        return translator.translate(text, lang_code)

    def _translate_action_text(self, text: str, lang_code: str) -> str:
        if not text:
            return text
        if not lang_code or lang_code == "en":
            return text
        has_accel = "&" in text
        raw = text.replace("&", "")
        translated = self._translate_text(raw, lang_code)
        if has_accel and translated:
            return f"&{translated}"
        return translated

    def _translate_actions(self, lang_code: str) -> None:
        for action in self.findChildren(QAction):
            if action.property("i18n_skip"):
                continue
            original_text = action.property("i18n_original_text") or action.text()
            action.setProperty("i18n_original_text", original_text)
            action.setText(self._translate_action_text(str(original_text), lang_code))

            original_tip = action.property("i18n_original_tooltip") or action.toolTip()
            action.setProperty("i18n_original_tooltip", original_tip)
            if original_tip:
                action.setToolTip(self._translate_text(str(original_tip), lang_code))

            original_status = action.property("i18n_original_statustip") or action.statusTip()
            action.setProperty("i18n_original_statustip", original_status)
            if original_status:
                action.setStatusTip(self._translate_text(str(original_status), lang_code))

    def _translate_widgets(self, lang_code: str) -> None:
        for widget in self.findChildren(QWidget):
            if widget.property("i18n_skip"):
                continue
            if isinstance(widget, QMainWindow):
                continue
            if isinstance(widget, QMenu):
                original = widget.property("i18n_original_title") or widget.title()
                widget.setProperty("i18n_original_title", original)
                widget.setTitle(self._translate_text(str(original), lang_code))
                continue
            if isinstance(widget, QDialog):
                original = widget.property("i18n_original_window_title") or widget.windowTitle()
                widget.setProperty("i18n_original_window_title", original)
                widget.setWindowTitle(self._translate_text(str(original), lang_code))
            if isinstance(widget, QGroupBox):
                original = widget.property("i18n_original_title") or widget.title()
                widget.setProperty("i18n_original_title", original)
                widget.setTitle(self._translate_text(str(original), lang_code))
            if isinstance(widget, (QLabel, QCheckBox, QPushButton, QRadioButton)):
                original = widget.property("i18n_original_text") or widget.text()
                widget.setProperty("i18n_original_text", original)
                widget.setText(self._translate_text(str(original), lang_code))
            if isinstance(widget, QLineEdit):
                original = widget.property("i18n_original_placeholder") or widget.placeholderText()
                widget.setProperty("i18n_original_placeholder", original)
                if original:
                    widget.setPlaceholderText(self._translate_text(str(original), lang_code))
            original_tooltip = widget.property("i18n_original_tooltip") or widget.toolTip()
            widget.setProperty("i18n_original_tooltip", original_tooltip)
            if original_tooltip:
                widget.setToolTip(self._translate_text(str(original_tooltip), lang_code))
            if isinstance(widget, QDialogButtonBox):
                for button in widget.buttons():
                    original = button.property("i18n_original_text") or button.text()
                    button.setProperty("i18n_original_text", original)
                    button.setText(self._translate_text(str(original), lang_code))

    def open_settings(self, initial_section: str | None = None) -> None:
        open_started_at = time.perf_counter()
        dlg = getattr(self, "_settings_dialog_cached", None)
        dlg_prepare_started_at = time.perf_counter()
        if dlg is None:
            dlg = SidebarSettingsDialog(self, self.settings, initial_section=initial_section)
            self._settings_dialog_cached = dlg
            dlg_prepare_mode = "create"
        elif hasattr(dlg, "reload_from_settings"):
            current_settings = dict(self.settings) if isinstance(self.settings, dict) else {}
            needs_reload = True
            try:
                if hasattr(dlg, "get_settings") and dlg.get_settings() == current_settings:
                    needs_reload = False
            except Exception:
                needs_reload = True
            if needs_reload:
                dlg.reload_from_settings(current_settings, initial_section=initial_section)
                dlg_prepare_mode = "reload"
            else:
                dlg_prepare_mode = "reuse_no_reload"
        else:
            dlg_prepare_mode = "reuse"
        dlg_prepare_ms = int((time.perf_counter() - dlg_prepare_started_at) * 1000)
        _LOGGER.info(
            "Settings open prepare: %sms mode=%s section=%s",
            dlg_prepare_ms,
            dlg_prepare_mode,
            str(initial_section or "").strip() or "default",
        )
        if hasattr(dlg, "reset_to_defaults_requested"):
            try:
                dlg.reset_to_defaults_requested = False
            except Exception:
                pass
        if hasattr(dlg, "prepare_for_open"):
            try:
                dlg.prepare_for_open()
            except Exception:
                _LOGGER.exception("Failed to prepare settings dialog before open")
        self.apply_language()
        exec_started_at = time.perf_counter()
        result = dlg.exec()
        exec_ms = int((time.perf_counter() - exec_started_at) * 1000)
        _LOGGER.info("Settings dialog exec duration: %sms result=%s", exec_ms, "accepted" if result else "rejected")
        if result:
            if getattr(dlg, "reset_to_defaults_requested", False):
                self.reset_settings_to_default_and_close()
                return
            current_settings = dict(self.settings)
            next_settings = dlg.get_settings()
            if next_settings == current_settings:
                _LOGGER.info("Settings accepted with no changes; skipping apply/save")
                return

            def _apply_after_dialog_close() -> None:
                apply_started_at = time.perf_counter()
                app = QApplication.instance()
                prev_quit_on_last: bool | None = None
                was_visible = self.isVisible()
                was_minimized = self.isMinimized()
                was_fullscreen = bool(self.windowState() & Qt.WindowState.WindowFullScreen)
                was_maximized = bool(self.windowState() & Qt.WindowState.WindowMaximized)
                try:
                    if app is not None:
                        prev_quit_on_last = app.quitOnLastWindowClosed()
                        app.setQuitOnLastWindowClosed(False)
                    self._suspend_layout_autosave = True
                    self._suppress_restart_after_settings_apply = True
                    self.settings = next_settings
                    apply_settings_started_at = time.perf_counter()
                    self.apply_settings()
                    # One-time post-save-close icon cache reset so recolored SVGs refresh
                    # immediately in the current frame.
                    try:
                        self._last_applied_icon_signature = None
                        if hasattr(self, "_apply_main_toolbar_icons"):
                            self._apply_main_toolbar_icons()
                        if hasattr(self, "_apply_markdown_icons"):
                            self._apply_markdown_icons()
                        if hasattr(self, "_apply_format_icons"):
                            self._apply_format_icons()
                        if hasattr(self, "_apply_ai_feature_icons"):
                            self._apply_ai_feature_icons()
                        ai_dock = getattr(self, "ai_chat_dock", None)
                        if ai_dock is not None and hasattr(ai_dock, "_icon_cache"):
                            ai_dock._icon_cache.clear()
                            if hasattr(ai_dock, "_refresh_quick_action_icons"):
                                ai_dock._refresh_quick_action_icons()
                    except Exception:
                        _LOGGER.exception("Post-settings one-time icon refresh failed")
                    if was_visible and not self.isVisible():
                        if was_minimized:
                            self.showMinimized()
                        elif was_fullscreen:
                            self.showFullScreen()
                        elif was_maximized:
                            self.showMaximized()
                        else:
                            self.showNormal()
                        if not was_minimized:
                            self.raise_()
                            self.activateWindow()
                    apply_settings_ms = int((time.perf_counter() - apply_settings_started_at) * 1000)
                    save_started_at = time.perf_counter()
                    self.save_settings_to_disk()
                    save_enqueue_ms = int((time.perf_counter() - save_started_at) * 1000)
                    total_apply_ms = int((time.perf_counter() - apply_started_at) * 1000)
                    _LOGGER.info(
                        "Settings post-OK apply/save: total=%sms apply_settings=%sms save_call=%sms",
                        total_apply_ms,
                        apply_settings_ms,
                        save_enqueue_ms,
                    )
                    self.log_event("Info", "Settings applied and saved")
                except Exception as exc:
                    _LOGGER.exception("Failed applying settings from preferences dialog")
                    QMessageBox.critical(
                        self,
                        "Apply Settings Failed",
                        f"An error occurred while applying settings.\n\n{exc}",
                    )
                finally:
                    self._suppress_restart_after_settings_apply = False
                    self._suspend_layout_autosave = False
                    if app is not None and prev_quit_on_last is not None:
                        app.setQuitOnLastWindowClosed(prev_quit_on_last)

            # Run after the modal dialog teardown to avoid UI re-entrancy stalls.
            QTimer.singleShot(0, _apply_after_dialog_close)
        total_open_ms = int((time.perf_counter() - open_started_at) * 1000)
        _LOGGER.info("Settings open flow total: %sms", total_open_ms)

    def _prewarm_settings_dialog_cache(self) -> None:
        if bool(getattr(self, "_settings_dialog_prewarm_started", False)):
            return
        self._settings_dialog_prewarm_started = True
        started_at = time.perf_counter()
        mode = "noop"
        try:
            dlg = getattr(self, "_settings_dialog_cached", None)
            if dlg is None:
                dlg = SidebarSettingsDialog(self, self.settings, initial_section=None)
                self._settings_dialog_cached = dlg
                mode = "create"
            elif hasattr(dlg, "reload_from_settings"):
                current_settings = dict(self.settings) if isinstance(self.settings, dict) else {}
                try:
                    if hasattr(dlg, "get_settings") and dlg.get_settings() != current_settings:
                        dlg.reload_from_settings(current_settings, initial_section=None)
                        mode = "reload"
                    else:
                        mode = "reuse_no_reload"
                except Exception:
                    dlg.reload_from_settings(current_settings, initial_section=None)
                    mode = "reload"
            else:
                mode = "reuse"
        except Exception:
            _LOGGER.exception("Settings dialog prewarm failed")
        finally:
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            _LOGGER.info("Settings dialog prewarm: %sms mode=%s", elapsed_ms, mode)

    @staticmethod
    def _settings_change_requires_restart(current: dict[str, Any], updated: dict[str, Any]) -> bool:
        _ = current
        _ = updated
        return False

    @staticmethod
    def _build_restart_command() -> list[str]:
        args = [str(a) for a in sys.argv[1:]]
        if getattr(sys, "frozen", False):
            return [str(Path(sys.executable).resolve()), *args]
        script_candidates: list[Path] = []
        main_file_raw = str(getattr(sys.modules.get("__main__"), "__file__", "") or "").strip()
        if main_file_raw:
            script_candidates.append(Path(main_file_raw).resolve())
        argv0_raw = str(sys.argv[0] or "").strip()
        if argv0_raw and argv0_raw not in {"-c", "-m"}:
            script_candidates.append(Path(argv0_raw).resolve())
        for script in script_candidates:
            if script.exists() and script.is_file():
                return [str(Path(sys.executable).resolve()), str(script), *args]
        return [str(Path(sys.executable).resolve()), *args]

    def _restart_app_after_theme_change(self) -> None:
        _LOGGER.info("Auto-restart after theme change is disabled; explicit reload required")
        if hasattr(self, "show_status_message"):
            self.show_status_message("Theme changes applied. Use Reload App if needed.", 3500)

    def reload_app(self) -> None:
        self._restart_app_with_message("The app will now reload.")

    def _restart_app_with_message(self, message: str) -> None:
        command = self._build_restart_command()
        popen_kwargs: dict[str, Any] = {"cwd": str(Path.cwd())}
        if os.name == "nt":
            detached = int(getattr(subprocess, "DETACHED_PROCESS", 0))
            new_group = int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
            popen_kwargs["creationflags"] = detached | new_group
            popen_kwargs["close_fds"] = True
        else:
            popen_kwargs["start_new_session"] = True
        try:
            subprocess.Popen(command, **popen_kwargs)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.exception("Failed to relaunch app for theme restart")
            QMessageBox.critical(
                self,
                "Restart Failed",
                "App relaunch failed.\n\n"
                f"Command: {' '.join(command)}\nError: {exc}",
            )
            return
        QMessageBox.information(self, "Restarting", message)
        self._request_app_quit("reload_app_requested")

    def _mark_close_trace(self, reason: str) -> None:
        self._pending_close_reason = str(reason or "unknown")
        self._pending_close_stack = "".join(traceback.format_stack(limit=12))
        _LOGGER.info("[CloseTrace] requested reason=%s", self._pending_close_reason)

    def _request_app_quit(self, reason: str) -> None:
        self._mark_close_trace(reason)
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _request_window_close(self, reason: str) -> None:
        self._mark_close_trace(reason)
        self.close()

    def get_shortcut_action_rows(self) -> list[ShortcutActionRow]:
        rows: list[ShortcutActionRow] = []
        for entry in discover_window_actions(self):
            try:
                entry.action.setObjectName(entry.action_id)
                label = f"{entry.label} [{entry.section}]"
            except RuntimeError:
                # Skip stale Python wrappers whose underlying Qt object was deleted.
                continue
            rows.append(ShortcutActionRow(action_id=entry.action_id, label=label, action=entry.action))
        rows.sort(key=lambda r: r.label.lower())
        return rows

    def _capture_default_shortcuts(self) -> None:
        rows = self.get_shortcut_action_rows()
        defaults: dict[str, list[str]] = {}
        for row in rows:
            try:
                seqs = [sequence_to_string(s).strip() for s in row.action.shortcuts() if not s.isEmpty()]
                if not seqs:
                    fallback = row.action.shortcut()
                    if not fallback.isEmpty():
                        seqs = [sequence_to_string(fallback).strip()]
            except RuntimeError:
                continue
            defaults[row.action_id] = [s for s in seqs if s]
        self._default_shortcuts_by_action_id = defaults

    def _resolve_effective_shortcuts(self) -> dict[str, list[str]]:
        profile = str(self.settings.get("shortcut_profile", "vscode"))
        custom_map = self.settings.get("shortcut_map", {})
        base = dict(getattr(self, "_default_shortcuts_by_action_id", {}))
        for aid, seq in PRESET_SHORTCUTS.get(profile, {}).items():
            base[aid] = [str(seq)]
        if isinstance(custom_map, dict):
            for aid, value in custom_map.items():
                if not isinstance(aid, str):
                    continue
                seqs = [sequence_to_string(q).strip() for q in parse_shortcut_value(value) if not q.isEmpty()]
                base[aid] = seqs
        return base

    def apply_shortcut_settings(self) -> None:
        mapping = self._resolve_effective_shortcuts()
        rows = self.get_shortcut_action_rows()
        for row in rows:
            seqs = mapping.get(row.action_id)
            if seqs is None:
                continue
            keyseqs = [QKeySequence(text) for text in seqs if text]
            try:
                row.action.setShortcuts(keyseqs)
            except RuntimeError:
                continue
        if hasattr(self, "configure_action_tooltips"):
            self.configure_action_tooltips()

    def open_shortcut_mapper(self) -> None:
        if not hasattr(self, "_default_shortcuts_by_action_id"):
            self._capture_default_shortcuts()
        rows = self.get_shortcut_action_rows()
        dlg = ShortcutMapperDialog(self, rows, dict(getattr(self, "_default_shortcuts_by_action_id", {})), dict(self.settings))
        dlg.exec()

    def edit_settings_json_in_app(self) -> None:
        self.save_settings_to_disk()
        path = str(self.settings_file)
        if not self._open_file_path(path):
            try:
                text = Path(path).read_text(encoding="utf-8")
            except Exception:
                text = "{}\n"
            self.add_new_tab(text=text, file_path=path, make_current=True)

    def reset_settings_to_default_and_close(self) -> None:
        self.settings = self._build_default_settings()
        self.save_settings_to_disk(synchronous=True)
        self.log_event("Info", "Settings reset to defaults. Closing app.")
        self._request_app_quit("settings_factory_reset")

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if (
            event.key() == Qt.Key_Escape
            and hasattr(self, "focus_mode_action")
            and self.focus_mode_action.isChecked()
            and self.settings.get("focus_allow_escape_exit", True)
        ):
            self.toggle_focus_mode(False)
            event.accept()
            return
        super().keyPressEvent(event)

    def update_window_title(self) -> None:
        tab = self.active_tab()
        if tab is None:
            self.setWindowTitle("Pypad")
            return
        name = tab.current_file if tab.current_file else "Untitled"
        modified_marker = "*" if tab.text_edit.is_modified() else ""
        self.setWindowTitle(f"{modified_marker}{name} - Pypad")

    def _on_modification_changed(self, _changed: bool) -> None:
        sender_editor = self.sender()
        for index in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(index)
            if isinstance(tab, EditorTab) and tab.text_edit is sender_editor:
                self._refresh_tab_title(tab)
                break
        self.update_window_title()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        close_reason = str(getattr(self, "_pending_close_reason", "") or "unknown")
        close_stack = str(getattr(self, "_pending_close_stack", "") or "")
        close_trace_debug = bool(self.settings.get("debug_telemetry_enabled", False)) or str(
            self.settings.get("logging_level", "INFO")
        ).upper() == "DEBUG"
        if close_trace_debug:
            if not close_stack:
                close_stack = "".join(traceback.format_stack(limit=12))
            _LOGGER.info("[CloseTrace] closeEvent reason=%s\n%s", close_reason, close_stack)
        else:
            _LOGGER.info("[CloseTrace] closeEvent reason=%s", close_reason)
        self._pending_close_reason = ""
        self._pending_close_stack = ""
        tabs: list[EditorTab] = []
        for index in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(index)
            if isinstance(tab, EditorTab):
                tabs.append(tab)
        for tab in tabs:
            self.tab_widget.setCurrentWidget(tab)
            if not self.maybe_save_tab(tab):
                self.log_event("Info", "Close cancelled by user")
                event.ignore()
                return
        session_state = self._collect_session_state()
        self.settings["last_session_files"] = session_state["files"]
        self.settings["last_session_unsaved_tabs"] = session_state.get("unsaved_tabs", [])
        self.settings["last_session_active_file"] = session_state["active_file"]
        self.settings["last_session_active_unsaved_index"] = session_state.get("active_unsaved_index", -1)
        self.settings["last_session_workspace_root"] = session_state["workspace_root"]
        self.settings["main_window_mode"] = self._current_window_mode()
        if hasattr(self, "save_current_layout"):
            try:
                self.save_current_layout()
            except Exception as exc:  # noqa: BLE001
                self.log_event("Error", f"Failed to persist layout on close: {exc}")
        self.save_settings_to_disk(synchronous=True)
        try:
            self.reminders_store.save()
        except Exception as exc:  # noqa: BLE001
            self.log_event("Error", f"Failed to save reminders: {exc}")
        try:
            self._run_autosave_cycle()
        except Exception as exc:  # noqa: BLE001
            self.log_event("Error", f"Failed during autosave cycle on shutdown: {exc}")
        try:
            if hasattr(self, "recovery_state_store"):
                self.recovery_state_store.clear_crash_snapshot()
        except Exception:
            pass
        self.log_event("Info", "Application closing")
        if self._session_review_enabled():
            try:
                self.show_session_review(auto=True)
            except Exception:
                pass
        type(self).windows_by_id.pop(self.window_id, None)
        event.accept()

    def _collect_session_state(self) -> dict[str, object]:
        files: list[str] = []
        seen: set[str] = set()
        unsaved_tabs: list[dict[str, object]] = []
        active_unsaved_index = -1
        for index in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(index)
            if not isinstance(tab, EditorTab):
                continue
            if not tab.current_file:
                unsaved_tabs.append(
                    {
                        "text": tab.text_edit.get_text(),
                        "markdown_mode": bool(getattr(tab, "markdown_mode_enabled", False)),
                        "modified": bool(tab.text_edit.is_modified()),
                    }
                )
                if tab is self.active_tab():
                    active_unsaved_index = len(unsaved_tabs) - 1
                continue
            if tab.current_file in seen:
                continue
            seen.add(tab.current_file)
            files.append(tab.current_file)
        active_tab = self.active_tab()
        active_file = active_tab.current_file if active_tab is not None and active_tab.current_file else ""
        workspace_root = str(self.settings.get("workspace_root", "") or "")
        return {
            "version": 2,
            "files": files,
            "unsaved_tabs": unsaved_tabs,
            "active_file": active_file,
            "active_unsaved_index": active_unsaved_index,
            "workspace_root": workspace_root,
        }

    def _save_session_to_path(self, path: str) -> bool:
        payload = self._collect_session_state()
        try:
            Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Save Session", f"Could not save session file:\n{exc}")
            return False
        self.settings["last_session_file_path"] = path
        self.save_settings_to_disk()
        self.show_status_message(f"Session saved: {path}", 3000)
        if self._session_review_enabled() and hasattr(self, "show_session_review"):
            self.show_session_review(auto=True)
        return True

    def save_session(self) -> None:
        path = str(self.settings.get("last_session_file_path", "") or "").strip()
        if not path:
            self.save_session_as()
            return
        self._save_session_to_path(path)

    def save_session_as(self) -> None:
        default_path = str(self.settings.get("last_session_file_path", "") or "").strip()
        if not default_path:
            default_path = str(Path.home() / "pypad.session.json")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Session As",
            default_path,
            "Session Files (*.session.json *.json);;All Files (*.*)",
        )
        if not path:
            return
        self._save_session_to_path(path)

    def _open_session_payload(self, payload: dict[str, object]) -> bool:
        raw_files = payload.get("files", [])
        files = [str(path) for path in raw_files if isinstance(path, str) and path]
        raw_unsaved_tabs = payload.get("unsaved_tabs", [])
        unsaved_tabs = [row for row in raw_unsaved_tabs if isinstance(row, dict)]
        unique_files: list[str] = []
        seen: set[str] = set()
        for path in files:
            if path in seen:
                continue
            seen.add(path)
            unique_files.append(path)

        active_file = str(payload.get("active_file", "") or "")
        try:
            active_unsaved_index = int(payload.get("active_unsaved_index", -1) or -1)
        except Exception:
            active_unsaved_index = -1
        workspace_root = str(payload.get("workspace_root", "") or "")

        for index in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(index)
            if isinstance(tab, EditorTab):
                self.tab_widget.setCurrentWidget(tab)
                if not self.maybe_save_tab(tab):
                    return False

        while self.tab_widget.count():
            tab = self.tab_widget.widget(0)
            if isinstance(tab, EditorTab):
                self._clear_tab_autosave(tab)
            self.tab_widget.removeTab(0)
            if tab is not None:
                tab.deleteLater()

        opened: list[str] = []
        opened_unsaved: list[EditorTab] = []
        for path in unique_files:
            if not Path(path).exists():
                continue
            if self._open_file_path(path):
                tab = self.active_tab()
                if tab is not None and hasattr(self, "_ensure_tab_autosave_meta"):
                    self._ensure_tab_autosave_meta(tab)
                opened.append(path)

        resolved_active_file = active_file if active_file in opened else (opened[0] if opened else "")

        for row in unsaved_tabs:
            text = str(row.get("text", "") or "")
            tab = self.add_new_tab(text=text, file_path=None, make_current=True)
            tab.markdown_mode_enabled = bool(row.get("markdown_mode", False))
            tab.text_edit.set_modified(bool(row.get("modified", bool(text))))
            if hasattr(self, "_sync_markdown_preview_for_active_tab") and tab is self.active_tab():
                self._sync_markdown_preview_for_active_tab()
            opened_unsaved.append(tab)

        if not opened and not opened_unsaved:
            tab = self.add_new_tab(make_current=True)
            if hasattr(self, "_ensure_tab_autosave_meta"):
                self._ensure_tab_autosave_meta(tab)
        elif resolved_active_file:
            for index in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(index)
                if isinstance(tab, EditorTab) and tab.current_file == resolved_active_file:
                    self.tab_widget.setCurrentIndex(index)
                    break
        elif 0 <= active_unsaved_index < len(opened_unsaved):
            target = opened_unsaved[active_unsaved_index]
            target_idx = self.tab_widget.indexOf(target)
            if target_idx >= 0:
                self.tab_widget.setCurrentIndex(target_idx)

        if workspace_root and Path(workspace_root).exists():
            self.settings["workspace_root"] = workspace_root

        self.settings["last_session_files"] = opened
        self.settings["last_session_unsaved_tabs"] = [
            {
                "text": str(row.get("text", "") or ""),
                "markdown_mode": bool(row.get("markdown_mode", False)),
                "modified": bool(row.get("modified", False)),
            }
            for row in unsaved_tabs
        ]
        self.settings["last_session_active_file"] = resolved_active_file
        self.settings["last_session_active_unsaved_index"] = active_unsaved_index
        self.settings["last_session_workspace_root"] = workspace_root
        self.update_window_title()
        self.update_status_bar()
        return True

    def load_session(self) -> None:
        start_dir = str(self.settings.get("last_session_file_path", "") or "").strip()
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Session",
            start_dir,
            "Session Files (*.session.json *.json);;All Files (*.*)",
        )
        if not path:
            return
        try:
            payload_raw = Path(path).read_text(encoding="utf-8")
            payload = json.loads(payload_raw)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Load Session", f"Could not load session file:\n{exc}")
            return
        if not isinstance(payload, dict):
            QMessageBox.warning(self, "Load Session", "Invalid session file format.")
            return
        if not self._open_session_payload(payload):
            return
        self.settings["last_session_file_path"] = path
        self.save_settings_to_disk()
        self.show_status_message(f"Session loaded: {path}", 3000)

    def restore_last_session(self) -> None:
        if not self.settings.get("restore_last_session", True):
            return
        files = [p for p in self.settings.get("last_session_files", []) if isinstance(p, str) and p]
        raw_unsaved_tabs = self.settings.get("last_session_unsaved_tabs", [])
        unsaved_tabs = [row for row in raw_unsaved_tabs if isinstance(row, dict)]
        if not files and not unsaved_tabs:
            return
        active = self.active_tab()
        if (
            active is not None
            and not active.current_file
            and not active.text_edit.is_modified()
            and not active.text_edit.get_text().strip()
        ):
            self.close_tab(self.tab_widget.indexOf(active))
        if active is not None and not active.current_file and hasattr(self, "_ensure_tab_autosave_meta"):
            self._ensure_tab_autosave_meta(active)
        active_file = str(self.settings.get("last_session_active_file", "") or "")
        try:
            active_unsaved_index = int(self.settings.get("last_session_active_unsaved_index", -1) or -1)
        except Exception:
            active_unsaved_index = -1
        workspace_root = str(self.settings.get("last_session_workspace_root", "") or "")
        opened_unsaved: list[EditorTab] = []
        for path in files:
            if Path(path).exists():
                if self._open_file_path(path):
                    tab = self.active_tab()
                    if tab is not None and hasattr(self, "_ensure_tab_autosave_meta"):
                        self._ensure_tab_autosave_meta(tab)
        for row in unsaved_tabs:
            text = str(row.get("text", "") or "")
            tab = self.add_new_tab(text=text, file_path=None, make_current=True)
            tab.markdown_mode_enabled = bool(row.get("markdown_mode", False))
            tab.text_edit.set_modified(bool(row.get("modified", bool(text))))
            if hasattr(self, "_sync_markdown_preview_for_active_tab") and tab is self.active_tab():
                self._sync_markdown_preview_for_active_tab()
            opened_unsaved.append(tab)
        if active_file:
            for index in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(index)
                if isinstance(tab, EditorTab) and tab.current_file == active_file:
                    self.tab_widget.setCurrentIndex(index)
                    break
        elif 0 <= active_unsaved_index < len(opened_unsaved):
            target = opened_unsaved[active_unsaved_index]
            target_idx = self.tab_widget.indexOf(target)
            if target_idx >= 0:
                self.tab_widget.setCurrentIndex(target_idx)
        if workspace_root and Path(workspace_root).exists():
            self.settings["workspace_root"] = workspace_root

    def _serialize_tab_for_reopen(self, tab: EditorTab) -> dict[str, object]:
        return {
            "path": str(tab.current_file or ""),
            "text": tab.text_edit.get_text(),
            "modified": bool(tab.text_edit.is_modified()),
            "markdown_mode": bool(tab.markdown_mode_enabled),
            "encoding": str(tab.encoding or ""),
            "eol_mode": str(tab.eol_mode or ""),
            "favorite": bool(tab.favorite),
            "pinned": bool(tab.pinned),
            "tab_color": str(tab.tab_color or ""),
            "tags": list(tab.tags),
            "bookmarks": sorted(int(line) for line in tab.bookmarks),
            "read_only": bool(tab.read_only),
            "closed_at": datetime.now().isoformat(timespec="seconds"),
        }

    def _push_closed_tab_snapshot(self, tab: EditorTab) -> None:
        history = list(getattr(self, "closed_tabs_history", []))
        history.insert(0, self._serialize_tab_for_reopen(tab))
        self.closed_tabs_history = history[:20]
        self.settings["closed_tab_history"] = list(self.closed_tabs_history)
        self.save_settings_to_disk()

    def _restore_closed_tab_snapshot(self, payload: dict[str, object]) -> bool:
        path = str(payload.get("path", "") or "").strip()
        text = str(payload.get("text", "") or "")
        active = self.active_tab()
        remove_placeholder = bool(
            active is not None
            and self.tab_widget.count() == 1
            and not active.current_file
            and not active.text_edit.is_modified()
            and not active.text_edit.get_text().strip()
        )
        tab = self.add_new_tab(text=text, file_path=path or None, make_current=True)
        tab.markdown_mode_enabled = bool(payload.get("markdown_mode", False))
        tab.encoding = str(payload.get("encoding", "") or tab.encoding or "utf-8")
        tab.eol_mode = str(payload.get("eol_mode", "") or tab.eol_mode or "CRLF")
        tab.favorite = bool(payload.get("favorite", False))
        tab.pinned = bool(payload.get("pinned", False))
        tab.tab_color = str(payload.get("tab_color", "") or "") or None
        tab.tags = [str(item) for item in payload.get("tags", []) if str(item).strip()]
        tab.bookmarks = {int(item) for item in payload.get("bookmarks", []) if str(item).strip()}
        tab.read_only = bool(payload.get("read_only", False))
        tab.text_edit.set_read_only(tab.read_only)
        tab.text_edit.set_modified(bool(payload.get("modified", False)))
        if hasattr(self, "_sync_scintilla_bookmark_markers"):
            self._sync_scintilla_bookmark_markers(tab)
        if hasattr(self, "_refresh_tab_title"):
            self._refresh_tab_title(tab)
        if remove_placeholder and active is not None:
            active_index = self.tab_widget.indexOf(active)
            if active_index >= 0:
                self.tab_widget.removeTab(active_index)
                active.deleteLater()
        self.update_status_bar()
        return True

    def reopen_closed_tab(self) -> None:
        history = list(getattr(self, "closed_tabs_history", []))
        if not history:
            QMessageBox.information(self, "Reopen Closed Tab", "There are no recently closed tabs.")
            return
        payload = history.pop(0)
        self.closed_tabs_history = history
        self.settings["closed_tab_history"] = history
        self._restore_closed_tab_snapshot(payload)
        self.save_settings_to_disk()
        self.update_action_states()
        self.show_status_message("Reopened closed tab.", 2500)

    def show_recently_closed_tabs(self) -> None:
        history = list(getattr(self, "closed_tabs_history", []))
        if not history:
            QMessageBox.information(self, "Recently Closed Tabs", "There are no recently closed tabs.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Recently Closed Tabs")
        dlg.resize(560, 380)
        apply_dialog_theme_from_window(self, dlg)
        layout = QVBoxLayout(dlg)
        listing = QListWidget(dlg)
        for row in history:
            path = str(row.get("path", "") or "").strip()
            title = Path(path).name if path else "Untitled"
            stamp = str(row.get("closed_at", "") or "").strip()
            listing.addItem(f"{title}    {stamp}")
        layout.addWidget(listing)
        buttons = QDialogButtonBox(QDialogButtonBox.Close, Qt.Horizontal, dlg)
        reopen_btn = buttons.addButton("Reopen Selected", QDialogButtonBox.AcceptRole)
        clear_btn = buttons.addButton("Clear History", QDialogButtonBox.DestructiveRole)
        def _reopen_selected() -> None:
            row = listing.currentRow()
            if row < 0 or row >= len(history):
                QMessageBox.information(self, "Recently Closed Tabs", "Select a tab to reopen.")
                return
            payload = history.pop(row)
            self.closed_tabs_history = history
            self.settings["closed_tab_history"] = history
            self._restore_closed_tab_snapshot(payload)
            self.save_settings_to_disk()
            self.update_action_states()
            dlg.accept()

        def _clear_history() -> None:
            self.closed_tabs_history = []
            self.settings["closed_tab_history"] = []
            self.save_settings_to_disk()
            self.update_action_states()
            dlg.accept()

        reopen_btn.clicked.connect(_reopen_selected)
        clear_btn.clicked.connect(_clear_history)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        if listing.count() > 0:
            listing.setCurrentRow(0)
        dlg.exec()

    def _watch_file(self, path: str) -> None:
        watcher = getattr(self, "file_watcher", None)
        if watcher is None:
            return
        if path and path not in watcher.files():
            watcher.addPath(path)

    def _refresh_file_watcher(self) -> None:
        watcher = getattr(self, "file_watcher", None)
        if watcher is None:
            return
        open_files = {
            tab.current_file
            for tab in (self.tab_widget.widget(i) for i in range(self.tab_widget.count()))
            if isinstance(tab, EditorTab) and tab.current_file
        }
        for path in list(watcher.files()):
            if path not in open_files:
                watcher.removePath(path)
        for path in open_files:
            if path not in watcher.files():
                watcher.addPath(path)

    def _on_file_changed(self, path: str) -> None:
        if not path:
            return
        normalized_path = os.path.normcase(os.path.abspath(path))
        suppress_map = getattr(self, "_self_save_suppressed_paths", None)
        if isinstance(suppress_map, dict):
            now = time.monotonic()
            expires_at = float(suppress_map.get(normalized_path, 0.0) or 0.0)
            if expires_at > now:
                return
            stale = [p for p, t in suppress_map.items() if float(t or 0.0) <= now]
            for stale_path in stale:
                suppress_map.pop(stale_path, None)
        tab = None
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, EditorTab) and widget.current_file == path:
                tab = widget
                break
        if tab is None:
            return
        if not Path(path).exists():
            QMessageBox.warning(self, "File Changed", f"File was removed or renamed:\n{path}")
            return
        if tab.text_edit.is_modified():
            msg = QMessageBox(self)
            msg.setWindowTitle("File Changed")
            msg.setIcon(QMessageBox.Warning)
            msg.setText(f'"{Path(path).name}" changed on disk while you also have local edits.')
            msg.setInformativeText("Choose Reload from Disk, Keep My Changes, or Compare.")
            reload_btn = msg.addButton("Reload from Disk", QMessageBox.AcceptRole)
            keep_btn = msg.addButton("Keep My Changes", QMessageBox.RejectRole)
            compare_btn = msg.addButton("Compare", QMessageBox.ActionRole)
            msg.exec()
            clicked = msg.clickedButton()
            if clicked is compare_btn:
                self._show_external_change_diff(tab, path)
                return
            if clicked is not reload_btn:
                return
        self.reload_tab_from_disk(tab)

    def _show_external_change_diff(self, tab: EditorTab, path: str) -> None:
        try:
            disk_text = Path(path).read_text(encoding="utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Compare with Disk", f"Could not read changed file:\n{exc}")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Changed on Disk")
        dlg.resize(980, 620)
        apply_dialog_theme_from_window(self, dlg)
        layout = QVBoxLayout(dlg)
        summary = QLabel(f'Comparing current tab with on-disk file:\n{path}', dlg)
        summary.setWordWrap(True)
        layout.addWidget(summary)
        split = QSplitter(Qt.Horizontal, dlg)
        left = QTextEdit(split)
        right = QTextEdit(split)
        left.setReadOnly(True)
        right.setReadOnly(True)
        left.setPlainText(tab.text_edit.get_text())
        right.setPlainText(disk_text)
        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        layout.addWidget(split, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close, Qt.Horizontal, dlg)
        reload_btn = buttons.addButton("Reload from Disk", QDialogButtonBox.AcceptRole)
        keep_btn = buttons.addButton("Keep My Changes", QDialogButtonBox.ActionRole)
        reload_btn.clicked.connect(lambda: (self.reload_tab_from_disk(tab), dlg.accept()))
        keep_btn.clicked.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        dlg.exec()

    def _bookmark_marker_id(self, tab: EditorTab) -> int | None:
        if not tab.text_edit.is_scintilla:
            return None
        marker_id = tab.bookmark_marker_id
        if marker_id is not None:
            return marker_id
        if hasattr(tab.text_edit.widget, "markerDefine"):
            marker_symbol = getattr(tab.text_edit.widget, "RightArrow", 2)
            marker_id = tab.text_edit.widget.markerDefine(marker_symbol)
            tab.text_edit.widget.setMarkerBackgroundColor(QColor("#ffcc00"), marker_id)
            tab.bookmark_marker_id = marker_id
            return marker_id
        return None

    def _sync_scintilla_bookmark_markers(self, tab: EditorTab) -> None:
        marker_id = self._bookmark_marker_id(tab)
        if marker_id is None or not tab.text_edit.is_scintilla:
            return
        try:
            tab.text_edit.widget.markerDeleteAll(marker_id)
        except Exception:
            pass
        for line in sorted(tab.bookmarks):
            try:
                tab.text_edit.widget.markerAdd(line, marker_id)
            except Exception:
                pass

    def _tab_style_lines(self, tab: EditorTab) -> dict[int, int]:
        raw = getattr(tab, "styled_lines", None)
        if isinstance(raw, dict):
            return raw
        styled: dict[int, int] = {}
        setattr(tab, "styled_lines", styled)
        return styled

    def _style_color(self, style_id: int) -> QColor:
        colors = {
            1: QColor("#9fd3a8"),
            2: QColor("#f6f4a0"),
            3: QColor("#f0a5b5"),
            4: QColor("#7bc67b"),
            5: QColor("#9d8df1"),
            0: QColor("#ff1493"),  # find-mark style
        }
        return colors.get(style_id, QColor("#9fd3a8"))

    def _apply_line_styles(self, tab: EditorTab) -> None:
        if tab.text_edit.is_native_scintilla:
            return
        styled = self._tab_style_lines(tab)
        if not styled:
            # Keep search highlights if enabled.
            if hasattr(tab.text_edit.widget, "clear_background_overlays"):
                tab.text_edit.widget.clear_background_overlays("line_styles")
            if hasattr(self, "_on_search_text_changed"):
                self._on_search_text_changed()
            return
        selections: list[QTextEdit.ExtraSelection] = []
        overlay_ranges: list[tuple[int, int, QColor]] = []
        for line, style_id in styled.items():
            block = tab.text_edit.widget.document().findBlockByNumber(line)
            if not block.isValid():
                continue
            cursor = QTextCursor(block)
            cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            sel = QTextEdit.ExtraSelection()
            sel.cursor = cursor
            color = self._style_color(style_id)
            color.setAlpha(90)
            sel.format.setBackground(color)
            selections.append(sel)
            overlay_ranges.append((int(cursor.selectionStart()), int(cursor.selectionEnd()), color))
        if hasattr(tab.text_edit.widget, "set_background_overlays"):
            tab.text_edit.widget.set_background_overlays("line_styles", overlay_ranges)
            return
        tab.text_edit.widget.setExtraSelections(selections)

    def _record_change_history_line(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        line, _ = tab.text_edit.cursor_position()
        lines = getattr(tab, "change_history_lines", None)
        if not isinstance(lines, list):
            lines = []
            setattr(tab, "change_history_lines", lines)
        if line not in lines:
            lines.append(line)
            lines.sort()
        if len(lines) > 4000:
            del lines[: len(lines) - 4000]

    def toggle_bookmark(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        line, _ = tab.text_edit.cursor_position()
        marker_id = self._bookmark_marker_id(tab)
        if line in tab.bookmarks:
            tab.bookmarks.remove(line)
            if marker_id is not None and tab.text_edit.is_scintilla:
                tab.text_edit.widget.markerDelete(line, marker_id)
        else:
            tab.bookmarks.add(line)
            if marker_id is not None and tab.text_edit.is_scintilla:
                tab.text_edit.widget.markerAdd(line, marker_id)

    def _goto_bookmark(self, forward: bool) -> None:
        tab = self.active_tab()
        if tab is None or not tab.bookmarks:
            return
        line, _ = tab.text_edit.cursor_position()
        sorted_marks = sorted(tab.bookmarks)
        if forward:
            for target in sorted_marks:
                if target > line:
                    tab.text_edit.set_cursor_position(target, 0)
                    return
            tab.text_edit.set_cursor_position(sorted_marks[0], 0)
        else:
            for target in reversed(sorted_marks):
                if target < line:
                    tab.text_edit.set_cursor_position(target, 0)
                    return
            tab.text_edit.set_cursor_position(sorted_marks[-1], 0)

    def goto_next_bookmark(self) -> None:
        self._goto_bookmark(forward=True)

    def goto_prev_bookmark(self) -> None:
        self._goto_bookmark(forward=False)

    def clear_bookmarks(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        marker_id = self._bookmark_marker_id(tab)
        if marker_id is not None and tab.text_edit.is_scintilla:
            for line in list(tab.bookmarks):
                tab.text_edit.widget.markerDelete(line, marker_id)
        tab.bookmarks.clear()

    def show_marks_bookmarks_panel(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        source = tab.text_edit.get_text()
        styled = self._tab_style_lines(tab)

        dlg = QDialog(self)
        dlg.setWindowTitle("Marks/Bookmarks Panel")
        dlg.resize(840, 560)
        apply_dialog_theme_from_window(self, dlg)
        layout = QVBoxLayout(dlg)

        options_row = QHBoxLayout()
        include_bookmarks = QCheckBox("Bookmarks", dlg)
        include_bookmarks.setChecked(True)
        include_marks = QCheckBox("Marks", dlg)
        include_marks.setChecked(True)
        options_row.addWidget(include_bookmarks)
        options_row.addWidget(include_marks)
        options_row.addStretch(1)
        layout.addLayout(options_row)

        table = QTableWidget(dlg)
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Line", "Kind", "Style", "Text"])
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, Qt.Horizontal, dlg)
        jump_btn = QPushButton("Jump", dlg)
        remove_btn = QPushButton("Remove Selected", dlg)
        clear_btn = QPushButton("Clear All Shown", dlg)
        export_btn = QPushButton("Export...", dlg)
        buttons.addButton(jump_btn, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton(remove_btn, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton(clear_btn, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton(export_btn, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        refs_cache = []

        def _refresh() -> None:
            nonlocal refs_cache
            refs_cache = build_line_refs(
                source,
                set(tab.bookmarks),
                dict(styled),
                include_bookmarks=include_bookmarks.isChecked(),
                include_marks=include_marks.isChecked(),
            )
            table.setRowCount(len(refs_cache))
            for row_idx, row in enumerate(refs_cache):
                line_item = QTableWidgetItem(str(row.line_no))
                line_item.setData(Qt.ItemDataRole.UserRole, row_idx)
                table.setItem(row_idx, 0, line_item)
                table.setItem(row_idx, 1, QTableWidgetItem(row.kind))
                table.setItem(row_idx, 2, QTableWidgetItem("" if row.style_id is None else str(row.style_id)))
                table.setItem(row_idx, 3, QTableWidgetItem(row.text))

        def _selected_ref_indices() -> list[int]:
            out: list[int] = []
            for item in table.selectedItems():
                row = item.row()
                if row not in out:
                    out.append(row)
            return sorted(out)

        def _jump() -> None:
            idxs = _selected_ref_indices()
            if not idxs:
                return
            row = refs_cache[idxs[0]]
            tab.text_edit.set_cursor_position(max(0, row.line_no - 1), 0)
            self.update_status_bar()
            self.show_status_message(f"Jumped to line {row.line_no}.", 2000)

        def _remove_selected() -> None:
            idxs = _selected_ref_indices()
            if not idxs:
                return
            for idx in reversed(idxs):
                row = refs_cache[idx]
                line_idx = row.line_no - 1
                if row.kind == "bookmark":
                    tab.bookmarks.discard(line_idx)
                elif row.kind == "mark":
                    styled.pop(line_idx, None)
            self._sync_scintilla_bookmark_markers(tab)
            self._apply_line_styles(tab)
            _refresh()
            self.show_status_message("Selected entries removed.", 2200)

        def _clear_shown() -> None:
            for row in refs_cache:
                line_idx = row.line_no - 1
                if row.kind == "bookmark":
                    tab.bookmarks.discard(line_idx)
                elif row.kind == "mark":
                    styled.pop(line_idx, None)
            self._sync_scintilla_bookmark_markers(tab)
            self._apply_line_styles(tab)
            _refresh()
            self.show_status_message("Displayed marks/bookmarks cleared.", 2200)

        def _export() -> None:
            if not refs_cache:
                QMessageBox.information(self, "Marks/Bookmarks Panel", "Nothing to export.")
                return
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Marks/Bookmarks",
                "marks_bookmarks.txt",
                "Text Files (*.txt);;All Files (*.*)",
            )
            if not path:
                return
            try:
                Path(path).write_text(export_line_refs_text(refs_cache), encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Marks/Bookmarks Panel", f"Export failed:\n{exc}")
                return
            self.show_status_message(f"Exported marks/bookmarks: {path}", 3000)

        include_bookmarks.toggled.connect(lambda _checked: _refresh())
        include_marks.toggled.connect(lambda _checked: _refresh())
        table.itemDoubleClicked.connect(lambda _item: _jump())
        jump_btn.clicked.connect(_jump)
        remove_btn.clicked.connect(_remove_selected)
        clear_btn.clicked.connect(_clear_shown)
        export_btn.clicked.connect(_export)
        _refresh()
        dlg.exec()

    # ---- Search menu extensions (Notepad++-style baseline) ----
    def search_find_in_files(self) -> None:
        self.search_workspace()

    def _set_search_results(self, query: str, items: list[dict[str, object]]) -> None:
        self._search_results_query = query
        self._search_results_items = list(items)
        self._search_results_index = -1 if not items else 0
        self._refresh_search_results_dock()
        self.update_action_states()

    def _init_layout_docks(self) -> None:
        if getattr(self, "_layout_docks_ready", False):
            return
        self._layout_docks_ready = True
        self._build_explorer_dock()
        self._build_search_results_dock()
        self._build_productivity_hub_dialog()
        self._ensure_default_layout()
        for dock_name in ("ai_chat_dock", "markdown_preview_dock"):
            dock = getattr(self, dock_name, None)
            if dock is not None:
                try:
                    dock.visibilityChanged.connect(lambda _v: self._sync_layout_panel_actions())
                except Exception:
                    pass
        self._sync_layout_panel_actions()
        self._install_layout_auto_save()

    def _build_workspace_dock(self) -> None:
        if hasattr(self, "workspace_dock"):
            return
        dock = QDockWidget("Workspace", self)
        dock.setObjectName("workspaceDock")
        dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        container = QWidget(dock)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        header = QHBoxLayout()
        self.workspace_path_label = QLabel("No workspace selected", container)
        self.workspace_set_btn = QPushButton("Set Workspace", container)
        self.workspace_set_btn.clicked.connect(self.open_workspace_folder)
        header.addWidget(self.workspace_path_label, 1)
        header.addWidget(self.workspace_set_btn)
        layout.addLayout(header)

        self.workspace_tree = QTreeView(container)
        self.workspace_tree.setHeaderHidden(False)
        self.workspace_tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.workspace_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.workspace_tree.setDragEnabled(True)
        self.workspace_tree.setAcceptDrops(True)
        self.workspace_tree.setDropIndicatorShown(True)
        self.workspace_tree.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.workspace_tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.workspace_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.workspace_tree.customContextMenuRequested.connect(self._on_workspace_tree_context_menu)
        self.workspace_model = QFileSystemModel(self.workspace_tree)
        self.workspace_model.setRootPath("")
        self.workspace_tree.setModel(self.workspace_model)
        self.workspace_tree.doubleClicked.connect(self._on_workspace_tree_open)
        layout.addWidget(self.workspace_tree, 1)
        dock.setWidget(container)
        self.workspace_dock = dock
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        dock.hide()
        dock.visibilityChanged.connect(lambda _visible: self._sync_layout_panel_actions())
        self._refresh_workspace_dock()
        if hasattr(self, "log_event"):
            self.log_event("Info", "[Startup] Dock created: Workspace")

    def _build_explorer_dock(self) -> None:
        if hasattr(self, "explorer_dock"):
            return
        dock = QDockWidget("Explorer", self)
        dock.setObjectName("explorerDock")
        dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        if hasattr(self, "_install_custom_dock_title_bar"):
            self._install_custom_dock_title_bar(dock, "Explorer", "explorer_dock_title_bar")
        dock.setMinimumWidth(0)
        dock.setMinimumSize(0, 0)
        container = QWidget(dock)
        container.setMinimumSize(0, 0)
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self.explorer_title_label = QLabel("EXPLORER", container)
        self.explorer_title_label.setObjectName("explorerTitleLabel")
        self.explorer_title_label.setMinimumWidth(0)
        self.explorer_title_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        header.addWidget(self.explorer_title_label, 1)

        self.explorer_set_btn = QToolButton(container)
        self.explorer_set_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.explorer_set_btn.setToolTip("Set Workspace")
        self.explorer_set_btn.setIcon(self._svg_icon("document-open"))
        self.explorer_set_btn.clicked.connect(self.open_workspace_folder)
        header.addWidget(self.explorer_set_btn)

        self.explorer_new_file_btn = QToolButton(container)
        self.explorer_new_file_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.explorer_new_file_btn.setToolTip("New File")
        self.explorer_new_file_btn.setIcon(self._svg_icon("document-new"))
        self.explorer_new_file_btn.clicked.connect(self.explorer_new_file)
        header.addWidget(self.explorer_new_file_btn)
        self.explorer_new_folder_btn = QToolButton(container)
        self.explorer_new_folder_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.explorer_new_folder_btn.setToolTip("New Folder")
        self.explorer_new_folder_btn.setIcon(self._svg_icon("document-list"))
        self.explorer_new_folder_btn.clicked.connect(self.explorer_new_folder)
        header.addWidget(self.explorer_new_folder_btn)
        self.explorer_rename_btn = QToolButton(container)
        self.explorer_rename_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.explorer_rename_btn.setToolTip("Rename")
        self.explorer_rename_btn.setIcon(self._svg_icon("edit-find-replace"))
        self.explorer_rename_btn.clicked.connect(self.explorer_rename_selected)
        header.addWidget(self.explorer_rename_btn)
        self.explorer_delete_btn = QToolButton(container)
        self.explorer_delete_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.explorer_delete_btn.setToolTip("Delete")
        self.explorer_delete_btn.setIcon(self._standard_style_icon("SP_TrashIcon"))
        self.explorer_delete_btn.clicked.connect(self.explorer_delete_selected)
        header.addWidget(self.explorer_delete_btn)
        layout.addLayout(header)

        self.explorer_path_label = QLabel("No workspace selected", container)
        self.explorer_path_label.setMinimumWidth(0)
        self.explorer_path_label.setObjectName("explorerPathLabel")
        self.explorer_path_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.explorer_path_label)

        self.explorer_tree = QTreeView(container)
        self.explorer_tree.setHeaderHidden(True)
        self.explorer_tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.explorer_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.explorer_tree.setAlternatingRowColors(False)
        self.explorer_tree.setDragEnabled(True)
        self.explorer_tree.setAcceptDrops(True)
        self.explorer_tree.setDropIndicatorShown(True)
        self.explorer_tree.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.explorer_tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.explorer_tree.setAnimated(True)
        self.explorer_tree.setUniformRowHeights(True)
        self.explorer_tree.setIndentation(14)
        self.explorer_tree.setExpandsOnDoubleClick(True)
        self.explorer_tree.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.explorer_tree.setMinimumWidth(0)
        self.explorer_tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.explorer_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.explorer_tree.customContextMenuRequested.connect(self._on_explorer_tree_context_menu)
        self.explorer_model = QFileSystemModel(self.explorer_tree)
        self.explorer_model.setIconProvider(self._ExplorerIconProvider(self))
        self.explorer_model.setRootPath("")
        self.explorer_tree.setModel(self.explorer_model)
        self.explorer_tree.setItemDelegate(self._ExplorerItemDelegate(self.explorer_tree, self))
        self.explorer_tree.doubleClicked.connect(self._on_explorer_tree_open)
        self.explorer_tree.setObjectName("explorerTree")
        self._apply_explorer_theme()
        layout.addWidget(self.explorer_tree, 1)
        dock.setWidget(container)
        self.explorer_dock = dock
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        dock.hide()
        dock.visibilityChanged.connect(lambda _visible: self._sync_layout_panel_actions())
        self._install_explorer_shortcuts()
        self._refresh_explorer_dock()
        if hasattr(self, "log_event"):
            self.log_event("Info", "[Startup] Dock created: Explorer")

    def _refresh_workspace_dock(self) -> None:
        root = str(self.settings.get("workspace_root", "") or "").strip()
        if hasattr(self, "workspace_dock") and hasattr(self, "workspace_path_label") and hasattr(self, "workspace_tree"):
            if not root or not Path(root).exists():
                self.workspace_path_label.setText("No workspace selected")
                self.workspace_tree.setRootIndex(self.workspace_model.index(""))
            else:
                self.workspace_path_label.setText(f"{root}{self._workspace_git_status_suffix(root)}")
                self.workspace_model.setRootPath(root)
                self.workspace_tree.setRootIndex(self.workspace_model.index(root))
                for col in range(1, self.workspace_model.columnCount()):
                    self.workspace_tree.hideColumn(col)
        self._refresh_explorer_dock()

    def _refresh_explorer_dock(self) -> None:
        if not hasattr(self, "explorer_dock"):
            return
        self._apply_explorer_theme()
        # Reattach icon provider so icons re-render with current theme tint.
        try:
            self.explorer_model.setIconProvider(self._ExplorerIconProvider(self))
        except Exception:
            pass
        root = str(self.settings.get("workspace_root", "") or "").strip()
        if not root or not Path(root).exists():
            self.explorer_path_label.setText("No workspace selected")
            self.explorer_tree.setRootIndex(self.explorer_model.index(""))
            return
        self.explorer_path_label.setText(f"{root}{self._workspace_git_status_suffix(root)}")
        self.explorer_model.setRootPath(root)
        self.explorer_tree.setRootIndex(self.explorer_model.index(root))
        for col in range(1, self.explorer_model.columnCount()):
            self.explorer_tree.hideColumn(col)

    def _apply_explorer_theme(self) -> None:
        if not hasattr(self, "explorer_tree"):
            return
        tokens = build_tokens_from_settings(self.settings)
        bg = QColor(tokens.input_bg)
        fg = QColor(tokens.text)
        if bg.isValid() and fg.isValid():
            pal = self.explorer_tree.palette()
            pal.setColor(self.explorer_tree.backgroundRole(), bg)
            pal.setColor(self.explorer_tree.foregroundRole(), fg)
            self.explorer_tree.setPalette(pal)
            self.explorer_tree.viewport().setPalette(pal)
        self.explorer_tree.setStyleSheet(
            f"""
            QTreeView#explorerTree {{
                border: none;
                padding: 0px;
                show-decoration-selected: 1;
                background: {tokens.input_bg};
                color: {tokens.text};
                selection-background-color: {tokens.accent};
                selection-color: {tokens.text_on_accent};
            }}
            QLabel#explorerTitleLabel {{
                font-weight: 600;
                letter-spacing: 0.5px;
                color: {tokens.text};
            }}
            QLabel#explorerPathLabel {{
                color: {tokens.text_muted};
                padding-left: 2px;
            }}
            QTreeView#explorerTree::item {{
                height: 20px;
                padding-left: 2px;
                color: {tokens.text};
            }}
            QTreeView#explorerTree::item:selected {{
                border-radius: 4px;
            }}
            QTreeView#explorerTree::branch {{
                background: transparent;
            }}
            QTreeView#explorerTree::branch:has-siblings:!adjoins-item,
            QTreeView#explorerTree::branch:has-siblings:adjoins-item,
            QTreeView#explorerTree::branch:!has-children:!has-siblings:adjoins-item {{
                border-image: none;
                image: none;
            }}
            """
        )

    def _explorer_icon_name_for_info(self, info: QFileInfo) -> str:
        if info.isDir():
            return "document-list"
        suffix = str(info.suffix() or "").lower()
        mapping = {
            "py": "file-python",
            "js": "file-javascript",
            "ts": "file-typescript",
            "tsx": "file-typescript",
            "json": "file-json",
            "md": "file-markdown",
            "txt": "file-text",
            "xml": "file-xml",
            "yaml": "file-yaml",
            "yml": "file-yaml",
            "html": "file-html",
            "css": "file-css",
            "cpp": "file-cpp",
            "c": "file-c",
            "cs": "file-csharp",
            "java": "file-java",
            "go": "file-go",
            "rs": "file-rust",
            "php": "file-php",
            "rb": "file-ruby",
            "lua": "file-lua",
            "sql": "file-sql",
            "sh": "file-shell",
            "ps1": "file-powershell",
            "csv": "file-csv",
            "tsv": "file-tsv",
            "log": "file-log",
            "kt": "file-kotlin",
            "swift": "file-swift",
            "bat": "file-batch",
            "conf": "file-config",
            "ini": "file-config",
            "toml": "file-config",
            "svg": "file-generic",
            "png": "file-generic",
            "jpg": "file-generic",
            "jpeg": "file-generic",
        }
        return mapping.get(suffix, "file-generic")

    def _on_workspace_tree_open(self, index) -> None:
        if not hasattr(self, "workspace_model"):
            return
        path = self.workspace_model.filePath(index)
        if path and Path(path).is_file():
            self._open_file_path(path)

    def _on_explorer_tree_open(self, index) -> None:
        if not hasattr(self, "explorer_model"):
            return
        path = self.explorer_model.filePath(index)
        if path and Path(path).is_file():
            self._open_file_path(path)

    def _workspace_git_status_suffix(self, root: str) -> str:
        try:
            cp = subprocess.run(
                ["git", "-C", root, "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
            if cp.returncode != 0:
                return ""
            added = modified = deleted = untracked = 0
            for raw in cp.stdout.splitlines():
                code = raw[:2]
                if "A" in code:
                    added += 1
                if "M" in code:
                    modified += 1
                if "D" in code:
                    deleted += 1
                if code == "??":
                    untracked += 1
            total = added + modified + deleted + untracked
            if total <= 0:
                return " [git: clean]"
            return f" [git: +{added} ~{modified} -{deleted} ?{untracked}]"
        except Exception:
            return ""

    def _workspace_tree_path_from_index(self, index) -> str:
        if not hasattr(self, "workspace_model"):
            return ""
        try:
            return str(self.workspace_model.filePath(index) or "")
        except Exception:
            return ""

    def _explorer_tree_path_from_index(self, index) -> str:
        if not hasattr(self, "explorer_model"):
            return ""
        try:
            return str(self.explorer_model.filePath(index) or "")
        except Exception:
            return ""

    def _selected_explorer_path(self) -> str:
        if not hasattr(self, "explorer_tree"):
            return ""
        index = self.explorer_tree.currentIndex()
        path = self._explorer_tree_path_from_index(index)
        if path:
            return path
        root = str(self.settings.get("workspace_root", "") or "").strip()
        return root

    def _explorer_target_dir(self) -> Path | None:
        path = self._selected_explorer_path().strip()
        if not path:
            return None
        selected = Path(path)
        return selected if selected.is_dir() else selected.parent

    def _on_workspace_tree_context_menu(self, pos: QPoint) -> None:
        if not hasattr(self, "workspace_tree"):
            return
        index = self.workspace_tree.indexAt(pos)
        selected_path = self._workspace_tree_path_from_index(index)
        workspace_root = str(self.settings.get("workspace_root", "") or "").strip()
        if not workspace_root:
            return
        if not selected_path:
            selected_path = workspace_root
        selected = Path(selected_path)
        target_dir = selected if selected.is_dir() else selected.parent

        menu = QMenu(self)
        new_file_action = menu.addAction("New File...")
        new_folder_action = menu.addAction("New Folder...")
        rename_action = menu.addAction("Rename...")
        delete_action = menu.addAction("Delete")
        menu.addSeparator()
        copy_path_action = menu.addAction("Copy Path")
        open_explorer_action = menu.addAction("Open in Explorer")
        refresh_action = menu.addAction("Refresh")
        rename_action.setEnabled(selected.exists())
        delete_action.setEnabled(selected.exists() and selected != Path(workspace_root))
        copy_path_action.setEnabled(selected.exists())
        open_explorer_action.setEnabled(selected.exists())

        chosen = menu.exec(self.workspace_tree.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == new_file_action:
            name, ok = QInputDialog.getText(self, "New File", "File name:", text="new_file.txt")
            if not ok or not name.strip():
                return
            path = target_dir / name.strip()
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch(exist_ok=False)
            except Exception as exc:
                QMessageBox.warning(self, "Workspace", f"Could not create file:\n{exc}")
                return
            self._refresh_workspace_dock()
            self._open_file_path(str(path))
            return
        if chosen == new_folder_action:
            name, ok = QInputDialog.getText(self, "New Folder", "Folder name:", text="new_folder")
            if not ok or not name.strip():
                return
            path = target_dir / name.strip()
            try:
                path.mkdir(parents=True, exist_ok=False)
            except Exception as exc:
                QMessageBox.warning(self, "Workspace", f"Could not create folder:\n{exc}")
                return
            self._refresh_workspace_dock()
            return
        if chosen == rename_action:
            old_name = selected.name
            name, ok = QInputDialog.getText(self, "Rename", "New name:", text=old_name)
            if not ok or not name.strip() or name.strip() == old_name:
                return
            new_path = selected.parent / name.strip()
            try:
                selected.rename(new_path)
            except Exception as exc:
                QMessageBox.warning(self, "Workspace", f"Could not rename:\n{exc}")
                return
            self._refresh_workspace_dock()
            return
        if chosen == delete_action:
            ret = QMessageBox.question(
                self,
                "Delete",
                f"Delete '{selected.name}'?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                return
            try:
                if selected.is_dir():
                    shutil.rmtree(selected)
                else:
                    selected.unlink(missing_ok=True)
            except Exception as exc:
                QMessageBox.warning(self, "Workspace", f"Could not delete:\n{exc}")
                return
            self._refresh_workspace_dock()
            return
        if chosen == copy_path_action:
            QApplication.clipboard().setText(str(selected))
            return
        if chosen == open_explorer_action:
            try:
                os.startfile(str(selected if selected.is_dir() else selected.parent))
            except Exception as exc:
                QMessageBox.warning(self, "Workspace", f"Could not open location:\n{exc}")
            return
        if chosen == refresh_action:
            self._refresh_workspace_dock()

    def _on_explorer_tree_context_menu(self, pos: QPoint) -> None:
        if not hasattr(self, "explorer_tree"):
            return
        index = self.explorer_tree.indexAt(pos)
        selected_path = self._explorer_tree_path_from_index(index)
        workspace_root = str(self.settings.get("workspace_root", "") or "").strip()
        if not workspace_root:
            return
        if not selected_path:
            selected_path = workspace_root
        selected = Path(selected_path)

        menu = QMenu(self)
        edit_action = menu.addAction(self._svg_icon("document-open"), "Edit/Open")
        reveal_action = menu.addAction(self._standard_style_icon("SP_DirOpenIcon"), "Reveal in File Explorer")
        shell_menu_action = menu.addAction(self._standard_style_icon("SP_DirOpenIcon"), "Open Shell Menu")
        menu.addSeparator()
        new_file_action = menu.addAction(self._svg_icon("document-new"), "New File")
        new_folder_action = menu.addAction(self._svg_icon("document-list"), "New Folder")
        rename_action = menu.addAction(self._svg_icon("edit-find-replace"), "Rename")
        delete_action = menu.addAction(self._standard_style_icon("SP_TrashIcon"), "Delete")
        menu.addSeparator()
        copy_action = menu.addAction(self._svg_icon("edit-copy"), "Copy")
        cut_action = menu.addAction(self._svg_icon("edit-cut"), "Cut")
        paste_action = menu.addAction(self._svg_icon("edit-paste"), "Paste")
        copy_path_action = menu.addAction("Copy Path")
        menu.addSeparator()
        refresh_action = menu.addAction("Refresh")
        edit_action.setEnabled(selected.exists() and selected.is_file())
        rename_action.setEnabled(selected.exists())
        delete_action.setEnabled(selected.exists() and selected != Path(workspace_root))
        copy_action.setEnabled(selected.exists())
        cut_action.setEnabled(selected.exists() and selected != Path(workspace_root))
        paste_action.setEnabled(bool(getattr(self, "_explorer_clipboard", {}).get("paths")))
        copy_path_action.setEnabled(selected.exists())
        reveal_action.setEnabled(selected.exists())
        shell_menu_action.setEnabled(selected.exists())

        chosen = menu.exec(self.explorer_tree.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == edit_action:
            self.explorer_edit_selected()
        elif chosen == reveal_action:
            self.explorer_reveal_selected()
        elif chosen == shell_menu_action:
            self.explorer_open_shell_menu()
        elif chosen == new_file_action:
            self.explorer_new_file()
        elif chosen == new_folder_action:
            self.explorer_new_folder()
        elif chosen == rename_action:
            self.explorer_rename_selected()
        elif chosen == delete_action:
            self.explorer_delete_selected()
        elif chosen == copy_action:
            self.explorer_copy_selected()
        elif chosen == cut_action:
            self.explorer_cut_selected()
        elif chosen == paste_action:
            self.explorer_paste()
        elif chosen == copy_path_action:
            QApplication.clipboard().setText(str(selected))
        elif chosen == refresh_action:
            self._refresh_explorer_dock()

    def _install_explorer_shortcuts(self) -> None:
        if not hasattr(self, "explorer_tree"):
            return
        self._explorer_shortcuts = []
        entries = [
            ("F2", self.explorer_rename_selected),
            ("Delete", self.explorer_delete_selected),
            ("Ctrl+C", self.explorer_copy_selected),
            ("Ctrl+X", self.explorer_cut_selected),
            ("Ctrl+V", self.explorer_paste),
            ("Ctrl+E", self.explorer_edit_selected),
            ("Alt+R", self.explorer_reveal_selected),
            ("Alt+S", self.explorer_open_shell_menu),
            ("Alt+N", self.explorer_new_file),
            ("Alt+Shift+N", self.explorer_new_folder),
        ]
        for key, handler in entries:
            shortcut = QShortcut(QKeySequence(key), self.explorer_tree)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(handler)
            self._explorer_shortcuts.append(shortcut)

    def explorer_new_file(self) -> None:
        target_dir = self._explorer_target_dir()
        if target_dir is None:
            return
        name, ok = QInputDialog.getText(self, "Explorer: New File", "File name:", text="new_file.txt")
        if not ok or not name.strip():
            return
        path = target_dir / name.strip()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=False)
        except Exception as exc:
            QMessageBox.warning(self, "Explorer", f"Could not create file:\n{exc}")
            return
        self._refresh_workspace_dock()
        self._open_file_path(str(path))

    def explorer_new_folder(self) -> None:
        target_dir = self._explorer_target_dir()
        if target_dir is None:
            return
        name, ok = QInputDialog.getText(self, "Explorer: New Folder", "Folder name:", text="new_folder")
        if not ok or not name.strip():
            return
        path = target_dir / name.strip()
        try:
            path.mkdir(parents=True, exist_ok=False)
        except Exception as exc:
            QMessageBox.warning(self, "Explorer", f"Could not create folder:\n{exc}")
            return
        self._refresh_workspace_dock()

    def explorer_edit_selected(self) -> None:
        path = self._selected_explorer_path().strip()
        if not path:
            return
        if Path(path).is_file():
            self._open_file_path(path)

    def explorer_reveal_selected(self) -> None:
        path = self._selected_explorer_path().strip()
        if not path:
            return
        selected = Path(path)
        try:
            if os.name == "nt" and selected.exists() and selected.is_file():
                subprocess.run(["explorer", "/select,", str(selected)], check=False)
            else:
                os.startfile(str(selected if selected.is_dir() else selected.parent))
        except Exception as exc:
            QMessageBox.warning(self, "Explorer", f"Could not open location:\n{exc}")

    def explorer_open_shell_menu(self) -> None:
        if not hasattr(self, "explorer_tree"):
            return
        index = self.explorer_tree.currentIndex()
        if not index.isValid():
            return
        rect = self.explorer_tree.visualRect(index)
        pos = rect.center() if not rect.isNull() else QPoint(8, 8)
        try:
            self._on_explorer_tree_context_menu(pos)
        except Exception as exc:
            QMessageBox.warning(self, "Explorer", f"Could not open context menu:\n{exc}")

    def explorer_rename_selected(self) -> None:
        path = self._selected_explorer_path().strip()
        if not path:
            return
        selected = Path(path)
        if not selected.exists():
            return
        old_name = selected.name
        name, ok = QInputDialog.getText(self, "Explorer: Rename", "New name:", text=old_name)
        if not ok or not name.strip() or name.strip() == old_name:
            return
        try:
            selected.rename(selected.parent / name.strip())
        except Exception as exc:
            QMessageBox.warning(self, "Explorer", f"Could not rename:\n{exc}")
            return
        self._refresh_workspace_dock()

    def explorer_delete_selected(self) -> None:
        path = self._selected_explorer_path().strip()
        if not path:
            return
        selected = Path(path)
        workspace_root = Path(str(self.settings.get("workspace_root", "") or "").strip() or ".")
        if not selected.exists() or selected == workspace_root:
            return
        ret = QMessageBox.question(self, "Explorer: Delete", f"Delete '{selected.name}'?", QMessageBox.Yes | QMessageBox.No)
        if ret != QMessageBox.Yes:
            return
        try:
            if selected.is_dir():
                shutil.rmtree(selected)
            else:
                selected.unlink(missing_ok=True)
        except Exception as exc:
            QMessageBox.warning(self, "Explorer", f"Could not delete:\n{exc}")
            return
        self._refresh_workspace_dock()

    def explorer_copy_selected(self) -> None:
        path = self._selected_explorer_path().strip()
        if not path:
            return
        self._explorer_clipboard = {"mode": "copy", "paths": [path]}
        self.show_status_message("Explorer copied selection.", 1800)

    def explorer_cut_selected(self) -> None:
        path = self._selected_explorer_path().strip()
        if not path:
            return
        self._explorer_clipboard = {"mode": "cut", "paths": [path]}
        self.show_status_message("Explorer cut selection.", 1800)

    def explorer_paste(self) -> None:
        clip = getattr(self, "_explorer_clipboard", {})
        if not isinstance(clip, dict):
            return
        paths = clip.get("paths", [])
        if not isinstance(paths, list) or not paths:
            return
        mode = str(clip.get("mode", "copy"))
        target_dir = self._explorer_target_dir()
        if target_dir is None:
            return
        for raw in paths:
            src = Path(str(raw))
            if not src.exists():
                continue
            dst = target_dir / src.name
            if dst.exists():
                QMessageBox.warning(self, "Explorer", f"Destination already exists:\n{dst}")
                continue
            try:
                if mode == "cut":
                    shutil.move(str(src), str(dst))
                elif src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            except Exception as exc:
                QMessageBox.warning(self, "Explorer", f"Paste failed:\n{exc}")
        if mode == "cut":
            self._explorer_clipboard = {"mode": "copy", "paths": []}
        self._refresh_workspace_dock()

    def _build_search_results_dock(self) -> None:
        if hasattr(self, "search_results_dock"):
            return
        dock = QDockWidget("Search Results", self)
        dock.setObjectName("searchResultsDock")
        dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        if hasattr(self, "_install_custom_dock_title_bar"):
            self._install_custom_dock_title_bar(dock, "Search Results", "search_results_dock_title_bar")
        container = QWidget(dock)
        container.setObjectName("searchResultsContainer")
        self.search_results_container = container
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        self.search_results_label = QLabel("No search results", container)
        self.search_results_label.setObjectName("searchResultsLabel")
        layout.addWidget(self.search_results_label)
        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(6)
        self.search_results_filter_edit = QLineEdit(container)
        self.search_results_filter_edit.setObjectName("searchResultsFilterEdit")
        self.search_results_filter_edit.setPlaceholderText("Filter results text/path...")
        self.search_results_filter_edit.setClearButtonEnabled(True)
        self.search_results_filter_edit.setMinimumWidth(110)
        self.search_results_filter_case_checkbox = QCheckBox("Case", container)
        self.search_results_filter_case_checkbox.setObjectName("searchResultsCaseCheckbox")
        self.search_results_filter_case_checkbox.setText("Aa")
        self.search_results_filter_case_checkbox.setToolTip("Case sensitive filter")
        self.search_results_replace_btn = QPushButton("Replace...", container)
        self.search_results_replace_btn.setObjectName("searchResultsReplaceBtn")
        self.search_results_replace_btn.setToolTip("Replace in displayed search results")
        self.search_results_replace_btn.setMinimumWidth(0)
        self._search_results_replace_btn_full_text = "Replace..."
        replace_icon = self._svg_icon("edit-find-replace")
        if not replace_icon.isNull():
            self.search_results_replace_btn.setIcon(replace_icon)
        filter_row.addWidget(self.search_results_filter_edit, 1)
        filter_row.addWidget(self.search_results_filter_case_checkbox)
        filter_row.addWidget(self.search_results_replace_btn)
        layout.addLayout(filter_row)
        self.search_results_list = QListWidget(container)
        self.search_results_list.setObjectName("searchResultsList")
        self.search_results_list.setAlternatingRowColors(False)
        self.search_results_list.itemDoubleClicked.connect(self._open_search_result_from_dock)
        layout.addWidget(self.search_results_list, 1)
        self.search_results_filter_edit.textChanged.connect(self._refresh_search_results_dock)
        self.search_results_filter_case_checkbox.toggled.connect(self._refresh_search_results_dock)
        self.search_results_replace_btn.clicked.connect(self.replace_in_search_results)
        class _SearchResultsResizeFilter(QObject):
            def __init__(self, owner):
                super().__init__(owner)
                self._owner = owner

            def eventFilter(self, _watched, event):  # type: ignore[override]
                if event is not None and event.type() == QEvent.Type.Resize:
                    try:
                        self._owner._update_search_results_compact_mode()
                    except Exception:
                        pass
                return False

        self._search_results_resize_filter = _SearchResultsResizeFilter(self)
        container.installEventFilter(self._search_results_resize_filter)
        dock.setWidget(container)
        self.search_results_dock = dock
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        dock.hide()
        dock.visibilityChanged.connect(lambda _visible: self._sync_layout_panel_actions())
        dock.visibilityChanged.connect(lambda _visible: self._update_search_results_compact_mode())
        dock.dockLocationChanged.connect(lambda _area: self._update_search_results_compact_mode())
        dock.topLevelChanged.connect(lambda _floating: self._update_search_results_compact_mode())
        self._refresh_search_results_dock()
        if hasattr(self, "log_event"):
            self.log_event("Info", "[Startup] Dock created: Search Results")

    def _refresh_search_results_dock(self) -> None:
        if not hasattr(self, "search_results_dock"):
            return
        self._apply_search_results_theme()
        self._update_search_results_compact_mode()
        items = list(getattr(self, "_search_results_items", []))
        filtered_indices = self._filtered_search_result_indices(items)
        query = str(getattr(self, "_search_results_query", "") or "")
        if not items:
            self.search_results_label.setText("No search results")
        else:
            if len(filtered_indices) == len(items):
                self.search_results_label.setText(f"Query: {query} ({len(items)} result(s))")
            else:
                self.search_results_label.setText(
                    f"Query: {query} ({len(filtered_indices)}/{len(items)} filtered)"
                )
        self.search_results_list.clear()
        for idx in filtered_indices:
            item = items[idx]
            path = Path(str(item.get("path", "") or ""))
            line_no = int(item.get("line_no", 1) or 1)
            line_text = str(item.get("line_text", "") or "").strip()
            row = f"{path.name}:{line_no} | {line_text}"
            lw_item = QListWidgetItem(row, self.search_results_list)
            lw_item.setToolTip(str(path))
            lw_item.setData(Qt.UserRole, idx)

    def _apply_search_results_theme(self) -> None:
        if not hasattr(self, "search_results_list"):
            return
        tokens = build_tokens_from_settings(self.settings)
        target = getattr(self, "search_results_container", None) or self.search_results_list
        target.setStyleSheet(
            f"""
            QWidget#searchResultsContainer {{
                background: {tokens.surface_bg};
            }}
            QLabel#searchResultsLabel {{
                color: {tokens.text};
                font-weight: 600;
            }}
            QLineEdit#searchResultsFilterEdit {{
                background: {tokens.input_bg};
                color: {tokens.text};
                border: 1px solid {tokens.border};
                border-radius: {tokens.radius_sm}px;
                padding: 4px 7px;
                min-height: {max(24, int(tokens.input_height) - 2)}px;
            }}
            QLineEdit#searchResultsFilterEdit:focus {{
                border: 1px solid {tokens.accent};
            }}
            QCheckBox#searchResultsCaseCheckbox {{
                color: {tokens.text};
            }}
            QPushButton#searchResultsReplaceBtn {{
                background: {tokens.button_bg};
                color: {tokens.text};
                border: 1px solid {tokens.border};
                border-radius: {tokens.radius_sm}px;
                padding: 4px 8px;
                min-height: {max(24, int(tokens.input_height) - 2)}px;
            }}
            QPushButton#searchResultsReplaceBtn:hover {{
                background: {tokens.toolbar_hover_bg};
            }}
            QPushButton#searchResultsReplaceBtn:pressed {{
                background: {tokens.toolbar_checked_bg};
            }}
            QPushButton#searchResultsReplaceBtn[compactIconOnly="true"] {{
                padding: 0px;
            }}
            QListWidget#searchResultsList {{
                background: {tokens.input_bg};
                color: {tokens.text};
                border: 1px solid {tokens.border};
                border-radius: {tokens.radius_sm}px;
                padding: 2px;
            }}
            QListWidget#searchResultsList::item {{
                padding: 4px 6px;
                border-radius: {tokens.radius_sm}px;
            }}
            QListWidget#searchResultsList::item:selected {{
                background: {tokens.accent};
                color: {tokens.text_on_accent};
            }}
            """
        )

    def _update_search_results_compact_mode(self) -> None:
        btn = getattr(self, "search_results_replace_btn", None)
        edit = getattr(self, "search_results_filter_edit", None)
        case_cb = getattr(self, "search_results_filter_case_checkbox", None)
        dock = getattr(self, "search_results_dock", None)
        if btn is None or edit is None or case_cb is None or dock is None:
            return
        icon_px = max(14, int(self.settings.get("icon_size_px", 18) or 18))
        button_h = max(24, int(build_tokens_from_settings(self.settings).input_height) - 2)
        btn.setIconSize(QSize(icon_px, icon_px))
        # Compact when dock is narrow so controls do not clip/truncate badly.
        compact = dock.width() < 330
        if compact:
            btn.setText("")
            btn.setToolTip("Replace in displayed search results")
            btn.setFixedSize(button_h, button_h)
            btn.setProperty("compactIconOnly", True)
            edit.setPlaceholderText("Filter...")
            case_cb.setText("Aa")
        else:
            btn.setText(str(getattr(self, "_search_results_replace_btn_full_text", "Replace...")))
            btn.setMinimumWidth(0)
            btn.setMinimumHeight(button_h)
            btn.setMaximumHeight(16777215)
            btn.setMaximumWidth(16777215)
            btn.setProperty("compactIconOnly", False)
            edit.setPlaceholderText("Filter results text/path...")
            case_cb.setText("Aa")
        style = btn.style()
        if style is not None:
            style.unpolish(btn)
            style.polish(btn)

    def _filtered_search_result_indices(self, items: list[dict[str, object]]) -> list[int]:
        text = ""
        if hasattr(self, "search_results_filter_edit"):
            text = self.search_results_filter_edit.text().strip()
        if not text:
            return list(range(len(items)))
        case_sensitive = bool(
            hasattr(self, "search_results_filter_case_checkbox")
            and self.search_results_filter_case_checkbox.isChecked()
        )
        needle = text if case_sensitive else text.lower()
        out: list[int] = []
        for idx, item in enumerate(items):
            path = str(item.get("path", "") or "")
            line_text = str(item.get("line_text", "") or "")
            hay = f"{path} {line_text}"
            if not case_sensitive:
                hay = hay.lower()
            if needle in hay:
                out.append(idx)
        return out

    def _open_search_result_from_dock(self, item: QListWidgetItem) -> None:
        idx = item.data(Qt.UserRole)
        items = list(getattr(self, "_search_results_items", []))
        if not isinstance(idx, int) or idx < 0 or idx >= len(items):
            return
        self._search_results_index = idx
        self._open_search_result(items[idx])

    def replace_in_search_results(self) -> None:
        items = list(getattr(self, "_search_results_items", []))
        if not items:
            QMessageBox.information(self, "Replace in Results", "No search results available.")
            return
        target_indices = self._filtered_search_result_indices(items)
        if not target_indices:
            QMessageBox.information(self, "Replace in Results", "No displayed results to replace.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Replace in Displayed Results")
        apply_dialog_theme_from_window(self, dialog)
        layout = QFormLayout(dialog)
        find_edit = QLineEdit(dialog)
        replace_edit = QLineEdit(dialog)
        regex_checkbox = QCheckBox("Use regex", dialog)
        case_checkbox = QCheckBox("Case sensitive", dialog)
        whole_word_checkbox = QCheckBox("Whole word", dialog)
        find_edit.setText(str(getattr(self, "_search_results_query", "") or ""))
        layout.addRow("Find what:", find_edit)
        layout.addRow("Replace with:", replace_edit)
        layout.addRow("", regex_checkbox)
        layout.addRow("", case_checkbox)
        layout.addRow("", whole_word_checkbox)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, dialog)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec() != QDialog.Accepted:
            return

        find_text = find_edit.text()
        replace_text = replace_edit.text()
        if not find_text:
            return
        use_regex = regex_checkbox.isChecked()
        case_sensitive = case_checkbox.isChecked()
        whole_word = whole_word_checkbox.isChecked()
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern_text = find_text if use_regex else re.escape(find_text)
        if whole_word:
            pattern_text = r"\b" + pattern_text + r"\b"
        try:
            pattern = re.compile(pattern_text, flags)
        except re.error as exc:
            QMessageBox.warning(self, "Replace in Results", f"Invalid regular expression:\n{exc}")
            return

        line_map: dict[str, set[int]] = {}
        for idx in target_indices:
            row = items[idx]
            path = str(row.get("path", "") or "")
            line_no = int(row.get("line_no", 1) or 1)
            if not path:
                continue
            line_map.setdefault(path, set()).add(max(1, line_no))

        enc_map = self.settings.get("file_encodings", {})
        open_tabs: dict[str, EditorTab] = {}
        for tab_idx in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(tab_idx)
            if isinstance(tab, EditorTab) and tab.current_file:
                open_tabs[tab.current_file] = tab

        files_changed = 0
        replacements = 0
        failures = 0
        for path, lines_set in line_map.items():
            encoding = "utf-8"
            if isinstance(enc_map, dict):
                encoding = str(enc_map.get(path, "utf-8") or "utf-8")
            try:
                original = Path(path).read_text(encoding=encoding, errors="replace")
            except Exception:
                failures += 1
                continue
            rows = original.splitlines(keepends=True)
            file_changes = 0
            for line_no in sorted(lines_set):
                line_idx = line_no - 1
                if line_idx < 0 or line_idx >= len(rows):
                    continue
                updated, count = pattern.subn(replace_text, rows[line_idx])
                if count:
                    rows[line_idx] = updated
                    file_changes += count
            if not file_changes:
                continue
            try:
                Path(path).write_text("".join(rows), encoding=encoding, errors="replace")
            except Exception:
                failures += 1
                continue
            files_changed += 1
            replacements += file_changes
            tab = open_tabs.get(path)
            if tab is not None and not tab.text_edit.is_modified():
                self.reload_tab_from_disk(tab)

        self.show_status_message(
            f"Replace in results: {replacements} replacement(s) across {files_changed} file(s).",
            3500,
        )
        if failures:
            QMessageBox.warning(self, "Replace in Results", f"Completed with {failures} file error(s).")

    def _build_status_panel_dock(self) -> None:
        if hasattr(self, "status_panel_dock"):
            return
        dock = QDockWidget("Status Panel", self)
        dock.setObjectName("statusPanelDock")
        dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        container = QWidget(dock)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        self.status_panel_position_label = QLabel("Ln -, Col -", container)
        self.status_panel_zoom_label = QLabel("100%", container)
        self.status_panel_eol_label = QLabel("", container)
        self.status_panel_encoding_label = QLabel("UTF8", container)
        self.status_panel_syntax_label = QLabel("Lang Auto", container)
        self.status_panel_breadcrumb_label = QLabel("-", container)
        self.status_panel_selection_stats_label = QLabel("W 0 | C 0", container)
        self.status_panel_ruler_label = QLabel("", container)
        self.status_panel_ai_usage_label = QLabel("AI 0", container)
        self.status_panel_gamification_widget = CompactGamificationWidget(container)
        self.status_panel_gamification_widget.open_requested.connect(self.open_gamification_dashboard)
        for label in (
            self.status_panel_position_label,
            self.status_panel_zoom_label,
            self.status_panel_eol_label,
            self.status_panel_encoding_label,
            self.status_panel_syntax_label,
            self.status_panel_breadcrumb_label,
            self.status_panel_selection_stats_label,
            self.status_panel_ruler_label,
            self.status_panel_ai_usage_label,
        ):
            label.setMargin(1)
            layout.addWidget(label)
        layout.addWidget(self.status_panel_gamification_widget)
        layout.addStretch(1)
        dock.setWidget(container)
        self.status_panel_dock = dock
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        dock.hide()
        dock.visibilityChanged.connect(lambda _visible: self._sync_layout_panel_actions())
        if hasattr(self, "log_event"):
            self.log_event("Info", "[Startup] Dock created: Status Panel")

    def _build_productivity_hub_dialog(self) -> None:
        if hasattr(self, "productivity_hub_dialog"):
            return
        widget = ProductivityHubWidget(self)
        widget.open_dashboard_requested.connect(self.open_gamification_dashboard)
        widget.focus_sprint_requested.connect(self.start_focus_sprint_mode)
        widget.bug_hunt_requested.connect(self.start_bug_hunt_mode)
        widget.craft_tool_requested.connect(self.craft_template_tool)
        widget.routine_requested.connect(self.run_productivity_routine)
        widget.recommended_action_requested.connect(self.run_coach_recommendation)
        if hasattr(self, "_icon"):
            widget.apply_icons(self._icon)
        dialog = ProductivityHubDialog(
            self,
            widget,
            restore_geometry=self._restore_productivity_hub_dialog_geometry,
            save_geometry=self._save_productivity_hub_dialog_geometry,
        )
        dialog.setObjectName("productivityHubDialog")
        dialog.finished.connect(lambda _result: self._sync_layout_panel_actions())
        self.productivity_hub_widget = widget
        self.productivity_hub_dialog = dialog
        self._refresh_productivity_hub()
        if hasattr(self, "log_event"):
            self.log_event("Info", "[Startup] Dialog created: Productivity Hub")

    def _save_productivity_hub_dialog_geometry(self, dialog) -> None:
        if dialog is None:
            return
        try:
            geometry = self._encode_layout_bytes(dialog.saveGeometry())
        except Exception:
            return
        self.settings["productivity_hub_dialog_geometry"] = geometry
        if hasattr(self, "save_settings_to_disk"):
            self.save_settings_to_disk()

    def _restore_productivity_hub_dialog_geometry(self, dialog) -> None:
        if dialog is None:
            return
        raw = str(self.settings.get("productivity_hub_dialog_geometry", "") or "")
        if raw:
            try:
                geo = self._decode_layout_bytes(raw)
                if not geo.isEmpty():
                    dialog.restoreGeometry(geo)
                    return
            except Exception:
                pass
        try:
            host_geo = self.geometry()
            width = min(max(920, int(host_geo.width() * 0.8)), 1260)
            height = min(max(640, int(host_geo.height() * 0.82)), 900)
            dialog.resize(width, height)
            center = host_geo.center()
            dialog.move(center.x() - (dialog.width() // 2), center.y() - (dialog.height() // 2))
        except Exception:
            pass

    def _sync_layout_panel_actions(self) -> None:
        if hasattr(self, "workspace_panel_action") and hasattr(self, "workspace_dock"):
            self.workspace_panel_action.blockSignals(True)
            self.workspace_panel_action.setChecked(self.workspace_dock.isVisible())
            self.workspace_panel_action.blockSignals(False)
        if hasattr(self, "explorer_panel_action") and hasattr(self, "explorer_dock"):
            self.explorer_panel_action.blockSignals(True)
            self.explorer_panel_action.setChecked(self.explorer_dock.isVisible())
            self.explorer_panel_action.blockSignals(False)
        if hasattr(self, "search_results_panel_action") and hasattr(self, "search_results_dock"):
            self.search_results_panel_action.blockSignals(True)
            self.search_results_panel_action.setChecked(self.search_results_dock.isVisible())
            self.search_results_panel_action.blockSignals(False)
        if hasattr(self, "productivity_hub_panel_action") and hasattr(self, "productivity_hub_dialog"):
            self.productivity_hub_panel_action.blockSignals(True)
            self.productivity_hub_panel_action.setChecked(self.productivity_hub_dialog.isVisible())
            self.productivity_hub_panel_action.blockSignals(False)
        if hasattr(self, "editor_panel_action") and hasattr(self, "editor_dock"):
            self.editor_panel_action.blockSignals(True)
            self.editor_panel_action.setChecked(self.editor_dock.isVisible())
            self.editor_panel_action.blockSignals(False)
        if hasattr(self, "lock_layout_action"):
            self.lock_layout_action.blockSignals(True)
            self.lock_layout_action.setChecked(bool(self.settings.get("layout_locked", False)))
            self.lock_layout_action.blockSignals(False)
        self._update_closed_windows_hint()

    def _update_closed_windows_hint(self) -> None:
        hint_text = "You dont have any windows :( Add me again by right clicking anywhere!"
        self._ensure_closed_windows_hint_overlay()
        self._apply_closed_windows_hint_theme()
        docks_to_check = (
            "editor_dock",
            "ai_chat_dock",
            "markdown_preview_dock",
            "explorer_dock",
            "search_results_dock",
            "minimap_dock",
            "outline_dock",
        )
        any_visible = False
        for name in docks_to_check:
            dock = getattr(self, name, None)
            if dock is not None and bool(dock.isVisible()):
                any_visible = True
                break
        label = getattr(self, "_closed_windows_hint_label", None)
        if label is None:
            return
        label.setText(hint_text)
        empty_hint = getattr(self, "empty_tabs_widget", None)
        empty_hint_label = empty_hint.findChild(QLabel, "emptyTabsHint") if empty_hint is not None else None
        if not any_visible:
            label.show()
            label.raise_()
            if empty_hint_label is not None:
                empty_hint_label.hide()
        else:
            label.hide()
            if empty_hint_label is not None:
                empty_hint_label.show()

    def _ensure_closed_windows_hint_overlay(self) -> None:
        label = getattr(self, "_closed_windows_hint_label", None)
        if label is not None:
            return
        label = QLabel(self)
        label.setObjectName("closedWindowsHintLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        label.setGeometry(self.contentsRect())
        label.hide()
        self._closed_windows_hint_label = label

    def _apply_closed_windows_hint_theme(self) -> None:
        label = getattr(self, "_closed_windows_hint_label", None)
        if label is None:
            return
        tokens = build_tokens_from_settings(self.settings)
        label.setStyleSheet(
            f"""
            QLabel#closedWindowsHintLabel {{
                color: {tokens.text_muted};
                font-size: 18px;
                font-weight: 600;
                padding: 14px 20px;
                background: transparent;
            }}
            """
        )

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        label = getattr(self, "_closed_windows_hint_label", None)
        if label is not None:
            label.setGeometry(self.contentsRect())
        if not getattr(self, "_layout_restore_in_progress", False):
            QTimer.singleShot(0, self._rebalance_primary_side_docks)
            self._schedule_layout_auto_save()

    def moveEvent(self, event) -> None:  # type: ignore[override]
        super().moveEvent(event)
        if not getattr(self, "_layout_restore_in_progress", False):
            self._schedule_layout_auto_save()

    def _install_layout_auto_save(self) -> None:
        if getattr(self, "_layout_auto_save_ready", False):
            return
        self._layout_auto_save_ready = True
        self._layout_autosave_watch_widgets = set()
        self._layout_auto_save_timer = QTimer(self)
        self._layout_auto_save_timer.setSingleShot(True)
        self._layout_auto_save_timer.timeout.connect(self._persist_layout_snapshot)
        if hasattr(self, "toolBarAreaChanged"):
            self.toolBarAreaChanged.connect(lambda _tb=None: self._schedule_layout_auto_save())
        for name in (
            "editor_dock",
            "ai_chat_dock",
            "markdown_preview_dock",
            "workspace_dock",
            "explorer_dock",
            "search_results_dock",
            "minimap_dock",
            "outline_dock",
        ):
            dock = getattr(self, name, None)
            if dock is None:
                continue
            self._layout_autosave_watch_widgets.add(dock)
            dock.installEventFilter(self)
            dock.dockLocationChanged.connect(lambda _area, _dock=dock: self._schedule_layout_auto_save())
            dock.topLevelChanged.connect(lambda _floating, _dock=dock: self._schedule_layout_auto_save())
            dock.visibilityChanged.connect(lambda _visible, _dock=dock: self._schedule_layout_auto_save())
        for toolbar_name in ("main_toolbar", "markdown_toolbar", "search_toolbar"):
            toolbar = getattr(self, toolbar_name, None)
            if toolbar is None:
                continue
            self._layout_autosave_watch_widgets.add(toolbar)
            toolbar.installEventFilter(self)
            toolbar.topLevelChanged.connect(lambda _floating, _tb=toolbar: self._schedule_layout_auto_save())
            toolbar.visibilityChanged.connect(lambda _visible, _tb=toolbar: self._schedule_layout_auto_save())

    def _schedule_layout_auto_save(self) -> None:
        if getattr(self, "_layout_restore_in_progress", False):
            return
        if bool(getattr(self, "_suspend_layout_autosave", False)):
            return
        app = QApplication.instance()
        if app is not None and not bool(app.property("app_started")):
            # Ignore startup/layout churn before the app is fully shown.
            return
        if not bool(self.settings.get("layout_auto_save_enabled", True)):
            return
        if not hasattr(self, "_layout_auto_save_timer"):
            return
        self._layout_auto_save_timer.start(1200)

    def _persist_layout_snapshot(self) -> None:
        if getattr(self, "_layout_restore_in_progress", False):
            return
        if hasattr(self, "save_current_layout"):
            try:
                self.save_current_layout(persist=True, show_status=False)
            except Exception as exc:  # noqa: BLE001
                self.log_event("Error", f"Failed to auto-save layout: {exc}")

    def _restore_editor_splitter_sizes(self, tab: EditorTab) -> None:
        sizes = None
        if bool(self.settings.get("per_tab_splitter_sizes_enabled", True)):
            key = self._splitter_key_for_tab(tab)
            by_path = self.settings.get("editor_splitter_sizes_by_path", {})
            if isinstance(by_path, dict):
                sizes = by_path.get(key)
        if sizes is None:
            sizes = self.settings.get("editor_splitter_sizes", None)
        if not isinstance(sizes, list) or not sizes:
            return
        try:
            sizes = [int(x) for x in sizes]
        except Exception:
            return
        if hasattr(tab, "editor_splitter") and tab.editor_splitter.count() == len(sizes):
            tab.editor_splitter.setSizes(sizes)

    def _splitter_key_for_tab(self, tab: EditorTab) -> str:
        if tab.current_file:
            return tab.current_file
        if tab.autosave_id:
            return f"autosave:{tab.autosave_id}"
        title = self._tab_display_name(tab) if hasattr(self, "_tab_display_name") else "Untitled"
        return f"unsaved:{title}"

    def _on_editor_splitter_moved(self, _pos: int, _index: int, splitter: QSplitter) -> None:
        sizes = splitter.sizes()
        if not sizes:
            return
        tab = self.active_tab()
        if tab is not None and bool(self.settings.get("per_tab_splitter_sizes_enabled", True)):
            if not tab.current_file and not tab.autosave_id and hasattr(self, "_ensure_tab_autosave_meta"):
                self._ensure_tab_autosave_meta(tab)
            key = self._splitter_key_for_tab(tab)
            by_path = self.settings.get("editor_splitter_sizes_by_path", {})
            if not isinstance(by_path, dict):
                by_path = {}
            by_path[key] = list(sizes)
            self.settings["editor_splitter_sizes_by_path"] = by_path
        self.settings["editor_splitter_sizes"] = list(sizes)
        self._schedule_layout_auto_save()
    def toggle_workspace_panel(self, checked: bool) -> None:
        # Workspace panel has been removed; keep compatibility by routing to Explorer.
        self.toggle_explorer_panel(bool(checked))

    def toggle_explorer_panel(self, checked: bool) -> None:
        if not hasattr(self, "explorer_dock"):
            return
        self.explorer_dock.setVisible(bool(checked))

    def toggle_search_results_panel(self, checked: bool) -> None:
        if not hasattr(self, "search_results_dock"):
            return
        self.search_results_dock.setVisible(bool(checked))

    def toggle_productivity_hub_panel(self, checked: bool) -> None:
        if not hasattr(self, "productivity_hub_dialog"):
            return
        if checked:
            self._refresh_productivity_hub()
            self.productivity_hub_dialog.show()
            self.productivity_hub_dialog.raise_()
            self.productivity_hub_dialog.activateWindow()
        else:
            self.productivity_hub_dialog.hide()
        self._sync_layout_panel_actions()

    def toggle_editor_panel(self, checked: bool) -> None:
        if not hasattr(self, "editor_dock"):
            return
        self.editor_dock.setVisible(bool(checked))

    def toggle_layout_lock(self, checked: bool) -> None:
        self.settings["layout_locked"] = bool(checked)
        self._apply_layout_lock()
        if hasattr(self, "save_settings_to_disk"):
            self.save_settings_to_disk()
        self.show_status_message("Layout locked." if checked else "Layout unlocked.", 2000)

    def _apply_layout_lock(self) -> None:
        locked = bool(self.settings.get("layout_locked", False))
        docks = []
        for name in (
            "editor_dock",
            "ai_chat_dock",
            "workspace_dock",
            "explorer_dock",
            "search_results_dock",
            "minimap_dock",
            "outline_dock",
        ):
            dock = getattr(self, name, None)
            if dock is not None:
                docks.append(dock)
        if not hasattr(self, "_dock_default_features"):
            self._dock_default_features = {}
        for dock in docks:
            if dock not in self._dock_default_features:
                self._dock_default_features[dock] = dock.features()
        for dock in docks:
            if locked:
                defaults = self._dock_default_features.get(dock, dock.features())
                if defaults & QDockWidget.DockWidgetClosable:
                    dock.setFeatures(QDockWidget.DockWidgetClosable)
                else:
                    dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
            else:
                defaults = self._dock_default_features.get(dock, dock.features())
                dock.setFeatures(defaults)
        for toolbar_name in ("main_toolbar", "markdown_toolbar", "search_toolbar"):
            toolbar = getattr(self, toolbar_name, None)
            if toolbar is None:
                continue
            toolbar.setMovable(not locked)
            toolbar.setFloatable(not locked)
        if hasattr(self, "tab_widget"):
            self.tab_widget.setMovable(not locked)
            tab_bar = self.tab_widget.tabBar()
            if hasattr(tab_bar, "detach_enabled"):
                tab_bar.detach_enabled = not locked

    def _focused_dock_widget(self) -> QDockWidget | None:
        focus = QApplication.focusWidget()
        if focus is not None:
            widget = focus
            while widget is not None:
                if isinstance(widget, QDockWidget):
                    return widget
                widget = widget.parentWidget()
        docks = [d for d in self.findChildren(QDockWidget) if d.isVisible()]
        if len(docks) == 1:
            return docks[0]
        return None

    def _snap_focused_dock(self, area: Qt.DockWidgetArea, label: str) -> None:
        dock = self._focused_dock_widget()
        if dock is None:
            self.show_status_message("Focus a dock panel to snap it.", 2500)
            return
        self.addDockWidget(area, dock)
        dock.raise_()
        self.show_status_message(f'Snapped "{dock.windowTitle()}" to {label}.', 2200)

    def snap_dock_left(self) -> None:
        self._snap_focused_dock(Qt.LeftDockWidgetArea, "left")

    def snap_dock_right(self) -> None:
        self._snap_focused_dock(Qt.RightDockWidgetArea, "right")

    def snap_dock_bottom(self) -> None:
        self._snap_focused_dock(Qt.BottomDockWidgetArea, "bottom")

    def _encode_layout_bytes(self, data: QByteArray) -> str:
        return base64.b64encode(bytes(data)).decode("ascii")

    def _decode_layout_bytes(self, data: str) -> QByteArray:
        try:
            return QByteArray(base64.b64decode(data.encode("ascii")))
        except Exception:
            return QByteArray()

    def _layout_snapshot(self) -> dict[str, Any]:
        snapshot: dict[str, Any] = {
            "state": self._encode_layout_bytes(self.saveState()),
            "geometry": self._encode_layout_bytes(self.saveGeometry()),
            "window_mode": self._current_window_mode(),
        }
        dock_sizes = self._capture_primary_horizontal_dock_sizes()
        if dock_sizes is not None:
            snapshot["primary_dock_sizes"] = dock_sizes
            snapshot["ai_chat_dock_width"] = int(dock_sizes[1])
            try:
                self.log_event("Info", f"[Layout] Saved primary_dock_sizes={dock_sizes}")
            except Exception:
                pass
        return snapshot

    def _current_window_mode(self) -> str:
        state = self.windowState()
        if bool(state & Qt.WindowState.WindowFullScreen):
            return "fullscreen"
        if bool(state & Qt.WindowState.WindowMaximized):
            return "maximized"
        return "normal"

    def _apply_window_mode(self, mode: str) -> None:
        normalized = str(mode or "normal").strip().lower()
        if normalized == "fullscreen":
            self.showFullScreen()
            return
        if normalized == "maximized":
            self.showMaximized()
            return
        if self.isFullScreen():
            self.showNormal()
            return
        state = self.windowState() & ~Qt.WindowState.WindowMinimized
        state = state & ~Qt.WindowState.WindowMaximized
        state = state & ~Qt.WindowState.WindowFullScreen
        self.setWindowState(state)

    def _capture_primary_horizontal_dock_sizes(self) -> list[int] | None:
        editor_dock = getattr(self, "editor_dock", None)
        ai_chat_dock = getattr(self, "ai_chat_dock", None)
        if editor_dock is None or ai_chat_dock is None:
            return None
        try:
            editor_w = int(editor_dock.width())
            ai_w = int(ai_chat_dock.width())
        except Exception:
            return None
        if editor_w <= 0 or ai_w <= 0:
            return None
        return [editor_w, ai_w]

    def _rebalance_primary_side_docks(self) -> None:
        editor_dock = getattr(self, "editor_dock", None)
        if editor_dock is None or not editor_dock.isVisible():
            return
        total_width = max(0, int(self.width()))
        if total_width <= 0:
            return

        ai_chat_dock = getattr(self, "ai_chat_dock", None)
        markdown_preview_dock = getattr(self, "markdown_preview_dock", None)
        visible_side_docks = [
            dock
            for dock in (ai_chat_dock, markdown_preview_dock)
            if dock is not None and dock.isVisible()
        ]
        if not visible_side_docks:
            return

        editor_min = min(max(520, total_width // 2), max(520, total_width - 220))
        side_budget = max(220, total_width - editor_min)
        if len(visible_side_docks) == 1:
            side_limits = {
                ai_chat_dock: min(420, side_budget),
                markdown_preview_dock: min(460, side_budget),
            }
        else:
            per_side_limit = max(180, side_budget // len(visible_side_docks))
            side_limits = {
                ai_chat_dock: min(360, per_side_limit),
                markdown_preview_dock: min(420, per_side_limit),
            }

        side_sizes: dict[object, int] = {}
        remaining_budget = side_budget
        remaining_docks = len(visible_side_docks)
        for dock in visible_side_docks:
            limit = max(180, int(side_limits.get(dock, side_budget)))
            try:
                current = int(dock.width())
            except Exception:
                current = limit
            desired = max(180, min(limit, current if current > 0 else limit))
            min_share = max(180, remaining_budget // max(1, remaining_docks))
            desired = min(desired, remaining_budget - 180 * max(0, remaining_docks - 1))
            desired = max(180, max(min_share, desired) if remaining_budget >= 180 * remaining_docks else desired)
            side_sizes[dock] = desired
            remaining_budget = max(0, remaining_budget - desired)
            remaining_docks -= 1

        dock_order = []
        size_order = []
        if ai_chat_dock is not None and ai_chat_dock.isVisible():
            dock_order.append(ai_chat_dock)
            size_order.append(int(side_sizes.get(ai_chat_dock, 180)))
        dock_order.append(editor_dock)
        editor_size = max(editor_min, total_width - sum(size_order) - sum(int(side_sizes.get(d, 0)) for d in visible_side_docks if d not in dock_order))
        size_order.append(editor_size)
        if markdown_preview_dock is not None and markdown_preview_dock.isVisible():
            dock_order.append(markdown_preview_dock)
            size_order.append(int(side_sizes.get(markdown_preview_dock, 260)))

        try:
            self.resizeDocks(dock_order, size_order, Qt.Orientation.Horizontal)
        except Exception:
            return

    def _apply_primary_horizontal_dock_sizes(self, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            return
        raw = payload.get("primary_dock_sizes")
        if not isinstance(raw, list) or len(raw) != 2:
            return
        try:
            sizes = [max(1, int(raw[0])), max(1, int(raw[1]))]
        except Exception:
            return
        editor_dock = getattr(self, "editor_dock", None)
        ai_chat_dock = getattr(self, "ai_chat_dock", None)
        if editor_dock is None or ai_chat_dock is None:
            return
        try:
            try:
                self.log_event("Info", f"[Layout] Restoring primary_dock_sizes={sizes}")
            except Exception:
                pass
            self.resizeDocks([editor_dock, ai_chat_dock], sizes, Qt.Orientation.Horizontal)
            try:
                applied = [int(editor_dock.width()), int(ai_chat_dock.width())]
                self.log_event("Info", f"[Layout] Applied primary_dock_sizes={applied}")
            except Exception:
                pass
        except Exception:
            return
        self._rebalance_primary_side_docks()
        self._enforce_ai_chat_dock_width(payload)

    def _enforce_ai_chat_dock_width(self, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            return
        raw = payload.get("ai_chat_dock_width")
        if raw is None:
            raw_sizes = payload.get("primary_dock_sizes")
            if isinstance(raw_sizes, list) and len(raw_sizes) == 2:
                raw = raw_sizes[1]
        if raw is None:
            return
        try:
            target = max(1, int(raw))
        except Exception:
            return
        ai_chat_dock = getattr(self, "ai_chat_dock", None)
        if ai_chat_dock is None:
            return

        def _apply_once() -> None:
            dock = getattr(self, "ai_chat_dock", None)
            if dock is None or not dock.isVisible():
                return
            try:
                self.resizeDocks([dock], [target], Qt.Orientation.Horizontal)
            except Exception:
                return
            self._rebalance_primary_side_docks()
            try:
                self.log_event("Info", f"[Layout] Enforce ai_chat_dock_width target={target} current={int(dock.width())}")
            except Exception:
                pass

        _apply_once()
        QTimer.singleShot(100, _apply_once)
        QTimer.singleShot(300, _apply_once)
        QTimer.singleShot(700, _apply_once)

    def _ensure_default_layout(self) -> None:
        layouts = self.settings.get("layout_presets")
        if not isinstance(layouts, dict):
            layouts = {}
        if "Default" not in layouts:
            layouts["Default"] = self._layout_snapshot()
        self.settings["layout_presets"] = layouts
        if not self.settings.get("layout_active"):
            self.settings["layout_active"] = "Default"

    def _ensure_main_window_on_screen(self) -> None:
        # Guard against saved layouts restoring the main window off-screen or tiny.
        try:
            frame_rect = self.frameGeometry()
            geo = self.geometry()
        except Exception:
            return
        if not frame_rect.isValid() and not geo.isValid():
            return

        target_rect = frame_rect if frame_rect.isValid() else geo
        width = max(int(geo.width()), int(target_rect.width()))
        height = max(int(geo.height()), int(target_rect.height()))

        needs_reset = width < 240 or height < 180
        if not needs_reset:
            app = QApplication.instance()
            screens = app.screens() if app is not None else []
            visible_on_any = False
            for screen in screens:
                try:
                    if screen.availableGeometry().intersects(target_rect):
                        visible_on_any = True
                        break
                except Exception:
                    continue
            needs_reset = not visible_on_any

        if not needs_reset:
            return

        app = QApplication.instance()
        primary = app.primaryScreen() if app is not None else None
        if primary is not None:
            avail = primary.availableGeometry()
            new_w = max(800, min(1200, int(avail.width() * 0.75)))
            new_h = max(600, min(900, int(avail.height() * 0.75)))
            self.resize(new_w, new_h)
            center = avail.center()
            self.move(center.x() - (self.width() // 2), center.y() - (self.height() // 2))
        else:
            self.resize(1000, 700)
            self.move(100, 100)
        try:
            self.log_event("Info", "[Startup] Window geometry reset (off-screen/invalid layout)")
        except Exception:
            pass

    def _restore_layout_from_settings(self) -> None:
        if getattr(self, "_layout_restore_in_progress", False):
            return
        name = str(self.settings.get("layout_active", "") or "")
        layouts = self.settings.get("layout_presets", {})
        if not isinstance(layouts, dict) or not name or name not in layouts:
            fallback_mode = str(self.settings.get("main_window_mode", "") or "")
            if fallback_mode:
                try:
                    self.log_event("Info", f"[Startup] Restoring window mode: {fallback_mode} (fallback)")
                except Exception:
                    pass
                QTimer.singleShot(0, lambda m=fallback_mode: self._apply_window_mode(m))
            return
        payload = layouts.get(name, {})
        if not isinstance(payload, dict):
            return
        self._layout_restore_in_progress = True
        try:
            geo = self._decode_layout_bytes(str(payload.get("geometry", "") or ""))
            state = self._decode_layout_bytes(str(payload.get("state", "") or ""))
            if not geo.isEmpty():
                self.restoreGeometry(geo)
            if not state.isEmpty():
                self.restoreState(state)
            self._apply_primary_horizontal_dock_sizes(payload)
            # Qt dock geometry can continue settling right after restoreState/show.
            # Re-apply once more on the next cycle to avoid transient startup widths.
            QTimer.singleShot(0, lambda p=dict(payload): self._apply_primary_horizontal_dock_sizes(p))
            window_mode = str(payload.get("window_mode", "") or self.settings.get("main_window_mode", "") or "")
            if window_mode:
                try:
                    self.log_event("Info", f"[Startup] Restoring window mode: {window_mode}")
                except Exception:
                    pass
                QTimer.singleShot(0, lambda m=window_mode: self._apply_window_mode(m))
        finally:
            self._layout_restore_in_progress = False
        self._ensure_main_window_on_screen()
        self._sync_layout_panel_actions()

    def save_current_layout(self, *, persist: bool = True, show_status: bool = True) -> None:
        name = str(self.settings.get("layout_active", "") or "Default")
        layouts = self.settings.get("layout_presets", {})
        if not isinstance(layouts, dict):
            layouts = {}
        snapshot = self._layout_snapshot()
        existing = layouts.get(name, {})
        if not isinstance(existing, dict):
            existing = {}
        unchanged = (
            str(existing.get("state", "") or "") == str(snapshot.get("state", "") or "")
            and str(existing.get("geometry", "") or "") == str(snapshot.get("geometry", "") or "")
            and str(existing.get("window_mode", "") or "") == str(snapshot.get("window_mode", "") or "")
            and list(existing.get("primary_dock_sizes", []) or []) == list(snapshot.get("primary_dock_sizes", []) or [])
            and int(existing.get("ai_chat_dock_width", 0) or 0) == int(snapshot.get("ai_chat_dock_width", 0) or 0)
        )
        if unchanged:
            self.settings["layout_active"] = name
            self.settings["main_window_mode"] = str(snapshot.get("window_mode", "normal"))
            if show_status:
                self.show_status_message(f'Layout unchanged: "{name}"', 1500)
            return
        layouts[name] = snapshot
        self.settings["layout_presets"] = layouts
        self.settings["layout_active"] = name
        self.settings["main_window_mode"] = str(snapshot.get("window_mode", "normal"))
        if persist and hasattr(self, "save_settings_to_disk"):
            self.save_settings_to_disk()
        if show_status:
            self.show_status_message(f'Layout saved: "{name}"', 2500)

    def save_layout_as(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Layout As", "Layout name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        layouts = self.settings.get("layout_presets", {})
        if not isinstance(layouts, dict):
            layouts = {}
        layouts[name] = self._layout_snapshot()
        self.settings["layout_presets"] = layouts
        self.settings["layout_active"] = name
        if hasattr(self, "save_settings_to_disk"):
            self.save_settings_to_disk()
        self.show_status_message(f'Layout saved: "{name}"', 2500)

    def load_layout(self) -> None:
        layouts = self.settings.get("layout_presets", {})
        if not isinstance(layouts, dict) or not layouts:
            QMessageBox.information(self, "Load Layout", "No saved layouts yet.")
            return
        names = sorted(layouts.keys())
        current = str(self.settings.get("layout_active", "") or "")
        start_idx = max(0, names.index(current)) if current in names else 0
        name, ok = QInputDialog.getItem(self, "Load Layout", "Layout:", names, start_idx, False)
        if not ok or not name:
            return
        self.settings["layout_active"] = name
        self._restore_layout_from_settings()
        if hasattr(self, "save_settings_to_disk"):
            self.save_settings_to_disk()
        self.show_status_message(f'Layout loaded: "{name}"', 2500)

    def reset_layout(self) -> None:
        self._ensure_default_layout()
        self.settings["layout_active"] = "Default"
        self._restore_layout_from_settings()
        if hasattr(self, "save_settings_to_disk"):
            self.save_settings_to_disk()
        self.show_status_message("Layout reset to Default.", 2500)

    def _open_search_result(self, item: dict[str, object]) -> None:
        path = str(item.get("path", "") or "")
        line_no = int(item.get("line_no", 1) or 1)
        if not path:
            return
        if not self._open_file_path(path):
            return
        tab = self.active_tab()
        if tab is None:
            return
        target_line = max(0, line_no - 1)
        tab.text_edit.set_cursor_position(target_line, 0)
        self.update_status_bar()

    def search_next_result(self) -> None:
        items = list(getattr(self, "_search_results_items", []))
        if not items:
            QMessageBox.information(self, "Search Results", "No search results available.")
            return
        idx = int(getattr(self, "_search_results_index", -1))
        idx = (idx + 1) % len(items)
        self._search_results_index = idx
        self._open_search_result(items[idx])

    def search_prev_result(self) -> None:
        items = list(getattr(self, "_search_results_items", []))
        if not items:
            QMessageBox.information(self, "Search Results", "No search results available.")
            return
        idx = int(getattr(self, "_search_results_index", -1))
        if idx < 0:
            idx = 0
        idx = (idx - 1) % len(items)
        self._search_results_index = idx
        self._open_search_result(items[idx])

    def show_search_results_window(self) -> None:
        items = list(getattr(self, "_search_results_items", []))
        if not items:
            QMessageBox.information(self, "Search Results", "No search results available.")
            return
        dlg = QDialog(self)
        query = str(getattr(self, "_search_results_query", "") or "")
        dlg.setWindowTitle("Search Results")
        dlg.resize(900, 540)
        apply_dialog_theme_from_window(self, dlg)
        dlg.setObjectName("searchResultsModal")
        layout = QVBoxLayout(dlg)
        header = QLabel(f"Query: {query} ({len(items)} result(s))", dlg)
        header.setObjectName("searchResultsModalHeader")
        layout.addWidget(header)
        list_widget = QListWidget(dlg)
        list_widget.setObjectName("searchResultsModalList")
        list_widget.setAlternatingRowColors(False)
        for idx, item in enumerate(items):
            path = Path(str(item.get("path", "") or ""))
            line_no = int(item.get("line_no", 1) or 1)
            line_text = str(item.get("line_text", "") or "").strip()
            row = f"{path.name}:{line_no} | {line_text}"
            lw_item = QListWidgetItem(row, list_widget)
            lw_item.setToolTip(str(path))
            lw_item.setData(Qt.UserRole, idx)
        layout.addWidget(list_widget, 1)
        btns = QDialogButtonBox(QDialogButtonBox.Close, Qt.Horizontal, dlg)
        open_btn = QPushButton("Open", dlg)
        open_btn.setObjectName("searchResultsModalOpenBtn")
        open_icon = self._svg_icon("document-open")
        if not open_icon.isNull():
            open_btn.setIcon(open_icon)
        export_btn = QPushButton("Export...", dlg)
        export_btn.setObjectName("searchResultsModalExportBtn")
        btns.addButton(open_btn, QDialogButtonBox.ActionRole)
        btns.addButton(export_btn, QDialogButtonBox.ActionRole)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        tokens = build_tokens_from_settings(self.settings)
        dlg.setStyleSheet(
            dlg.styleSheet()
            + f"""
            QDialog#searchResultsModal QLabel#searchResultsModalHeader {{
                color: {tokens.text};
                font-weight: 600;
            }}
            QDialog#searchResultsModal QListWidget#searchResultsModalList {{
                background: {tokens.input_bg};
                color: {tokens.text};
                border: 1px solid {tokens.border};
                border-radius: {tokens.radius_sm}px;
                padding: 2px;
            }}
            QDialog#searchResultsModal QListWidget#searchResultsModalList::item {{
                padding: 4px 6px;
                border-radius: {tokens.radius_sm}px;
            }}
            QDialog#searchResultsModal QListWidget#searchResultsModalList::item:selected {{
                background: {tokens.accent};
                color: {tokens.text_on_accent};
            }}
            QDialog#searchResultsModal QPushButton#searchResultsModalOpenBtn,
            QDialog#searchResultsModal QPushButton#searchResultsModalExportBtn {{
                background: {tokens.button_bg};
                color: {tokens.text};
                border: 1px solid {tokens.border};
                border-radius: {tokens.radius_sm}px;
                padding: 5px 8px;
            }}
            QDialog#searchResultsModal QPushButton#searchResultsModalOpenBtn:hover,
            QDialog#searchResultsModal QPushButton#searchResultsModalExportBtn:hover {{
                background: {tokens.toolbar_hover_bg};
            }}
            QDialog#searchResultsModal QPushButton#searchResultsModalOpenBtn:pressed,
            QDialog#searchResultsModal QPushButton#searchResultsModalExportBtn:pressed {{
                background: {tokens.toolbar_checked_bg};
            }}
            """
        )

        def _open_selected() -> None:
            current = list_widget.currentItem()
            if current is None:
                return
            idx = current.data(Qt.UserRole)
            if not isinstance(idx, int) or idx < 0 or idx >= len(items):
                return
            self._search_results_index = idx
            self._open_search_result(items[idx])
            dlg.accept()

        def _export_results() -> None:
            default = "search_results.txt"
            path, _ = QFileDialog.getSaveFileName(self, "Export Search Results", default, "Text Files (*.txt)")
            if not path:
                return
            lines = [f"Query: {query}", f"Results: {len(items)}", ""]
            for item in items:
                lines.append(
                    f"{item.get('path','')}:{int(item.get('line_no',1) or 1)} | {str(item.get('line_text','') or '').strip()}"
                )
            try:
                Path(path).write_text("\n".join(lines), encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Search Results", f"Export failed:\n{exc}")
                return
            self.show_status_message(f"Search results exported: {path}", 3000)

        list_widget.itemDoubleClicked.connect(lambda _item: _open_selected())
        open_btn.clicked.connect(_open_selected)
        export_btn.clicked.connect(_export_results)
        list_widget.setCurrentRow(max(0, int(getattr(self, "_search_results_index", 0))))
        dlg.exec()

    def search_select_and_find_next(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        selected = tab.text_edit.selected_text().strip()
        if selected:
            self.last_search_text = selected
        self.edit_find_next()

    def search_select_and_find_previous(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        selected = tab.text_edit.selected_text().strip()
        if selected:
            self.last_search_text = selected
        self.edit_find_previous()

    def search_find_volatile_next(self) -> None:
        self.edit_find_next()

    def search_find_volatile_previous(self) -> None:
        self.edit_find_previous()

    def search_incremental(self) -> None:
        self.show_search_panel()
        if hasattr(self, "search_input"):
            self.search_input.setFocus()

    def search_goto_line(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        total_lines = max(1, len(tab.text_edit.get_text().splitlines()) or 1)
        line, ok = QInputDialog.getInt(self, "Go To", "Line number:", 1, 1, total_lines)
        if not ok:
            return
        tab.text_edit.set_cursor_position(line - 1, 0)
        self.update_status_bar()

    def search_mark(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        text = tab.text_edit.selected_text().strip() or (self.last_search_text or "")
        if not text:
            text, ok = QInputDialog.getText(self, "Mark", "Text to mark:")
            if not ok or not text.strip():
                return
        style_id = 0
        source = tab.text_edit.get_text()
        styled = self._tab_style_lines(tab)
        for i, line in enumerate(source.splitlines()):
            if text in line:
                styled[i] = style_id
        self._apply_line_styles(tab)
        self.show_status_message("Marked search matches.", 2500)

    def search_change_history_next(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        lines = getattr(tab, "change_history_lines", [])
        if not lines:
            return
        cur, _ = tab.text_edit.cursor_position()
        for ln in lines:
            if ln > cur:
                tab.text_edit.set_cursor_position(ln, 0)
                return
        tab.text_edit.set_cursor_position(lines[0], 0)

    def search_change_history_previous(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        lines = getattr(tab, "change_history_lines", [])
        if not lines:
            return
        cur, _ = tab.text_edit.cursor_position()
        for ln in reversed(lines):
            if ln < cur:
                tab.text_edit.set_cursor_position(ln, 0)
                return
        tab.text_edit.set_cursor_position(lines[-1], 0)

    def search_change_history_clear(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        setattr(tab, "change_history_lines", [])
        self.show_status_message("Change history cleared.", 2500)

    def search_style_all_occurrences(self, style_id: int) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        token = tab.text_edit.selected_text().strip()
        if not token:
            token = self.last_search_text or ""
        if not token:
            QMessageBox.information(self, "Style All Occurrences", "Select text or perform Find first.")
            return
        styled = self._tab_style_lines(tab)
        for i, line in enumerate(tab.text_edit.get_text().splitlines()):
            if token in line:
                styled[i] = style_id
        self._apply_line_styles(tab)

    def search_style_one_token(self, style_id: int) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        line, _ = tab.text_edit.cursor_position()
        styled = self._tab_style_lines(tab)
        styled[line] = style_id
        self._apply_line_styles(tab)

    def search_clear_style(self, style_id: int | None = None) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        styled = self._tab_style_lines(tab)
        if style_id is None:
            styled.clear()
        else:
            to_delete = [ln for ln, sid in styled.items() if sid == style_id]
            for ln in to_delete:
                styled.pop(ln, None)
        self._apply_line_styles(tab)

    def search_jump_up_styled(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        styled = self._tab_style_lines(tab)
        if not styled:
            return
        cur, _ = tab.text_edit.cursor_position()
        lines = sorted(styled.keys())
        for ln in reversed(lines):
            if ln < cur:
                tab.text_edit.set_cursor_position(ln, 0)
                return
        tab.text_edit.set_cursor_position(lines[-1], 0)

    def search_jump_down_styled(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        styled = self._tab_style_lines(tab)
        if not styled:
            return
        cur, _ = tab.text_edit.cursor_position()
        lines = sorted(styled.keys())
        for ln in lines:
            if ln > cur:
                tab.text_edit.set_cursor_position(ln, 0)
                return
        tab.text_edit.set_cursor_position(lines[0], 0)

    def search_copy_styled_text(self, style_id: int | None = None) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        styled = self._tab_style_lines(tab)
        if not styled:
            return
        lines = tab.text_edit.get_text().splitlines()
        selected_lines: list[str] = []
        for ln, sid in sorted(styled.items()):
            if style_id is not None and sid != style_id:
                continue
            if 0 <= ln < len(lines):
                selected_lines.append(lines[ln])
        if not selected_lines:
            return
        QApplication.clipboard().setText("\n".join(selected_lines))
        self.show_status_message("Styled text copied.", 2500)

    # ---- Bookmark line operations ----
    def _bookmarked_lines_sorted(self, tab: EditorTab) -> list[int]:
        return sorted(int(x) for x in tab.bookmarks if isinstance(x, int))

    def bookmark_cut_lines(self) -> None:
        tab = self.active_tab()
        if tab is None or tab.text_edit.is_read_only():
            return
        lines = tab.text_edit.get_text().splitlines()
        marks = self._bookmarked_lines_sorted(tab)
        if not marks:
            return
        cut = [lines[i] for i in marks if 0 <= i < len(lines)]
        QApplication.clipboard().setText("\n".join(cut))
        kept = [line for idx, line in enumerate(lines) if idx not in set(marks)]
        tab.text_edit.set_text("\n".join(kept))
        tab.text_edit.set_modified(True)
        tab.bookmarks.clear()
        self._sync_scintilla_bookmark_markers(tab)

    def bookmark_copy_lines(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        lines = tab.text_edit.get_text().splitlines()
        marks = self._bookmarked_lines_sorted(tab)
        if not marks:
            return
        copied = [lines[i] for i in marks if 0 <= i < len(lines)]
        QApplication.clipboard().setText("\n".join(copied))
        self.show_status_message("Bookmarked lines copied.", 2500)

    def bookmark_paste_replace_lines(self) -> None:
        tab = self.active_tab()
        if tab is None or tab.text_edit.is_read_only():
            return
        marks = self._bookmarked_lines_sorted(tab)
        if not marks:
            return
        clip = QApplication.clipboard().text()
        if not clip:
            return
        repl = clip.splitlines()
        lines = tab.text_edit.get_text().splitlines()
        if not lines:
            return
        for i, ln in enumerate(marks):
            if 0 <= ln < len(lines):
                lines[ln] = repl[i] if i < len(repl) else repl[-1]
        tab.text_edit.set_text("\n".join(lines))
        tab.text_edit.set_modified(True)

    def bookmark_remove_lines(self) -> None:
        tab = self.active_tab()
        if tab is None or tab.text_edit.is_read_only():
            return
        marks = set(self._bookmarked_lines_sorted(tab))
        if not marks:
            return
        lines = tab.text_edit.get_text().splitlines()
        kept = [line for i, line in enumerate(lines) if i not in marks]
        tab.text_edit.set_text("\n".join(kept))
        tab.text_edit.set_modified(True)
        tab.bookmarks.clear()
        self._sync_scintilla_bookmark_markers(tab)

    def bookmark_remove_non_bookmarked_lines(self) -> None:
        tab = self.active_tab()
        if tab is None or tab.text_edit.is_read_only():
            return
        marks = set(self._bookmarked_lines_sorted(tab))
        if not marks:
            return
        lines = tab.text_edit.get_text().splitlines()
        kept = [line for i, line in enumerate(lines) if i in marks]
        tab.text_edit.set_text("\n".join(kept))
        tab.text_edit.set_modified(True)
        tab.bookmarks = set(range(len(kept)))
        self._sync_scintilla_bookmark_markers(tab)

    def bookmark_inverse(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        line_count = len(tab.text_edit.get_text().splitlines())
        all_lines = set(range(line_count))
        tab.bookmarks = all_lines.difference(set(tab.bookmarks))
        self._sync_scintilla_bookmark_markers(tab)

    def show_about(self) -> None:
        username = getpass.getuser()
        self.log_event("Info", "Opened About dialog")
        app_mode_text = "You are using the production app." if getattr(sys, "frozen", False) else "You are using the development app."

        # --- Read version from file ---
        version_path = resolve_asset_path("version.txt")
        if version_path is None:
            version = "v?.?.?"  # fallback if missing
        else:
            try:
                version = version_path.read_text(encoding="utf-8").strip()
            except OSError:
                version = "v?.?.?"  # fallback if missing
        capsule_path = str(self.settings.get("pending_update_installer_path", "") or "").strip()
        capsule_version = str(self.settings.get("pending_update_version", "") or "").strip()
        if capsule_path:
            capsule_text = f"{html_escape(capsule_version or 'unknown')} @ {html_escape(capsule_path)}"
        else:
            capsule_text = "none"

        about_box = QMessageBox(self)
        about_box.setWindowTitle("About Pypad")
        about_box.setIcon(QMessageBox.Information)
        about_box.setTextFormat(Qt.RichText)
        about_box.setTextInteractionFlags(Qt.TextBrowserInteraction)
        about_box.setStandardButtons(QMessageBox.Ok)

        # --- Add version info dynamically ---
        about_box.setText(
            f"""
    <a href="easteregg"><b>Pypad</b></a><br>
    Simple Pypad implemented with PySide6<br>
    Version: <b>{version}</b><br><br>
    <b>{html_escape(app_mode_text)}</b><br><br>
    Pending update capsule: <b>{capsule_text}</b><br><br>

    &copy; 2026 Pypad Project<br>
    Inspired by Windows 10 Notepad<br><br>

    <b>This product is registered to:</b><br>
    {username}
    """
        )

        # --- Handle easter egg link ---
        text_label = about_box.findChild(QLabel, "qt_msgbox_label")
        if text_label is not None:
            text_label.setOpenExternalLinks(False)
            text_label.linkActivated.connect(
                lambda link: (
                    about_box.done(0),
                    self.log_event("Info", "About dialog easter egg link clicked"),
                    self.trigger_easter_egg(),
                )
                if link == "easteregg"
                else None
            )

        about_box.exec()

    def show_open_source_licenses(self) -> None:
        self.log_event("Info", "Opened Open Source Licenses dialog")
        dialog = QDialog(self)
        dialog.setWindowTitle("Open Source Licenses")
        dialog.resize(900, 640)
        apply_dialog_theme_from_window(self, dialog)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Installed Python libraries and declared license metadata", dialog))
        splitter = QSplitter(Qt.Horizontal, dialog)
        library_list = QListWidget(splitter)
        library_list.setSelectionMode(QAbstractItemView.SingleSelection)
        output = QTextEdit(splitter)
        output.setReadOnly(True)
        output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        splitter.addWidget(library_list)
        splitter.addWidget(output)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 560])
        layout.addWidget(splitter, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close, Qt.Horizontal, dialog)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        copy_btn = QPushButton("Copy Selected", dialog)
        buttons.addButton(copy_btn, QDialogButtonBox.ActionRole)
        layout.addWidget(buttons)

        rows: list[dict[str, str]] = []
        errors: list[str] = []
        try:
            for dist in importlib_metadata.distributions():
                try:
                    meta = dist.metadata
                    name = str(meta.get("Name") or dist.metadata.get("Summary") or "").strip()
                    if not name:
                        name = str(getattr(dist, "name", "") or "")
                    version = str(getattr(dist, "version", "") or meta.get("Version") or "").strip()
                    license_text = str(meta.get("License") or "").strip()
                    if not license_text:
                        classifiers = [str(v) for v in meta.get_all("Classifier", []) or []]
                        license_classifiers = [c for c in classifiers if c.startswith("License :: ")]
                        license_text = "; ".join(license_classifiers) if license_classifiers else "(not declared)"
                    summary = str(meta.get("Summary") or "").strip() or "(no summary provided)"
                    home_page = str(meta.get("Home-page") or "").strip() or "(not declared)"
                    rows.append(
                        {
                            "name": name or "(unknown)",
                            "version": version or "?",
                            "license": license_text,
                            "summary": summary,
                            "home_page": home_page,
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    errors.append(str(exc))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Open Source Licenses", f"Could not load package metadata:\n{exc}")
            return

        rows.sort(key=lambda item: item["name"].lower())
        for row in rows:
            item = QListWidgetItem(f'{row["name"]} {row["version"]}')
            item.setData(Qt.UserRole, row)
            library_list.addItem(item)

        def _render_selected_preview() -> None:
            current = library_list.currentItem()
            if current is None:
                output.setPlainText("Select a library to preview its license metadata.")
                return
            row = current.data(Qt.UserRole)
            if not isinstance(row, dict):
                output.setPlainText("No metadata available.")
                return
            output.setPlainText(
                "\n".join(
                    [
                        f'Library: {row.get("name", "(unknown)")}',
                        f'Version: {row.get("version", "?")}',
                        f'License: {row.get("license", "(not declared)")}',
                        f'Summary: {row.get("summary", "(no summary provided)")}',
                        f'Home page: {row.get("home_page", "(not declared)")}',
                    ]
                )
            )

        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(output.toPlainText()))
        library_list.currentItemChanged.connect(lambda _curr, _prev: _render_selected_preview())
        if library_list.count() > 0:
            library_list.setCurrentRow(0)
        else:
            output.setPlainText("No installed library metadata found.")
        if errors:
            output.append(f"\n\nMetadata parse warnings: {len(errors)}")
        dialog.exec()

    def _maybe_show_welcome_tutorial(self) -> None:
        if not bool(self.settings.get("onboarding_enabled", True)):
            return
        if self.settings.get("welcome_tutorial_seen", False):
            if bool(self.settings.get("onboarding_contextual_tips_enabled", True)):
                QTimer.singleShot(900, lambda: self._maybe_show_contextual_tip("startup"))
            if bool(self.settings.get("onboarding_next_unlock_prompts_enabled", True)):
                QTimer.singleShot(1400, self._maybe_show_next_unlock_prompt)
                QTimer.singleShot(2100, self._maybe_show_daily_briefing_prompt)
            QTimer.singleShot(2800, self._maybe_show_seasonal_event_prompt)
            return
        self.show_first_time_tutorial()

    def _onboarding_state(self) -> dict[str, Any]:
        state = self.settings.get("onboarding_state")
        if not isinstance(state, dict):
            state = {}
            self.settings["onboarding_state"] = state
        state.setdefault("completed_steps", [])
        state.setdefault("shown_tips", [])
        state.setdefault("unlock_prompt_levels", [])
        return state

    def _onboarding_mark_step(self, step: str) -> None:
        key = str(step or "").strip()
        if not key:
            return
        state = self._onboarding_state()
        completed = {str(x) for x in state.get("completed_steps", [])}
        if key in completed:
            return
        completed.add(key)
        state["completed_steps"] = sorted(completed)
        self.save_settings_to_disk()

    def _onboarding_has_step(self, step: str) -> bool:
        key = str(step or "").strip()
        if not key:
            return False
        state = self._onboarding_state()
        completed = {str(x) for x in state.get("completed_steps", [])}
        return key in completed

    def _onboarding_mark_tip(self, tip_key: str) -> None:
        key = str(tip_key or "").strip()
        if not key:
            return
        state = self._onboarding_state()
        shown = {str(x) for x in state.get("shown_tips", [])}
        if key in shown:
            return
        shown.add(key)
        state["shown_tips"] = sorted(shown)
        self.save_settings_to_disk()

    def _maybe_show_contextual_tip(self, reason: str = "general") -> None:
        if not bool(self.settings.get("onboarding_enabled", True)):
            return
        if not bool(self.settings.get("onboarding_contextual_tips_enabled", True)):
            return
        state = self._onboarding_state()
        shown = {str(x) for x in state.get("shown_tips", [])}
        tips: list[tuple[str, str]] = []
        if not self._onboarding_has_step("used_command_palette"):
            tips.append(("tip_command_palette", "Tip: press Ctrl+Shift+P to open Command Palette."))
        if not self._onboarding_has_step("used_quick_open"):
            tips.append(("tip_quick_open", "Tip: press Ctrl+Alt+P for Quick Open and jump to files/symbols."))
        if not self._onboarding_has_step("opened_gamification_dashboard"):
            tips.append(("tip_gamification_dashboard", "Tip: open Play > Gamification Dashboard to track quests and unlocks."))
        if not self._onboarding_has_step("opened_daily_briefing"):
            tips.append(("tip_daily_briefing", "Tip: open Play > Daily Briefing for today's quest and companion guidance."))
        if not self._onboarding_has_step("opened_seasonal_event_briefing"):
            tips.append(("tip_seasonal_event", "Tip: open Play > Seasonal Event Briefing to track live event rewards."))
        if not self._onboarding_has_step("opened_session_review"):
            tips.append(("tip_session_review", "Tip: open Play > Session Review for a productivity recap and next unlock."))
        if not self._onboarding_has_step("used_coach_recommendation"):
            tips.append(("tip_coach_recommendation", "Tip: use the Productivity Hub recommendation button for the fastest next step."))
        if reason == "after_tutorial":
            tips.insert(0, ("tip_after_tutorial_demo", "Welcome tour done. Next: File > Templates > Demo Pack."))
            tips.insert(1, ("tip_after_tutorial", "Then try Command Palette (Ctrl+Shift+P)."))
        for tip_key, text in tips:
            if tip_key in shown:
                continue
            self._onboarding_mark_tip(tip_key)
            self.show_status_message(text, 5000)
            return

    def _maybe_show_next_unlock_prompt(self) -> None:
        if not bool(self.settings.get("onboarding_enabled", True)):
            return
        if not bool(self.settings.get("onboarding_next_unlock_prompts_enabled", True)):
            return
        if not self._gamification_enabled() or not hasattr(self, "gamification"):
            return
        state = self._onboarding_state()
        prompted_levels = {int(x) for x in state.get("unlock_prompt_levels", []) if str(x).isdigit()}
        gstate = self.gamification.state()
        level = int(gstate.get("level", 1) or 1)
        if level in prompted_levels:
            return
        next_unlock: tuple[int, str] | None = None
        for unlock_level, label in (
            (2, "Theme pack: Sunrise Sprint"),
            (4, "Tab badge: Neon Bracket"),
            (6, "Sound pack: LoFi Keys"),
        ):
            if level < unlock_level:
                next_unlock = (unlock_level, label)
                break
        if next_unlock is None:
            return
        target_level, reward_label = next_unlock
        xp = int(gstate.get("xp", 0) or 0)
        xp_to_target = max(0, (target_level - 1) * 120 - xp)
        self.show_status_message(
            f"Next unlock at LVL {target_level}: {reward_label} (about {xp_to_target} XP to go).",
            5500,
        )
        prompted_levels.add(level)
        state["unlock_prompt_levels"] = sorted(prompted_levels)
        self.save_settings_to_disk()

    def _maybe_show_daily_briefing_prompt(self) -> None:
        if not bool(self.settings.get("onboarding_enabled", True)):
            return
        if not bool(self.settings.get("onboarding_next_unlock_prompts_enabled", True)):
            return
        if not self._gamification_enabled() or not hasattr(self, "gamification"):
            return
        state = self._onboarding_state()
        today_key = datetime.now().date().isoformat()
        if str(state.get("daily_briefing_prompt_date", "") or "") == today_key:
            return
        state["daily_briefing_prompt_date"] = today_key
        self.save_settings_to_disk()

    def _maybe_show_seasonal_event_prompt(self) -> None:
        if not bool(self.settings.get("onboarding_enabled", True)):
            return
        if not self._gamification_enabled() or not hasattr(self, "gamification"):
            return
        if not self.gamification.active_events():
            return
        state = self._onboarding_state()
        today_key = datetime.now().date().isoformat()
        if str(state.get("seasonal_event_prompt_date", "") or "") == today_key:
            return
        state["seasonal_event_prompt_date"] = today_key
        self.save_settings_to_disk()

    def show_first_time_tutorial(self) -> None:
        tutorial = InteractiveTutorialDialog(self)
        accepted = tutorial.exec() == QDialog.Accepted
        if not accepted:
            self.show_status_message("Tutorial skipped. Reopen via Help > First Time Tutorial.", 3500)
            return
        self.settings["welcome_tutorial_seen"] = True
        self._onboarding_mark_step("completed_tutorial")
        self.save_settings_to_disk()
        self.show_status_message("First time tutorial completed. Try File > Templates > Demo Pack.", 3200)
        QTimer.singleShot(700, lambda: self._maybe_show_contextual_tip("after_tutorial"))
        QTimer.singleShot(1400, self._maybe_show_next_unlock_prompt)
        QTimer.singleShot(2100, self._maybe_show_daily_briefing_prompt)
        QTimer.singleShot(2800, self._maybe_show_seasonal_event_prompt)

    def open_demo_pack_first_template(self) -> None:
        root_fn = getattr(self, "_demo_templates_root", None)
        if not callable(root_fn):
            QMessageBox.information(self, "Open Demo Pack", "Demo pack path resolver is unavailable.")
            return
        root = root_fn()
        candidate = root / "01_welcome_quick_tour.md"
        if not candidate.exists():
            options = sorted(root.glob("*.md")) if root.exists() else []
            if not options:
                QMessageBox.information(self, "Open Demo Pack", "No demo templates were found.")
                return
            candidate = options[0]
        try:
            text = candidate.read_text(encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Open Demo Pack", f"Could not open demo template:\n{exc}")
            return
        tab = self.add_new_tab(text=text, file_path=None, make_current=True)
        tab.markdown_mode_enabled = True
        self.show_status_message(f"Opened demo template: {candidate.name}", 3000)

    def show_user_guide(self) -> None:
        guide_text = """
Pypad User Guide

1. Core Editing
- New/Open/Save/Save As are in File menu.
- Drag a text file into the app to open it.
- Use Ctrl+F for search panel, F3/Shift+F3 for next/previous.
- Ctrl+Shift+P opens the Command Palette.

2. Tabs and Navigation
- Middle-click any tab to close it.
- Pin Tab keeps important tabs grouped at the top.
- Favorite Tab marks important files and lists them under File > Favorite Files.
- Ctrl+Alt+P opens Quick Open / Go to Anything.
- Quick Open supports file/path search, :line[:col], @symbol, @@workspace-symbol, and >command.

3. Markdown and Code
- Use Format > Markdown for headings, lists, links, tables.
- Live Markdown Preview toggles side-by-side preview.
- Syntax language picker is in the status bar.

4. Versioning and Recovery
- Version History restores earlier snapshots and shows diffs.
- Autosave periodically captures unsaved changes.
- On startup, crash recovery offers unsaved autosave drafts.

5. Reminders and Tasks
- Reminders & Alarms let you schedule alerts, recurrence, and snooze.
- Checklist shortcuts can toggle - [ ] and - [x] tasks.

6. Templates and Export
- File > Templates inserts meeting, daily log, and checklist templates.
- File > Templates > Demo Pack includes full walkthrough templates covering major features.
- File > Export supports PDF, Markdown, HTML, DOCX, and ODT.

7. Workspace
- File > Workspace > Open Workspace Folder sets the active project folder.
- Browse files via Workspace Files.
- Search across the workspace with Search Workspace.

8. Security
- File > Security enables per-note encryption.
- Use .encnote extension for encrypted note files.
- Open encrypted notes by entering the note password.

9. AI Features
- File > AI > Ask AI for general prompts.
- Explain Selection with AI explains selected text.
- AI Inline Edit (Preview) supports hunk-level accept/reject.
- Ask Workspace (Citations) answers from workspace excerpts with file/line citations.
- AI Chat Panel supports prompt/response bubbles with live generation.
- Assistant responses can offer Insert / Replace / Append / New Tab / Replace File / Diff actions.
- Configure API key and model in Settings > AI & Updates.
- Tools > Collaboration Presence and conflict-resolution tools support shared editing workflows.

10. Updates
- Help > Check for Updates reads the update feed and shows changelog notes.
- Downloaded updates can be opened directly from the app.

11. UI and Productivity
- The app supports light/dark themes, accent color, custom chrome colors, and density modes.
- Most dialogs and panels now share a rounded token-based UI style for a consistent experience.
"""
        dlg = QDialog(self)
        dlg.setWindowTitle("User Guide")
        dlg.resize(760, 560)
        apply_dialog_theme_from_window(self, dlg)
        layout = QVBoxLayout(dlg)
        viewer = QTextEdit(dlg)
        viewer.setReadOnly(True)
        viewer.setPlainText(guide_text.strip())
        layout.addWidget(viewer)
        buttons = QDialogButtonBox(QDialogButtonBox.Close, Qt.Horizontal, dlg)
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)
        buttons.button(QDialogButtonBox.Close).clicked.connect(dlg.accept)
        layout.addWidget(buttons)
        dlg.exec()

    @staticmethod
    def _fmt_timestamp(ts: float | None) -> str:
        if ts is None:
            return "N/A"
        try:
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "N/A"

    @staticmethod
    def _text_stats(text: str) -> dict[str, int]:
        probe = str(text or "")
        return {
            "words": len(re.findall(r"\S+", probe)),
            "chars": len(probe),
            "chars_no_eol": len(probe.replace("\r", "").replace("\n", "")),
            "lines": probe.count("\n") + (1 if probe else 0),
        }

    def _selection_stats_text(self, tab: EditorTab | None) -> str:
        if tab is None:
            return "Words 0 | Chars 0"
        selected = ""
        try:
            selected = str(tab.text_edit.selected_text() or "")
        except Exception:
            selected = ""
        stats = self._text_stats(selected if selected else tab.text_edit.get_text())
        prefix = "Sel" if selected else "Doc"
        return f"{prefix} W {stats['words']} | C {stats['chars_no_eol']} | L {stats['lines']}"

    def show_document_summary(self) -> None:
        tab = self.active_tab()
        if tab is None:
            QMessageBox.information(self, "Document Summary", "No active document.")
            return

        text = tab.text_edit.get_text()
        file_path = tab.current_file or "(unsaved)"
        created = None
        modified = None
        if tab.current_file:
            try:
                st = Path(tab.current_file).stat()
                created = st.st_ctime
                modified = st.st_mtime
            except Exception:
                created = None
                modified = None

        stats = self._text_stats(text)

        selection = tab.text_edit.selection_range()
        selected_chars = 0
        selected_bytes = 0
        selected_range = "None"
        if selection is not None:
            l1, c1, l2, c2 = selection
            selected_text = tab.text_edit.selected_text()
            selected_chars = len(selected_text)
            selected_bytes = len(selected_text.encode("utf-8"))
            start_index = tab.text_edit.index_from_line_col(l1, c1)
            end_index = tab.text_edit.index_from_line_col(l2, c2)
            selected_range = (
                f"L{l1 + 1}:C{c1 + 1} -> L{l2 + 1}:C{c2 + 1} "
                f"(index {start_index}..{end_index})"
            )

        summary = (
            f"Path: {file_path}\n"
            f"Created: {self._fmt_timestamp(created)}\n"
            f"Modified: {self._fmt_timestamp(modified)}\n\n"
            f"Characters (without line endings): {stats['chars_no_eol']}\n"
            f"Characters (with line endings): {stats['chars']}\n"
            f"Words: {stats['words']}\n"
            f"Lines: {stats['lines']}\n\n"
            f"Selected characters: {selected_chars}\n"
            f"Selected bytes (UTF-8): {selected_bytes}\n"
            f"Selection range: {selected_range}\n"
        )

        dlg = QDialog(self)
        dlg.setWindowTitle("Document Summary")
        dlg.resize(700, 460)
        apply_dialog_theme_from_window(self, dlg)
        layout = QVBoxLayout(dlg)
        viewer = QTextEdit(dlg)
        viewer.setReadOnly(True)
        viewer.setPlainText(summary)
        layout.addWidget(viewer)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, Qt.Orientation.Horizontal, dlg)
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(dlg.accept)
        layout.addWidget(buttons)
        dlg.exec()

    def _spellcheck_custom_words(self) -> list[str]:
        raw = self.settings.get("spellcheck_user_dictionary", [])
        if isinstance(raw, list):
            return [str(item).strip().lower() for item in raw if str(item).strip()]
        return []

    def open_spell_check_dialog(self) -> None:
        tab = self.active_tab()
        if tab is None:
            QMessageBox.information(self, "Spell Check", "No active document.")
            return
        if not spellcheck_available():
            QMessageBox.information(
                self,
                "Spell Check",
                "Local spellcheck dependency is not installed.\n\n"
                "Install it with:\n"
                "pip install pyspellchecker\n\n"
                "Or reinstall project requirements to enable Spell Check Document.",
            )
            return
        self.show_status_message("Scanning document for misspellings...", 2000)
        findings = unknown_words(
            tab.text_edit.get_text(),
            language=str(self.settings.get("spellcheck_language", "en") or "en"),
            custom_words=self._spellcheck_custom_words(),
        )
        if not findings:
            QMessageBox.information(self, "Spell Check", "No potential misspellings were found in the current document.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Spell Check")
        dlg.resize(760, 520)
        apply_dialog_theme_from_window(self, dlg)
        layout = QVBoxLayout(dlg)
        summary = QLabel(f"Potential misspellings found: {len(findings)}", dlg)
        layout.addWidget(summary)
        split = QSplitter(Qt.Horizontal, dlg)
        words_list = QListWidget(split)
        suggestion_list = QListWidget(split)
        split.addWidget(words_list)
        split.addWidget(suggestion_list)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        layout.addWidget(split, 1)
        for row in findings:
            words_list.addItem(str(row.get("word", "")))

        def _refresh_suggestions(row_index: int) -> None:
            suggestion_list.clear()
            if row_index < 0 or row_index >= len(findings):
                return
            for item in findings[row_index].get("suggestions", []):
                suggestion_list.addItem(str(item))

        def _replace_selected() -> None:
            row_index = words_list.currentRow()
            if row_index < 0 or row_index >= len(findings):
                return
            chosen = suggestion_list.currentItem()
            if chosen is None:
                return
            entry = findings[row_index]
            start = int(entry.get("start", 0))
            end = int(entry.get("end", start))
            tab.text_edit.set_selection_by_index(start, end)
            tab.text_edit.replace_selection(chosen.text())
            dlg.accept()
            self.show_status_message("Spelling correction applied.", 2500)

        words_list.currentRowChanged.connect(_refresh_suggestions)
        buttons = QDialogButtonBox(QDialogButtonBox.Close, Qt.Horizontal, dlg)
        replace_btn = buttons.addButton("Replace", QDialogButtonBox.AcceptRole)
        replace_btn.clicked.connect(_replace_selected)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        if findings:
            words_list.setCurrentRow(0)
        dlg.exec()

    def show_spellcheck_suggestions_for_current_word(self) -> None:
        tab = self.active_tab()
        if tab is None:
            return
        if not spellcheck_available():
            self.show_status_message("Spellcheck dependency is unavailable.", 2500)
            return
        span = word_span_at(tab.text_edit.get_text(), tab.text_edit.cursor_index())
        if span is None:
            self.show_status_message("Move the caret onto a word first.", 2500)
            return
        word, start, end = span
        suggestions = suggestions_for_word(
            word,
            language=str(self.settings.get("spellcheck_language", "en") or "en"),
            custom_words=self._spellcheck_custom_words(),
        )
        if not suggestions:
            self.show_status_message("No spelling suggestions for the current word.", 2500)
            return
        menu = QMenu(self)
        for suggestion in suggestions:
            action = menu.addAction(suggestion)
            action.triggered.connect(
                lambda _checked=False, replacement=suggestion, lo=start, hi=end: (
                    tab.text_edit.set_selection_by_index(lo, hi),
                    tab.text_edit.replace_selection(replacement),
                    self.show_status_message("Spelling correction applied.", 2500),
                )
            )
        menu.exec(self.mapToGlobal(self.rect().center()))

    def show_discoverability_guide(self) -> None:
        body = (
            "Core workflows\n"
            "- File > Open / Quick Open for jumping into files fast\n"
            "- File > More > Workspace for folders, search, and profiles\n"
            "- View > Advanced > Project Panels for explorer, minimap, and symbol outline\n"
            "- Tools > Spell Check Document for local spelling review\n"
            "- Settings > UI Presets for Writing, Coding, and Review layouts\n\n"
            "Useful shortcuts\n"
            "- Ctrl+Shift+P: Command Palette\n"
            "- Ctrl+Alt+P: Quick Open\n"
            "- Ctrl+Shift+T: Reopen Closed Tab\n"
            "- F12: Go To Definition\n"
            "- Ctrl+F2 / F2: Toggle and navigate bookmarks\n"
        )
        dlg = QDialog(self)
        dlg.setWindowTitle("What Can I Do Here?")
        dlg.resize(720, 480)
        apply_dialog_theme_from_window(self, dlg)
        layout = QVBoxLayout(dlg)
        viewer = QTextEdit(dlg)
        viewer.setReadOnly(True)
        viewer.setPlainText(body)
        layout.addWidget(viewer)
        buttons = QDialogButtonBox(QDialogButtonBox.Close, Qt.Horizontal, dlg)
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)
        buttons.button(QDialogButtonBox.Close).clicked.connect(dlg.accept)
        layout.addWidget(buttons)
        dlg.exec()

    def enforce_privacy_lock(self) -> None:
        """Show a simple lock screen if privacy_lock is enabled.

        The user can unlock with either the configured password or PIN.
        This is intentionally lightweight and not cryptographically secure.
        """
        if not self.settings.get("privacy_lock", False):
            return

        stored_password = (self.settings.get("lock_password") or "").strip()
        stored_pin = (self.settings.get("lock_pin") or "").strip()

        # If no credentials are configured, don't block the user.
        if not stored_password and not stored_pin:
            return

        class LockDialog(QDialog):
            def __init__(self, parent=None, want_password: bool = True, want_pin: bool = True) -> None:
                super().__init__(parent)
                self.setWindowTitle("Unlock Pypad")
                layout = QFormLayout(self)

                self.password_edit: QLineEdit | None = None
                self.pin_edit: QLineEdit | None = None

                if want_password:
                    self.password_edit = QLineEdit(self)
                    self.password_edit.setEchoMode(QLineEdit.Password)
                    layout.addRow("Password:", self.password_edit)

                if want_pin:
                    self.pin_edit = QLineEdit(self)
                    self.pin_edit.setMaxLength(10)
                    self.pin_edit.setPlaceholderText("Digits only")
                    layout.addRow("PIN:", self.pin_edit)

                buttons = QDialogButtonBox(
                    QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                    Qt.Horizontal,
                    self,
                )
                buttons.accepted.connect(self.accept)
                buttons.rejected.connect(self.reject)
                layout.addRow(buttons)

            def get_values(self) -> tuple[str, str]:
                pw = self.password_edit.text() if self.password_edit is not None else ""
                pin = self.pin_edit.text() if self.pin_edit is not None else ""
                return pw.strip(), pin.strip()

        dlg = LockDialog(
            self,
            want_password=bool(stored_password),
            want_pin=bool(stored_pin),
        )

        while True:
            result = dlg.exec()
            if result != QDialog.Accepted:
                # User cancelled: close the window.
                self._request_window_close("privacy_lock_cancelled")
                return

            entered_password, entered_pin = dlg.get_values()
            ok_password = bool(stored_password) and entered_password == stored_password
            ok_pin = bool(stored_pin) and entered_pin == stored_pin

            if ok_password or ok_pin:
                # Successfully unlocked.
                return

            QMessageBox.warning(
                self,
                "Unlock Failed",
                "Incorrect password or PIN. Please try again.",
            )

    def trigger_easter_egg(self) -> None:
        """Spawn a draggable bouncing ball inside the main window."""
        existing = getattr(self, "_easter_egg_ball", None)
        if existing is not None and isinstance(existing, QWidget) and not existing.isHidden():
            existing.raise_()
            existing.activateWindow()
            self.log_event("Debug", "Bouncing ball already active")
            return
        self._easter_egg_running = True
        ball = self._EasterEggBall(self)
        self._easter_egg_ball = ball
        x = max(0, min(self.width() // 3, self.width() - ball.width()))
        y = max(0, min(self.height() // 4, self.height() - ball.height()))
        ball.move(x, y)
        ball.show()
        ball.raise_()

        def _clear_ball() -> None:
            self._easter_egg_running = False
            if getattr(self, "_easter_egg_ball", None) is ball:
                self._easter_egg_ball = None
            self.log_event("Info", "Bouncing ball easter egg closed")

        ball.destroyed.connect(lambda _obj=None: _clear_ball())
        self.log_event("Info", "Bouncing ball easter egg spawned")



