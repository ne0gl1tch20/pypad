from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pypad.ui.theme.dialog_theme import apply_dialog_theme_from_window
from pypad.ui.theme.theme_tokens import UIThemeTokens, build_gamification_widget_qss


class CompactGamificationWidget(QFrame):
    open_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pypadGamificationWidget")
        self.setFrameShape(QFrame.Shape.NoFrame)
        root = QHBoxLayout(self)
        root.setContentsMargins(6, 2, 6, 2)
        root.setSpacing(6)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(0)

        self.summary_label = QLabel("LVL 1 | XP 0 | Byte:Seed", self)
        self.summary_label.setObjectName("pypadGamificationSummary")
        self.quest_label = QLabel("Today: Complete 1 quiz (0/1)", self)
        self.quest_label.setObjectName("pypadGamificationQuest")
        self.quest_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.quest_label.setWordWrap(False)

        text_col.addWidget(self.summary_label)
        text_col.addWidget(self.quest_label)
        root.addLayout(text_col, 1)

        self.open_button = QPushButton("Play", self)
        self.open_button.setObjectName("pypadGamificationOpenButton")
        self.open_button.clicked.connect(self.open_requested.emit)
        root.addWidget(self.open_button, 0, Qt.AlignmentFlag.AlignVCenter)

    def update_payload(self, payload: dict[str, str]) -> None:
        self.summary_label.setText(str(payload.get("summary", "") or "LVL 1 | XP 0 | Byte:Seed"))
        self.quest_label.setText(str(payload.get("quest", "") or "Today: No quest"))
        self.setToolTip(str(payload.get("tooltip", "") or self.quest_label.text()))

    def apply_theme(self, tokens: UIThemeTokens) -> None:
        self.setStyleSheet(build_gamification_widget_qss(tokens))


class GamificationToast(QFrame):
    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self._host = host
        self._tokens: UIThemeTokens | None = None
        self.setObjectName("pypadGamificationToast")
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.hide()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.content_box = QFrame(self)
        self.content_box.setObjectName("pypadGamificationToastBox")
        self.content_box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        outer.addWidget(self.content_box)

        layout = QVBoxLayout(self.content_box)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self.title_label = QLabel("Quest progress", self.content_box)
        self.title_label.setObjectName("pypadGamificationToastTitle")
        self.title_label.setWordWrap(True)
        self.detail_label = QLabel("", self.content_box)
        self.detail_label.setObjectName("pypadGamificationToastDetail")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.detail_label)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self._host.installEventFilter(self)

    def apply_theme(self, tokens: UIThemeTokens) -> None:
        self._tokens = tokens
        self.setStyleSheet(build_gamification_widget_qss(tokens))

    def show_reward(self, title: str, detail: str = "", timeout_ms: int = 2800) -> None:
        self.title_label.setText(str(title or "Quest progress"))
        self.detail_label.setText(str(detail or ""))
        self.setMinimumWidth(280)
        self.setMaximumWidth(360)
        self.adjustSize()
        self._reposition()
        self.raise_()
        self.show()
        self._timer.start(max(1200, int(timeout_ms or 0)))

    def _reposition(self) -> None:
        host_rect = self._host.rect()
        width = min(max(self.sizeHint().width(), 280), max(280, host_rect.width() // 3))
        self.resize(width, self.sizeHint().height())
        x = max(12, host_rect.width() - self.width() - 18)
        y = 18
        self.move(QPoint(x, y))

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self._host and event.type() in {QEvent.Type.Resize, QEvent.Type.Move, QEvent.Type.Show}:
            if self.isVisible():
                self._reposition()
        return super().eventFilter(watched, event)


class MomentumBannerWidget(QFrame):
    recommended_action_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pypadMomentumBanner")
        self.setFrameShape(QFrame.Shape.NoFrame)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)
        self.title_label = QLabel("Momentum", self)
        self.title_label.setObjectName("pypadMomentumBannerTitle")
        self.detail_label = QLabel("Review quests and keep the streak alive.", self)
        self.detail_label.setObjectName("pypadMomentumBannerDetail")
        self.detail_label.setWordWrap(False)
        self.detail_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.action_button = QPushButton("Next Move", self)
        self.action_button.setObjectName("pypadMomentumBannerButton")
        self.action_button.clicked.connect(self.recommended_action_requested.emit)
        layout.addWidget(self.title_label)
        layout.addWidget(self.detail_label, 1)
        layout.addWidget(self.action_button)

    def update_payload(self, payload: dict[str, Any]) -> None:
        detail = str(payload.get("recommended_action_detail", "") or "Review quests and keep the streak alive.")
        next_unlock = str(payload.get("next_unlock", "") or "")
        text = detail if not next_unlock else f"{detail} | {next_unlock}"
        self.detail_label.setText(text)
        self.action_button.setText(str(payload.get("recommended_action_label", "") or "Next Move"))
        self.setToolTip(text)

    def apply_theme(self, tokens: UIThemeTokens) -> None:
        self.setStyleSheet(build_gamification_widget_qss(tokens))


class ProductivityHubWidget(QFrame):
    open_dashboard_requested = Signal()
    focus_sprint_requested = Signal()
    bug_hunt_requested = Signal()
    craft_tool_requested = Signal()
    routine_requested = Signal()
    recommended_action_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pypadProductivityHub")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(760)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        left_col = QWidget(self)
        left_col.setObjectName("pypadProductivityHubSidebar")
        left_col.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        left_col.setMinimumWidth(300)
        left_col.setMaximumWidth(360)
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(12)

        hero = QFrame(left_col)
        hero.setObjectName("pypadProductivityHubHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(14, 14, 14, 14)
        hero_layout.setSpacing(8)

        self.title_label = QLabel("Productivity Hub", hero)
        self.title_label.setObjectName("pypadProductivityHubTitle")
        self.title_label.setWordWrap(True)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.subtitle_label = QLabel("Quests, streaks, unlocks, and next moves tied to real work.", hero)
        self.subtitle_label.setObjectName("pypadProductivityHubSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        hero_layout.addWidget(self.title_label)
        hero_layout.addWidget(self.subtitle_label)

        stats_grid = QGridLayout()
        stats_grid.setContentsMargins(0, 0, 0, 0)
        stats_grid.setHorizontalSpacing(8)
        stats_grid.setVerticalSpacing(6)
        self.summary_value = QLabel("LVL 1 | XP 0 | Byte:Seed", hero)
        self.summary_value.setObjectName("pypadProductivityHubSummary")
        self.streak_value = QLabel("Streaks: writing 0 | focus 0 | review 0", hero)
        self.streak_value.setObjectName("pypadProductivityHubMeta")
        self.next_unlock_value = QLabel("Next unlock: keep moving", hero)
        self.next_unlock_value.setObjectName("pypadProductivityHubMeta")
        self.next_milestone_value = QLabel("Next milestone: keep moving", hero)
        self.next_milestone_value.setObjectName("pypadProductivityHubMeta")
        self.next_secret_value = QLabel("Secret trail: keep exploring", hero)
        self.next_secret_value.setObjectName("pypadProductivityHubMeta")
        self.next_routine_value = QLabel("Routine ready: keep moving", hero)
        self.next_routine_value.setObjectName("pypadProductivityHubMeta")
        self.companion_value = QLabel("Byte says: keep your streak alive.", hero)
        self.companion_value.setObjectName("pypadProductivityHubCompanion")
        self.companion_value.setWordWrap(True)
        self.recommendation_value = QLabel("Recommended next move: open the daily briefing.", hero)
        self.recommendation_value.setObjectName("pypadProductivityHubCompanion")
        self.recommendation_value.setWordWrap(True)
        for label in (
            self.summary_value,
            self.streak_value,
            self.next_unlock_value,
            self.next_milestone_value,
            self.next_secret_value,
            self.next_routine_value,
            self.companion_value,
            self.recommendation_value,
        ):
            label.setWordWrap(True)
            label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        stats_grid.addWidget(self.summary_value, 0, 0, 1, 2)
        stats_grid.addWidget(self.streak_value, 1, 0, 1, 2)
        stats_grid.addWidget(self.next_unlock_value, 2, 0, 1, 2)
        stats_grid.addWidget(self.next_milestone_value, 3, 0, 1, 2)
        stats_grid.addWidget(self.next_secret_value, 4, 0, 1, 2)
        stats_grid.addWidget(self.next_routine_value, 5, 0, 1, 2)
        stats_grid.addWidget(self.companion_value, 6, 0, 1, 2)
        stats_grid.addWidget(self.recommendation_value, 7, 0, 1, 2)
        hero_layout.addLayout(stats_grid)
        left_layout.addWidget(hero)

        actions_card = QFrame(left_col)
        actions_card.setObjectName("pypadProductivityHubCard")
        actions_layout = QGridLayout(actions_card)
        actions_layout.setContentsMargins(12, 12, 12, 12)
        actions_layout.setHorizontalSpacing(8)
        actions_layout.setVerticalSpacing(8)
        self.focus_btn = QPushButton("Focus Sprint", actions_card)
        self.bug_hunt_btn = QPushButton("Bug Hunt", actions_card)
        self.craft_btn = QPushButton("Craft Tool", actions_card)
        self.routine_btn = QPushButton("Run Routine", actions_card)
        self.recommendation_btn = QPushButton("Open Daily Briefing", actions_card)
        self.dashboard_btn = QPushButton("Open Dashboard", actions_card)
        self.focus_btn.clicked.connect(self.focus_sprint_requested.emit)
        self.bug_hunt_btn.clicked.connect(self.bug_hunt_requested.emit)
        self.craft_btn.clicked.connect(self.craft_tool_requested.emit)
        self.routine_btn.clicked.connect(self.routine_requested.emit)
        self.recommendation_btn.clicked.connect(self.recommended_action_requested.emit)
        self.dashboard_btn.clicked.connect(self.open_dashboard_requested.emit)
        for index, button in enumerate((
            self.focus_btn,
            self.bug_hunt_btn,
            self.craft_btn,
            self.routine_btn,
            self.recommendation_btn,
            self.dashboard_btn,
        )):
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.setMinimumHeight(34)
            button.setObjectName("pypadProductivityHubAction")
            actions_layout.addWidget(button, index // 2, index % 2)
        left_layout.addWidget(actions_card)
        left_layout.addStretch(1)
        root.addWidget(left_col, 0)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root.addWidget(self.scroll, 1)

        content = QWidget(self.scroll)
        content.setObjectName("pypadProductivityHubContent")
        self.scroll.setWidget(content)
        content_layout = QGridLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setHorizontalSpacing(12)
        content_layout.setVerticalSpacing(12)

        self.quest_list = self._add_section(content_layout, 0, 0, "Active Quests")
        self.badge_list = self._add_section(content_layout, 0, 1, "Recent Unlocks")
        self.briefing_list = self._add_section(content_layout, 1, 0, "Daily Briefing")
        self.events_list = self._add_section(content_layout, 1, 1, "Seasonal Events")
        self.session_list = self._add_section(content_layout, 2, 0, "Session Review")
        self.milestone_list = self._add_section(content_layout, 2, 1, "Long-Term Milestones")
        self.secret_list = self._add_section(content_layout, 3, 0, "Secret Trails")
        self.routine_list = self._add_section(content_layout, 3, 1, "Productivity Routines")
        self.routine_history_list = self._add_section(content_layout, 4, 0, "Routine History")
        self.activity_list = self._add_section(content_layout, 4, 1, "Recent Activity")

    def _add_section(self, layout: QGridLayout, row: int, column: int, title: str) -> QListWidget:
        card = QFrame(self.scroll.widget())
        card.setObjectName("pypadProductivityHubCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)
        header = QLabel(title, card)
        header.setObjectName("pypadProductivityHubSection")
        card_layout.addWidget(header)
        items = QListWidget(card)
        items.setObjectName("pypadProductivityHubList")
        items.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        items.setMinimumHeight(130)
        items.setMaximumHeight(180)
        card_layout.addWidget(items, 1)
        layout.addWidget(card, row, column)
        return items

    def apply_icons(self, icon_fn) -> None:
        if not callable(icon_fn):
            return
        icon_map = {
            self.focus_btn: "ai-sparkles",
            self.bug_hunt_btn: "edit-find",
            self.craft_btn: "document-new",
            self.routine_btn: "sync-horizontal",
            self.recommendation_btn: "ai-sparkles",
            self.dashboard_btn: "document-list",
        }
        for button, icon_name in icon_map.items():
            try:
                icon = icon_fn(icon_name, size=14)
            except Exception:
                icon = QIcon()
            if not icon.isNull():
                button.setIcon(icon)

    def update_payload(self, payload: dict[str, Any]) -> None:
        self.summary_value.setText(str(payload.get("summary", "") or "LVL 1 | XP 0 | Byte:Seed"))
        self.streak_value.setText(str(payload.get("streaks", "") or "Streaks: writing 0 | focus 0 | review 0"))
        self.next_unlock_value.setText(str(payload.get("next_unlock", "") or "Next unlock: keep moving"))
        self.next_milestone_value.setText(str(payload.get("next_milestone", "") or "Next milestone: keep moving"))
        self.next_secret_value.setText(str(payload.get("next_secret", "") or "Secret trail: keep exploring"))
        self.next_routine_value.setText(str(payload.get("next_routine", "") or "Routine ready: keep moving"))
        self.companion_value.setText(str(payload.get("companion_hint", "") or "Byte says: keep your streak alive."))
        self.recommendation_value.setText(
            str(payload.get("recommended_action_detail", "") or "Recommended next move: open the daily briefing.")
        )
        self.routine_btn.setText(str(payload.get("primary_routine_label", "") or "Run Routine"))
        self.recommendation_btn.setText(
            str(payload.get("recommended_action_label", "") or "Open Daily Briefing")
        )
        quests = payload.get("quests", [])
        badges = payload.get("recent_unlocks", [])
        briefing = payload.get("briefing", [])
        events = payload.get("events", [])
        session_review = payload.get("session_review", [])
        milestones = payload.get("milestones", [])
        secret_trails = payload.get("secret_trails", [])
        routines = payload.get("routines", [])
        routine_history = payload.get("routine_history", [])
        activity_timeline = payload.get("activity_timeline", [])
        self.quest_list.clear()
        for item in quests if isinstance(quests, list) else []:
            self.quest_list.addItem(str(item))
        if self.quest_list.count() == 0:
            self.quest_list.addItem("No active quests.")
        self.badge_list.clear()
        for item in badges if isinstance(badges, list) else []:
            self.badge_list.addItem(str(item))
        if self.badge_list.count() == 0:
            self.badge_list.addItem("No unlocks yet.")
        self.briefing_list.clear()
        for item in briefing if isinstance(briefing, list) else []:
            self.briefing_list.addItem(str(item))
        if self.briefing_list.count() == 0:
            self.briefing_list.addItem("No briefing yet.")
        self.events_list.clear()
        for item in events if isinstance(events, list) else []:
            if isinstance(item, dict):
                self.events_list.addItem(
                    f"{item.get('name', '')}: {item.get('quest_label', '')} "
                    f"({item.get('progress', '0')}/{item.get('target', '1')})"
                )
            else:
                self.events_list.addItem(str(item))
        if self.events_list.count() == 0:
            self.events_list.addItem("No active seasonal events.")
        self.session_list.clear()
        for item in session_review if isinstance(session_review, list) else []:
            self.session_list.addItem(str(item))
        if self.session_list.count() == 0:
            self.session_list.addItem("No session review yet.")
        self.milestone_list.clear()
        for item in milestones if isinstance(milestones, list) else []:
            self.milestone_list.addItem(str(item))
        if self.milestone_list.count() == 0:
            self.milestone_list.addItem("No milestones tracked yet.")
        self.secret_list.clear()
        for item in secret_trails if isinstance(secret_trails, list) else []:
            self.secret_list.addItem(str(item))
        if self.secret_list.count() == 0:
            self.secret_list.addItem("No secret trails visible yet.")
        self.routine_list.clear()
        for item in routines if isinstance(routines, list) else []:
            self.routine_list.addItem(str(item))
        if self.routine_list.count() == 0:
            self.routine_list.addItem("No productivity routines suggested yet.")
        self.routine_history_list.clear()
        for item in routine_history if isinstance(routine_history, list) else []:
            self.routine_history_list.addItem(str(item))
        if self.routine_history_list.count() == 0:
            self.routine_history_list.addItem("No routines completed yet.")
        self.activity_list.clear()
        for item in activity_timeline if isinstance(activity_timeline, list) else []:
            self.activity_list.addItem(str(item))
        if self.activity_list.count() == 0:
            self.activity_list.addItem("No recent activity yet.")

    def apply_theme(self, tokens: UIThemeTokens) -> None:
        self.setStyleSheet(build_gamification_widget_qss(tokens))


class ProductivityHubDialog(QDialog):
    def __init__(
        self,
        window: QWidget,
        hub_widget: ProductivityHubWidget,
        *,
        restore_geometry: Callable[[QDialog], None] | None = None,
        save_geometry: Callable[[QDialog], None] | None = None,
    ) -> None:
        super().__init__(window)
        self._restore_geometry = restore_geometry
        self._save_geometry = save_geometry
        self._geometry_restored = False
        self._geometry_save_timer = QTimer(self)
        self._geometry_save_timer.setSingleShot(True)
        self._geometry_save_timer.timeout.connect(self._flush_geometry_save)
        self.setObjectName("pypadProductivityHubDialog")
        self.setWindowTitle("Productivity Hub")
        self.resize(1100, 760)
        self.setModal(False)
        apply_dialog_theme_from_window(window, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Productivity Hub", self)
        title.setObjectName("pypadProductivityHubDialogTitle")
        subtitle = QLabel("A focused command center for quests, streaks, and coaching.", self)
        subtitle.setObjectName("pypadProductivityHubDialogSubtitle")
        subtitle.setWordWrap(True)
        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(2)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col, 1)
        close_btn = QToolButton(self)
        close_btn.setObjectName("pypadProductivityHubDialogClose")
        close_btn.setText("Close")
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)
        layout.addWidget(hub_widget, 1)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if not self._geometry_restored and callable(self._restore_geometry):
            try:
                self._restore_geometry(self)
            except Exception:
                pass
            self._geometry_restored = True

    def moveEvent(self, event) -> None:  # type: ignore[override]
        super().moveEvent(event)
        self._schedule_geometry_save()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._schedule_geometry_save()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._flush_geometry_save()
        super().closeEvent(event)

    def _schedule_geometry_save(self) -> None:
        if not self.isVisible():
            return
        self._geometry_save_timer.start(350)

    def _flush_geometry_save(self) -> None:
        if callable(self._save_geometry):
            try:
                self._save_geometry(self)
            except Exception:
                pass
