"""Show a dialog that summarizes gamification progress, stats, and available rewards or goals.

This module belongs to the optional productivity and feature UI layer. It helps explain how `pypad.ui.features` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from pypad.ui.features.gamification_system import GamificationSystem
from pypad.ui.theme.dialog_theme import apply_dialog_theme_from_window


class GamificationDashboardDialog(QDialog):
    """gamification dashboard dialog."""
    def __init__(self, window, gamification: GamificationSystem) -> None:
        """Build the gamification dashboard dialog and initialize its widgets."""
        super().__init__(window)
        self.window = window
        self.gamification = gamification
        self.setWindowTitle("Gamification Dashboard")
        self.resize(920, 620)
        apply_dialog_theme_from_window(window, self)

        root = QVBoxLayout(self)
        self.header = QLabel("", self)
        root.addWidget(self.header)

        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs, 1)

        self.quests_table = QTableWidget(self)
        self.skill_table = QTableWidget(self)
        self.companion_text = QTextEdit(self)
        self.companion_text.setReadOnly(True)
        self.crafted_list = QListWidget(self)
        self.events_table = QTableWidget(self)
        self.secrets_table = QTableWidget(self)
        self.routines_table = QTableWidget(self)

        self._build_quests_tab()
        self._build_skill_tree_tab()
        self._build_companion_tab()
        self._build_crafted_tools_tab()
        self._build_events_tab()
        self._build_secrets_tab()
        self._build_routines_tab()

        buttons = QDialogButtonBox(QDialogButtonBox.Close, self)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self.refresh()

    def _build_quests_tab(self) -> None:
        """Build quests tab."""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        self.quests_table.setColumnCount(5)
        self.quests_table.setHorizontalHeaderLabels(["Scope", "Quest", "Progress", "Target", "Done"])
        self.quests_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.quests_table)
        self.tabs.addTab(container, "Quests")

    def _build_skill_tree_tab(self) -> None:
        """Build skill tree tab."""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        self.skill_table.setColumnCount(4)
        self.skill_table.setHorizontalHeaderLabels(["Branch", "Tier", "XP", "Unlocks"])
        self.skill_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.skill_table)
        self.tabs.addTab(container, "Skill Tree")

    def _build_companion_tab(self) -> None:
        """Build companion tab."""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.addWidget(self.companion_text)
        self.tabs.addTab(container, "Companion")

    def _build_crafted_tools_tab(self) -> None:
        """Build crafted tools tab."""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.addWidget(self.crafted_list, 1)
        row = QHBoxLayout()
        star_btn = QPushButton("Toggle Star", container)
        delete_btn = QPushButton("Delete Tool", container)
        export_btn = QPushButton("Export Pack", container)
        star_btn.clicked.connect(self._toggle_star)
        delete_btn.clicked.connect(self._delete_selected)
        export_btn.clicked.connect(self.window.export_crafted_tools_pack)
        row.addWidget(star_btn)
        row.addWidget(delete_btn)
        row.addStretch(1)
        row.addWidget(export_btn)
        layout.addLayout(row)
        self.tabs.addTab(container, "Crafted Tools")

    def _build_events_tab(self) -> None:
        """Build events tab."""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        help_text = QLabel(
            "Customizable events are read from settings key `gamification_custom_events` "
            "with fields: name, start (YYYY-MM-DD), end (YYYY-MM-DD), theme_pack, badge.",
            container,
        )
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        self.events_table.setColumnCount(6)
        self.events_table.setHorizontalHeaderLabels(["Event", "Quest", "Progress", "Target", "Done", "Badge"])
        self.events_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.events_table, 1)
        self.tabs.addTab(container, "Seasonal Events")

    def _build_secrets_tab(self) -> None:
        """Build secrets tab."""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        help_text = QLabel(
            "Secret trails hint at hidden unlocks without fully spoiling them. Progress is tracked from your real usage.",
            container,
        )
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        self.secrets_table.setColumnCount(5)
        self.secrets_table.setHorizontalHeaderLabels(["Secret", "Progress", "Target", "Status", "Hint"])
        self.secrets_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.secrets_table, 1)
        self.tabs.addTab(container, "Secret Trails")

    def _build_routines_tab(self) -> None:
        """Build routines tab."""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        help_text = QLabel(
            "Productivity routines are reusable workflow starts. PyPad tracks which ones you actually use.",
            container,
        )
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        self.routines_table.setColumnCount(4)
        self.routines_table.setHorizontalHeaderLabels(["Routine", "Suggested Action", "Runs", "Last Run"])
        self.routines_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.routines_table, 1)
        self.tabs.addTab(container, "Routines")

    def refresh(self) -> None:
        """Refresh the value."""
        state = self.gamification.state()
        quests = self.gamification.quests_snapshot()
        self.header.setText(
            f"Level {state.get('level', 1)} | XP {state.get('xp', 0)} | "
            f"Companion: {state.get('companion', {}).get('name', 'Byte')} "
            f"({state.get('companion', {}).get('stage', 'Seed')})"
        )

        rows: list[tuple[str, dict[str, Any]]] = []
        for scope in ("daily", "weekly"):
            bucket = quests.get(scope, {})
            if isinstance(bucket, dict):
                for item in bucket.values():
                    if isinstance(item, dict):
                        rows.append((scope.title(), item))
        self.quests_table.setRowCount(len(rows))
        for idx, (scope, row) in enumerate(rows):
            self.quests_table.setItem(idx, 0, QTableWidgetItem(scope))
            self.quests_table.setItem(idx, 1, QTableWidgetItem(str(row.get("label", ""))))
            self.quests_table.setItem(idx, 2, QTableWidgetItem(str(row.get("progress", 0))))
            self.quests_table.setItem(idx, 3, QTableWidgetItem(str(row.get("target", 1))))
            self.quests_table.setItem(idx, 4, QTableWidgetItem("Yes" if bool(row.get("done", False)) else "No"))

        skills = state.get("skill_tree", {})
        branches = ["writing", "coding", "research", "ai_workflow"]
        self.skill_table.setRowCount(len(branches))
        for idx, branch in enumerate(branches):
            node = skills.get(branch, {}) if isinstance(skills, dict) else {}
            unlocks = ", ".join(node.get("unlocks", [])) if isinstance(node, dict) else ""
            self.skill_table.setItem(idx, 0, QTableWidgetItem(branch))
            self.skill_table.setItem(idx, 1, QTableWidgetItem(str(node.get("tier", 1))))
            self.skill_table.setItem(idx, 2, QTableWidgetItem(str(node.get("xp", 0))))
            self.skill_table.setItem(idx, 3, QTableWidgetItem(unlocks or "-"))

        companion = state.get("companion", {})
        achievements = state.get("achievements", [])
        badges = state.get("event_badges", [])
        companion_lines = [
            f"Name: {companion.get('name', 'Byte')}",
            f"Persona: {companion.get('persona', 'Guide')}",
            f"Evolution Stage: {companion.get('stage', 'Seed')}",
            "",
            "Achievements:",
        ]
        if achievements:
            companion_lines.extend(f"- {a}" for a in achievements)
        else:
            companion_lines.append("- None yet")
        companion_lines.append("")
        companion_lines.append("Event Badges:")
        if badges:
            companion_lines.extend(f"- {b}" for b in badges)
        else:
            companion_lines.append("- None yet")
        self.companion_text.setPlainText("\n".join(companion_lines))

        self.crafted_list.clear()
        crafted = state.get("crafted_tools", [])
        if isinstance(crafted, list):
            for row in crafted:
                if not isinstance(row, dict):
                    continue
                name = str(row.get("name", "")).strip() or "Untitled Tool"
                star = " *" if bool(row.get("starred", False)) else ""
                components = row.get("components", [])
                count = len(components) if isinstance(components, list) else 0
                item = QListWidgetItem(f"{name}{star} ({count} parts)")
                item.setData(256, name)
                self.crafted_list.addItem(item)

        events = self.gamification.active_event_snapshot()
        self.events_table.setRowCount(len(events))
        for idx, row in enumerate(events):
            self.events_table.setItem(idx, 0, QTableWidgetItem(str(row.get("name", ""))))
            self.events_table.setItem(idx, 1, QTableWidgetItem(str(row.get("quest_label", ""))))
            self.events_table.setItem(idx, 2, QTableWidgetItem(str(row.get("progress", "0"))))
            self.events_table.setItem(idx, 3, QTableWidgetItem(str(row.get("target", "1"))))
            self.events_table.setItem(idx, 4, QTableWidgetItem(str(row.get("done", "No"))))
            self.events_table.setItem(idx, 5, QTableWidgetItem(str(row.get("badge", ""))))
        if not events:
            self.events_table.setRowCount(1)
            self.events_table.setItem(0, 0, QTableWidgetItem("No active events."))

        secrets = self.gamification.easter_egg_snapshot()
        self.secrets_table.setRowCount(len(secrets))
        for idx, row in enumerate(secrets):
            self.secrets_table.setItem(idx, 0, QTableWidgetItem(str(row.get("title", ""))))
            self.secrets_table.setItem(idx, 1, QTableWidgetItem(str(row.get("progress", "0"))))
            self.secrets_table.setItem(idx, 2, QTableWidgetItem(str(row.get("target", "1"))))
            self.secrets_table.setItem(idx, 3, QTableWidgetItem(str(row.get("status", "Hidden"))))
            self.secrets_table.setItem(idx, 4, QTableWidgetItem(str(row.get("hint", ""))))

        routines = self.gamification.productivity_routines()
        routine_stats = state.get("routine_stats", {})
        self.routines_table.setRowCount(len(routines))
        for idx, row in enumerate(routines):
            routine_id = str(row.get("routine_id", "") or "")
            stats_row = routine_stats.get(routine_id, {}) if isinstance(routine_stats, dict) else {}
            runs = int(stats_row.get("runs", 0) or 0) if isinstance(stats_row, dict) else 0
            last_run = str(stats_row.get("last_run", "") or "") if isinstance(stats_row, dict) else ""
            self.routines_table.setItem(idx, 0, QTableWidgetItem(routine_id or "-"))
            self.routines_table.setItem(idx, 1, QTableWidgetItem(str(row.get("label", ""))))
            self.routines_table.setItem(idx, 2, QTableWidgetItem(str(runs)))
            self.routines_table.setItem(idx, 3, QTableWidgetItem(last_run or "-"))

    def _selected_tool_name(self) -> str:
        """Handle selected tool name."""
        item = self.crafted_list.currentItem()
        if item is None:
            return ""
        return str(item.data(256) or "").strip()

    def _toggle_star(self) -> None:
        """Handle toggle star."""
        name = self._selected_tool_name()
        if not name:
            return
        state = self.gamification.state()
        rows = state.get("crafted_tools", [])
        if not isinstance(rows, list):
            return
        for row in rows:
            if isinstance(row, dict) and str(row.get("name", "")).strip() == name:
                row["starred"] = not bool(row.get("starred", False))
                break
        self.refresh()

    def _delete_selected(self) -> None:
        """Handle delete selected."""
        name = self._selected_tool_name()
        if not name:
            return
        state = self.gamification.state()
        rows = state.get("crafted_tools", [])
        if not isinstance(rows, list):
            return
        state["crafted_tools"] = [
            row for row in rows if not (isinstance(row, dict) and str(row.get("name", "")).strip() == name)
        ]
        self.refresh()
