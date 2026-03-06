from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

XP_PER_LEVEL = 120


@dataclass(frozen=True)
class XPResult:
    xp_added: int
    level_before: int
    level_after: int

    @property
    def leveled_up(self) -> bool:
        return self.level_after > self.level_before


class GamificationSystem:
    def __init__(self, settings: dict[str, Any]) -> None:
        self.settings = settings

    def state(self) -> dict[str, Any]:
        state = self.settings.get("gamification_state")
        if not isinstance(state, dict):
            state = {}
            self.settings["gamification_state"] = state
        self._coerce_state(state)
        return state

    def _coerce_state(self, state: dict[str, Any]) -> None:
        state["xp"] = max(0, int(state.get("xp", 0) or 0))
        state["level"] = max(1, int(state.get("level", 1) or 1))
        state["achievements"] = sorted({str(x) for x in state.get("achievements", []) if str(x).strip()})
        state["cosmetics"] = state.get("cosmetics", {}) if isinstance(state.get("cosmetics"), dict) else {}
        state["skill_tree"] = state.get("skill_tree", {}) if isinstance(state.get("skill_tree"), dict) else {}
        state["quests"] = state.get("quests", {}) if isinstance(state.get("quests"), dict) else {}
        state["challenge_modes"] = state.get("challenge_modes", {}) if isinstance(state.get("challenge_modes"), dict) else {}
        state["companion"] = state.get("companion", {}) if isinstance(state.get("companion"), dict) else {}
        state["crafted_tools"] = state.get("crafted_tools", []) if isinstance(state.get("crafted_tools"), list) else []
        state["event_badges"] = sorted({str(x) for x in state.get("event_badges", []) if str(x).strip()})
        state["stats"] = state.get("stats", {}) if isinstance(state.get("stats"), dict) else {}

        for key, value in {
            "quizzes_finished": 0,
            "workspace_reviews": 0,
            "focus_sprints_completed": 0,
            "words_written": 0,
            "todo_fixed": 0,
            "plugin_uses": 0,
        }.items():
            state["stats"][key] = max(0, int(state["stats"].get(key, value) or value))

        state["companion"].setdefault("name", "Byte")
        state["companion"].setdefault("persona", "Guide")
        state["companion"].setdefault("stage", "Seed")

        cosmetics = state["cosmetics"]
        cosmetics["themes_unlocked"] = sorted({str(x) for x in cosmetics.get("themes_unlocked", []) if str(x).strip()})
        cosmetics["tab_badges_unlocked"] = sorted({str(x) for x in cosmetics.get("tab_badges_unlocked", []) if str(x).strip()})
        cosmetics["sound_packs_unlocked"] = sorted({str(x) for x in cosmetics.get("sound_packs_unlocked", []) if str(x).strip()})

        for branch in ("writing", "coding", "research", "ai_workflow"):
            raw = state["skill_tree"].get(branch, {})
            if not isinstance(raw, dict):
                raw = {}
            state["skill_tree"][branch] = {
                "xp": max(0, int(raw.get("xp", 0) or 0)),
                "tier": max(1, int(raw.get("tier", 1) or 1)),
                "unlocks": sorted({str(x) for x in raw.get("unlocks", []) if str(x).strip()}),
            }

    def _level_from_xp(self, xp: int) -> int:
        return max(1, 1 + (max(0, xp) // XP_PER_LEVEL))

    def award_xp(self, amount: int, reason: str, *, skill_branch: str | None = None) -> XPResult:
        state = self.state()
        xp_added = max(0, int(amount or 0))
        before = int(state["level"])
        state["xp"] = int(state["xp"]) + xp_added
        state["level"] = self._level_from_xp(int(state["xp"]))
        if reason:
            state["last_xp_reason"] = str(reason)
        if skill_branch and skill_branch in state["skill_tree"]:
            tree = state["skill_tree"][skill_branch]
            tree["xp"] = int(tree.get("xp", 0)) + xp_added
            tree["tier"] = max(1, 1 + (int(tree["xp"]) // 300))
            self._sync_branch_unlocks(skill_branch)
        self._sync_level_unlocks()
        self._sync_companion()
        return XPResult(xp_added=xp_added, level_before=before, level_after=int(state["level"]))

    def _sync_level_unlocks(self) -> None:
        state = self.state()
        lvl = int(state["level"])
        cosmetics = state["cosmetics"]
        if lvl >= 2:
            cosmetics["themes_unlocked"] = sorted(set(cosmetics["themes_unlocked"]) | {"Sunrise Sprint"})
        if lvl >= 4:
            cosmetics["tab_badges_unlocked"] = sorted(set(cosmetics["tab_badges_unlocked"]) | {"Neon Bracket"})
        if lvl >= 6:
            cosmetics["sound_packs_unlocked"] = sorted(set(cosmetics["sound_packs_unlocked"]) | {"LoFi Keys"})

    def _sync_branch_unlocks(self, branch: str) -> None:
        state = self.state()
        node = state["skill_tree"][branch]
        tier = int(node.get("tier", 1))
        unlocks = set(node.get("unlocks", []))
        if branch == "writing" and tier >= 2:
            unlocks.add("No-backspace challenge hints")
        if branch == "coding" and tier >= 2:
            unlocks.add("Advanced quick-open tricks")
        if branch == "research" and tier >= 2:
            unlocks.add("Smarter workspace scan preset")
        if branch == "ai_workflow" and tier >= 2:
            unlocks.add("Auto-template synthesis")
        node["unlocks"] = sorted(unlocks)

    def _sync_companion(self) -> None:
        state = self.state()
        lvl = int(state["level"])
        if lvl >= 8:
            stage = "Sage"
        elif lvl >= 5:
            stage = "Pilot"
        elif lvl >= 3:
            stage = "Scout"
        else:
            stage = "Seed"
        state["companion"]["stage"] = stage

    def add_achievement(self, title: str) -> bool:
        state = self.state()
        key = str(title or "").strip()
        if not key:
            return False
        existing = set(state["achievements"])
        if key in existing:
            return False
        existing.add(key)
        state["achievements"] = sorted(existing)
        return True

    def apply_stat_delta(self, key: str, delta: int = 1) -> int:
        state = self.state()
        current = int(state["stats"].get(key, 0) or 0)
        state["stats"][key] = max(0, current + int(delta or 0))
        return int(state["stats"][key])

    def quests_snapshot(self, now: datetime | None = None) -> dict[str, Any]:
        stamp = now or datetime.now()
        day_key = stamp.date().isoformat()
        iso = stamp.isocalendar()
        week_key = f"{iso.year}-W{iso.week:02d}"
        state = self.state()
        quests = state["quests"]
        if quests.get("daily_key") != day_key:
            quests["daily_key"] = day_key
            quests["daily"] = {
                "complete_quiz": {"label": "Complete 1 quiz", "target": 1, "progress": 0, "done": False},
                "write_words": {"label": "Write 300 words", "target": 300, "progress": 0, "done": False},
                "todo_fix": {"label": "Fix 3 TODOs", "target": 3, "progress": 0, "done": False},
            }
        if quests.get("weekly_key") != week_key:
            quests["weekly_key"] = week_key
            quests["weekly"] = {
                "workspace_review": {"label": "Run workspace review", "target": 1, "progress": 0, "done": False},
                "focus_sprint": {"label": "Finish 3 focus sprints", "target": 3, "progress": 0, "done": False},
                "plugin_use": {"label": "Use plugin features 2 times", "target": 2, "progress": 0, "done": False},
            }
        return quests

    def _bump_quest(self, bucket: str, quest_id: str, amount: int = 1) -> bool:
        quests = self.quests_snapshot()
        row = quests.get(bucket, {}).get(quest_id)
        if not isinstance(row, dict):
            return False
        row["progress"] = min(int(row.get("target", 1)), int(row.get("progress", 0)) + max(1, int(amount or 1)))
        row["done"] = bool(row["progress"] >= int(row.get("target", 1)))
        return bool(row["done"])

    def mark_quiz_finished(self) -> tuple[XPResult, list[str]]:
        done: list[str] = []
        self.apply_stat_delta("quizzes_finished", 1)
        if self._bump_quest("daily", "complete_quiz", 1):
            done.append("Daily quest complete: Complete 1 quiz")
        res = self.award_xp(40, "Quiz finished", skill_branch="research")
        if self.apply_stat_delta("quizzes_finished", 0) >= 10 and self.add_achievement("Quiz Apprentice"):
            done.append("Achievement unlocked: Quiz Apprentice")
        return res, done

    def mark_workspace_review(self) -> tuple[XPResult, list[str]]:
        done: list[str] = []
        self.apply_stat_delta("workspace_reviews", 1)
        if self._bump_quest("weekly", "workspace_review", 1):
            done.append("Weekly quest complete: Run workspace review")
        res = self.award_xp(25, "Workspace review", skill_branch="coding")
        return res, done

    def mark_focus_sprint_completed(self) -> tuple[XPResult, list[str]]:
        done: list[str] = []
        self.apply_stat_delta("focus_sprints_completed", 1)
        if self._bump_quest("weekly", "focus_sprint", 1):
            done.append("Weekly quest complete: Finish 3 focus sprints")
        res = self.award_xp(30, "Focus sprint completed", skill_branch="writing")
        return res, done

    def mark_plugin_used(self) -> tuple[XPResult, list[str]]:
        done: list[str] = []
        self.apply_stat_delta("plugin_uses", 1)
        if self._bump_quest("weekly", "plugin_use", 1):
            done.append("Weekly quest complete: Use plugin features 2 times")
        res = self.award_xp(15, "Plugin feature used", skill_branch="ai_workflow")
        return res, done

    def add_written_words(self, words: int) -> tuple[XPResult | None, list[str]]:
        if words <= 0:
            return None, []
        done: list[str] = []
        self.apply_stat_delta("words_written", words)
        if self._bump_quest("daily", "write_words", words):
            done.append("Daily quest complete: Write 300 words")
        res = self.award_xp(max(1, words // 25), "Writing streak", skill_branch="writing")
        return res, done

    def add_todo_fixed(self, count: int = 1) -> tuple[XPResult | None, list[str]]:
        if count <= 0:
            return None, []
        done: list[str] = []
        self.apply_stat_delta("todo_fixed", count)
        if self._bump_quest("daily", "todo_fix", count):
            done.append("Daily quest complete: Fix 3 TODOs")
        res = self.award_xp(count * 8, "TODO fixes", skill_branch="coding")
        return res, done

    def set_challenge_state(self, challenge_id: str, active: bool, payload: dict[str, Any] | None = None) -> None:
        state = self.state()["challenge_modes"]
        row = state.get(challenge_id)
        if not isinstance(row, dict):
            row = {}
            state[challenge_id] = row
        row["active"] = bool(active)
        row["updated_at"] = datetime.now().isoformat(timespec="seconds")
        if payload:
            row.update(payload)

    def active_events(self, now: date | None = None) -> list[dict[str, str]]:
        today = now or date.today()
        custom = self.settings.get("gamification_custom_events", [])
        rows: list[dict[str, str]] = []
        if isinstance(custom, list):
            for row in custom:
                if not isinstance(row, dict):
                    continue
                name = str(row.get("name", "")).strip()
                start = str(row.get("start", "")).strip()
                end = str(row.get("end", "")).strip()
                if not name or not start or not end:
                    continue
                try:
                    d1 = date.fromisoformat(start)
                    d2 = date.fromisoformat(end)
                except Exception:
                    continue
                if d1 <= today <= d2:
                    rows.append({"name": name, "theme_pack": str(row.get("theme_pack", "")), "badge": str(row.get("badge", ""))})

        year = today.year
        defaults = [
            {"name": "Markdown Week", "start": date(year, 3, 1), "end": date(year, 3, 7), "theme_pack": "Paper Sprint", "badge": "Markdown Maven"},
            {"name": "Refactor Month", "start": date(year, 10, 1), "end": date(year, 10, 31), "theme_pack": "Clean Code", "badge": "Refactor Ranger"},
        ]
        for row in defaults:
            if row["start"] <= today <= row["end"]:
                rows.append({"name": row["name"], "theme_pack": row["theme_pack"], "badge": row["badge"]})
        return rows
