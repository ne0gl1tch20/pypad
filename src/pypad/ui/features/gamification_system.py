"""Track gamification rules, progress, and reward calculations used by the application.

This module belongs to the optional productivity and feature UI layer. It helps explain how `pypad.ui.features` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

XP_PER_LEVEL = 120


@dataclass(frozen=True)
class XPResult:
    """x p result."""
    xp_added: int
    level_before: int
    level_after: int

    @property
    def leveled_up(self) -> bool:
        """Handle leveled up."""
        return self.level_after > self.level_before


class GamificationSystem:
    """gamification system."""
    def __init__(self, settings: dict[str, Any]) -> None:
        """Set up gamification progress tracking, storage, and unlock state."""
        self.settings = settings

    @staticmethod
    def _safe_int(value: Any, default: int = 0, *, minimum: int | None = None) -> int:
        """Handle safe int."""
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = default
        if minimum is not None:
            number = max(minimum, number)
        return number

    def state(self) -> dict[str, Any]:
        """Handle state."""
        state = self.settings.get("gamification_state")
        if not isinstance(state, dict):
            state = {}
            self.settings["gamification_state"] = state
        self._coerce_state(state)
        return state

    def _coerce_state(self, state: dict[str, Any]) -> None:
        """Handle coerce state."""
        state["xp"] = self._safe_int(state.get("xp", 0), 0, minimum=0)
        state["level"] = self._safe_int(state.get("level", 1), 1, minimum=1)
        state["achievements"] = sorted({str(x) for x in state.get("achievements", []) if str(x).strip()})
        state["cosmetics"] = state.get("cosmetics", {}) if isinstance(state.get("cosmetics"), dict) else {}
        state["skill_tree"] = state.get("skill_tree", {}) if isinstance(state.get("skill_tree"), dict) else {}
        state["quests"] = state.get("quests", {}) if isinstance(state.get("quests"), dict) else {}
        state["challenge_modes"] = state.get("challenge_modes", {}) if isinstance(state.get("challenge_modes"), dict) else {}
        state["companion"] = state.get("companion", {}) if isinstance(state.get("companion"), dict) else {}
        state["crafted_tools"] = state.get("crafted_tools", []) if isinstance(state.get("crafted_tools"), list) else []
        state["event_badges"] = sorted({str(x) for x in state.get("event_badges", []) if str(x).strip()})
        state["stats"] = state.get("stats", {}) if isinstance(state.get("stats"), dict) else {}
        state["streaks"] = state.get("streaks", {}) if isinstance(state.get("streaks"), dict) else {}
        state["activity_log"] = state.get("activity_log", {}) if isinstance(state.get("activity_log"), dict) else {}
        state["events_state"] = state.get("events_state", {}) if isinstance(state.get("events_state"), dict) else {}
        state["session_review"] = state.get("session_review", {}) if isinstance(state.get("session_review"), dict) else {}
        state["activity_timeline"] = state.get("activity_timeline", []) if isinstance(state.get("activity_timeline"), list) else []
        state["milestones"] = state.get("milestones", {}) if isinstance(state.get("milestones"), dict) else {}
        state["routine_stats"] = state.get("routine_stats", {}) if isinstance(state.get("routine_stats"), dict) else {}
        state["secret_progress"] = state.get("secret_progress", {}) if isinstance(state.get("secret_progress"), dict) else {}

        for key, value in {
            "quizzes_finished": 0,
            "workspace_reviews": 0,
            "focus_sprints_completed": 0,
            "words_written": 0,
            "writing_xp_buffer": 0,
            "todo_fixed": 0,
            "plugin_uses": 0,
        }.items():
            state["stats"][key] = self._safe_int(state["stats"].get(key, value), value, minimum=0)

        for key in ("writing_days", "focus_days", "review_days"):
            state["streaks"][key] = self._safe_int(state["streaks"].get(key, 0), 0, minimum=0)

        for key, value in {
            "writing_streak_3": False,
            "focus_streak_3": False,
            "workspace_reviews_5": False,
            "words_written_1000": False,
            "todo_fixed_25": False,
        }.items():
            state["milestones"][key] = bool(state["milestones"].get(key, value))

        for key in ("focus_sprint", "workspace_search", "command_palette", "bug_hunt", "daily_briefing"):
            row = state["routine_stats"].get(key, {})
            if not isinstance(row, dict):
                row = {}
            state["routine_stats"][key] = {
                "runs": self._safe_int(row.get("runs", 0), 0, minimum=0),
                "last_run": str(row.get("last_run", "") or ""),
            }

        for key in ("night_owl_sessions", "keyboard_shortcuts", "vault_keeper_notes"):
            state["secret_progress"][key] = self._safe_int(state["secret_progress"].get(key, 0), 0, minimum=0)

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
                "xp": self._safe_int(raw.get("xp", 0), 0, minimum=0),
                "tier": self._safe_int(raw.get("tier", 1), 1, minimum=1),
                "unlocks": sorted({str(x) for x in raw.get("unlocks", []) if str(x).strip()}),
            }

    def _level_from_xp(self, xp: int) -> int:
        """Handle level from xp."""
        return max(1, 1 + (max(0, xp) // XP_PER_LEVEL))

    def award_xp(self, amount: int, reason: str, *, skill_branch: str | None = None) -> XPResult:
        """Handle award xp."""
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
        """Sync level unlocks."""
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
        """Sync branch unlocks."""
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
        """Sync companion."""
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
        """Add achievement."""
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
        """Apply stat delta."""
        state = self.state()
        current = int(state["stats"].get(key, 0) or 0)
        state["stats"][key] = max(0, current + int(delta or 0))
        return int(state["stats"][key])

    def push_activity(self, title: str, detail: str = "") -> None:
        """Handle push activity."""
        state = self.state()
        rows = state.get("activity_timeline", [])
        if not isinstance(rows, list):
            rows = []
            state["activity_timeline"] = rows
        rows.append(
            {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "title": str(title or "").strip() or "Activity",
                "detail": str(detail or "").strip(),
            }
        )
        if len(rows) > 20:
            del rows[:-20]

    def activity_timeline_lines(self) -> list[str]:
        """Handle activity timeline lines."""
        rows = self.state().get("activity_timeline", [])
        if not isinstance(rows, list):
            return []
        out: list[str] = []
        for row in rows[-8:]:
            if not isinstance(row, dict):
                continue
            ts = str(row.get("ts", "") or "").strip()
            title = str(row.get("title", "") or "").strip()
            detail = str(row.get("detail", "") or "").strip()
            stamp = ts[11:16] if len(ts) >= 16 else ts
            out.append(f"{stamp}  {title}" + (f" | {detail}" if detail else ""))
        return list(reversed(out))

    def quests_snapshot(self, now: datetime | None = None) -> dict[str, Any]:
        """Handle quests snapshot."""
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
        """Handle bump quest."""
        quests = self.quests_snapshot()
        row = quests.get(bucket, {}).get(quest_id)
        if not isinstance(row, dict):
            return False
        was_done = bool(row.get("done", False))
        row["progress"] = min(int(row.get("target", 1)), int(row.get("progress", 0)) + max(1, int(amount or 1)))
        row["done"] = bool(row["progress"] >= int(row.get("target", 1)))
        return bool(row["done"] and not was_done)

    def mark_quiz_finished(self) -> tuple[XPResult, list[str]]:
        """Mark quiz finished."""
        done: list[str] = []
        self.apply_stat_delta("quizzes_finished", 1)
        if self._bump_quest("daily", "complete_quiz", 1):
            done.append("Daily quest complete: Complete 1 quiz")
        res = self.award_xp(40, "Quiz finished", skill_branch="research")
        if self.apply_stat_delta("quizzes_finished", 0) >= 10 and self.add_achievement("Quiz Apprentice"):
            done.append("Achievement unlocked: Quiz Apprentice")
        return res, done

    def mark_workspace_review(self) -> tuple[XPResult, list[str]]:
        """Mark workspace review."""
        done: list[str] = []
        self.apply_stat_delta("workspace_reviews", 1)
        if self._bump_quest("weekly", "workspace_review", 1):
            done.append("Weekly quest complete: Run workspace review")
        res = self.award_xp(25, "Workspace review", skill_branch="coding")
        return res, done

    def mark_focus_sprint_completed(self) -> tuple[XPResult, list[str]]:
        """Mark focus sprint completed."""
        done: list[str] = []
        self.apply_stat_delta("focus_sprints_completed", 1)
        if self._bump_quest("weekly", "focus_sprint", 1):
            done.append("Weekly quest complete: Finish 3 focus sprints")
        res = self.award_xp(30, "Focus sprint completed", skill_branch="writing")
        return res, done

    def mark_plugin_used(self) -> tuple[XPResult, list[str]]:
        """Mark plugin used."""
        done: list[str] = []
        self.apply_stat_delta("plugin_uses", 1)
        if self._bump_quest("weekly", "plugin_use", 1):
            done.append("Weekly quest complete: Use plugin features 2 times")
        res = self.award_xp(15, "Plugin feature used", skill_branch="ai_workflow")
        return res, done

    def add_written_words(self, words: int) -> tuple[XPResult | None, list[str]]:
        """Add written words."""
        if words <= 0:
            return None, []
        done: list[str] = []
        self.apply_stat_delta("words_written", words)
        if self._bump_quest("daily", "write_words", words):
            done.append("Daily quest complete: Write 300 words")
        state = self.state()
        stats = state.get("stats", {})
        buffer_words = self._safe_int(stats.get("writing_xp_buffer", 0), 0, minimum=0) + int(words)
        xp_chunks = buffer_words // 25
        stats["writing_xp_buffer"] = buffer_words % 25
        if xp_chunks <= 0:
            return None, done
        res = self.award_xp(xp_chunks, "Writing progress", skill_branch="writing")
        return res, done

    def add_todo_fixed(self, count: int = 1) -> tuple[XPResult | None, list[str]]:
        """Add todo fixed."""
        if count <= 0:
            return None, []
        done: list[str] = []
        self.apply_stat_delta("todo_fixed", count)
        if self._bump_quest("daily", "todo_fix", count):
            done.append("Daily quest complete: Fix 3 TODOs")
        res = self.award_xp(count * 8, "TODO fixes", skill_branch="coding")
        return res, done

    def set_challenge_state(self, challenge_id: str, active: bool, payload: dict[str, Any] | None = None) -> None:
        """Replace the saved state for a named challenge."""
        state = self.state()["challenge_modes"]
        row = state.get(challenge_id)
        if not isinstance(row, dict):
            row = {}
            state[challenge_id] = row
        row["active"] = bool(active)
        row["updated_at"] = datetime.now().isoformat(timespec="seconds")
        if payload:
            row.update(payload)

    def record_activity_day(self, activity_key: str, now: datetime | None = None) -> int:
        """Record activity day."""
        stamp = now or datetime.now()
        day_key = stamp.date().isoformat()
        state = self.state()
        activity = state["activity_log"]
        streaks = state["streaks"]
        last_key_name = f"{activity_key}_last_day"
        if activity.get(last_key_name) == day_key:
            return int(streaks.get(activity_key, 0) or 0)
        previous = str(activity.get(last_key_name, "") or "")
        current = int(streaks.get(activity_key, 0) or 0)
        try:
            prev_day = date.fromisoformat(previous) if previous else None
        except Exception:
            prev_day = None
        if prev_day is not None and (stamp.date() - prev_day).days == 1:
            current += 1
        else:
            current = 1
        streaks[activity_key] = current
        activity[last_key_name] = day_key
        return current

    def active_events(self, now: date | None = None) -> list[dict[str, str]]:
        """Handle active events."""
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
                    rows.append(
                        {
                            "name": name,
                            "theme_pack": str(row.get("theme_pack", "")),
                            "badge": str(row.get("badge", "")),
                            "quest_label": str(row.get("quest_label", "")),
                            "progress_key": str(row.get("progress_key", "")),
                            "target": str(row.get("target", "1")),
                        }
                    )

        year = today.year
        defaults = [
            {
                "name": "Markdown Week",
                "start": date(year, 3, 1),
                "end": date(year, 3, 7),
                "theme_pack": "Paper Sprint",
                "badge": "Markdown Maven",
                "quest_label": "Write 500 words and finish 1 focus sprint",
                "progress_key": "markdown_week",
                "target": 2,
            },
            {
                "name": "Refactor Month",
                "start": date(year, 10, 1),
                "end": date(year, 10, 31),
                "theme_pack": "Clean Code",
                "badge": "Refactor Ranger",
                "quest_label": "Run 3 workspace reviews and clean 10 TODOs",
                "progress_key": "refactor_month",
                "target": 2,
            },
        ]
        for row in defaults:
            if row["start"] <= today <= row["end"]:
                rows.append(
                    {
                        "name": row["name"],
                        "theme_pack": row["theme_pack"],
                        "badge": row["badge"],
                        "quest_label": row["quest_label"],
                        "progress_key": row["progress_key"],
                        "target": str(row["target"]),
                    }
                )
        return rows

    def sync_active_event_progress(self) -> list[str]:
        """Sync active event progress."""
        state = self.state()
        stats = state.get("stats", {})
        events_state = state.get("events_state", {})
        unlocked: list[str] = []
        for row in self.active_events():
            progress_key = str(row.get("progress_key", "") or "").strip()
            badge = str(row.get("badge", "") or "").strip()
            if not progress_key:
                continue
            target = max(1, int(str(row.get("target", "1") or "1")))
            current = 0
            if progress_key == "markdown_week":
                if int(stats.get("words_written", 0) or 0) >= 500:
                    current += 1
                if int(stats.get("focus_sprints_completed", 0) or 0) >= 1:
                    current += 1
            elif progress_key == "refactor_month":
                if int(stats.get("workspace_reviews", 0) or 0) >= 3:
                    current += 1
                if int(stats.get("todo_fixed", 0) or 0) >= 10:
                    current += 1
            event_row = events_state.get(progress_key)
            if not isinstance(event_row, dict):
                event_row = {}
                events_state[progress_key] = event_row
            event_row["progress"] = min(target, current)
            event_row["target"] = target
            event_row["done"] = bool(current >= target)
            event_row["label"] = str(row.get("quest_label", "") or row.get("name", ""))
            if bool(event_row["done"]) and badge and badge not in state["event_badges"]:
                state["event_badges"] = sorted(set(state["event_badges"]) | {badge})
                unlocked.append(badge)
        return unlocked

    def active_event_snapshot(self) -> list[dict[str, str]]:
        """Handle active event snapshot."""
        state = self.state()
        events_state = state.get("events_state", {})
        out: list[dict[str, str]] = []
        for row in self.active_events():
            progress_key = str(row.get("progress_key", "") or "").strip()
            event_row = events_state.get(progress_key, {}) if progress_key else {}
            progress = self._safe_int(event_row.get("progress", 0), 0, minimum=0) if isinstance(event_row, dict) else 0
            target = (
                self._safe_int(event_row.get("target", row.get("target", "1")), 1, minimum=1)
                if isinstance(event_row, dict)
                else self._safe_int(row.get("target", "1"), 1, minimum=1)
            )
            done = bool(event_row.get("done", False)) if isinstance(event_row, dict) else False
            out.append(
                {
                    "name": str(row.get("name", "") or ""),
                    "theme_pack": str(row.get("theme_pack", "") or ""),
                    "badge": str(row.get("badge", "") or ""),
                    "quest_label": str(row.get("quest_label", "") or ""),
                    "progress": str(progress),
                    "target": str(target),
                    "done": "Yes" if done else "No",
                }
            )
        return out

    def progress_snapshot(self) -> dict[str, str]:
        """Handle progress snapshot."""
        state = self.state()
        quests = self.quests_snapshot()
        companion = state.get("companion", {}) if isinstance(state.get("companion"), dict) else {}
        summary = (
            f"LVL {state.get('level', 1)} | XP {state.get('xp', 0)} | "
            f"{companion.get('name', 'Byte')}:{companion.get('stage', 'Seed')}"
        )
        quest_text = "Today: No quest"
        tooltip_parts = [summary]
        daily = quests.get("daily", {})
        if isinstance(daily, dict):
            active_rows = [row for row in daily.values() if isinstance(row, dict)]
            active_rows.sort(
                key=lambda row: (
                    bool(row.get("done", False)),
                    -(
                        self._safe_int(row.get("target", 1), 1, minimum=1)
                        - self._safe_int(row.get("progress", 0), 0, minimum=0)
                    ),
                )
            )
            if active_rows:
                row = active_rows[0]
                quest_text = (
                    f"Today: {row.get('label', 'Quest')} "
                    f"({self._safe_int(row.get('progress', 0), 0, minimum=0)}/{self._safe_int(row.get('target', 1), 1, minimum=1)})"
                )
                tooltip_parts.append(quest_text)
        achievements = state.get("achievements", [])
        if isinstance(achievements, list) and achievements:
            tooltip_parts.append(f"Achievements: {len(achievements)}")
        return {
            "summary": summary,
            "quest": quest_text,
            "tooltip": " | ".join(part for part in tooltip_parts if part),
        }

    def sync_milestones(self) -> list[str]:
        """Sync milestones."""
        state = self.state()
        stats = state.get("stats", {})
        streaks = state.get("streaks", {})
        milestones = state.get("milestones", {})
        defs = [
            ("writing_streak_3", int(streaks.get("writing_days", 0) or 0) >= 3, "Writing Streak", "Write across 3 days."),
            ("focus_streak_3", int(streaks.get("focus_days", 0) or 0) >= 3, "Focus Chain", "Complete focus work on 3 days."),
            (
                "workspace_reviews_5",
                int(stats.get("workspace_reviews", 0) or 0) >= 5,
                "Review Cadence",
                "Run 5 workspace reviews.",
            ),
            (
                "words_written_1000",
                int(stats.get("words_written", 0) or 0) >= 1000,
                "Kiloword",
                "Write 1000 words total.",
            ),
            ("todo_fixed_25", int(stats.get("todo_fixed", 0) or 0) >= 25, "Cleanup Crew", "Fix 25 TODO markers."),
        ]
        unlocked: list[str] = []
        for key, ready, title, detail in defs:
            if ready and not bool(milestones.get(key, False)):
                milestones[key] = True
                unlocked.append(f"{title}: {detail}")
        return unlocked

    def milestone_snapshot(self) -> list[str]:
        """Handle milestone snapshot."""
        state = self.state()
        stats = state.get("stats", {})
        streaks = state.get("streaks", {})
        milestones = state.get("milestones", {})
        rows = [
            (
                "Writing Streak",
                int(streaks.get("writing_days", 0) or 0),
                3,
                bool(milestones.get("writing_streak_3", False)),
            ),
            (
                "Focus Chain",
                int(streaks.get("focus_days", 0) or 0),
                3,
                bool(milestones.get("focus_streak_3", False)),
            ),
            (
                "Review Cadence",
                int(stats.get("workspace_reviews", 0) or 0),
                5,
                bool(milestones.get("workspace_reviews_5", False)),
            ),
            (
                "Kiloword",
                int(stats.get("words_written", 0) or 0),
                1000,
                bool(milestones.get("words_written_1000", False)),
            ),
            (
                "Cleanup Crew",
                int(stats.get("todo_fixed", 0) or 0),
                25,
                bool(milestones.get("todo_fixed_25", False)),
            ),
        ]
        return [
            f"{title}: {min(target, progress)}/{target}" + (" | Complete" if done else "")
            for title, progress, target, done in rows
        ]

    def easter_egg_snapshot(self) -> list[dict[str, str]]:
        """Handle easter egg snapshot."""
        state = self.state()
        stats = state.get("stats", {})
        secret_progress = state.get("secret_progress", {})
        achievements = {str(item).strip() for item in state.get("achievements", []) if str(item).strip()}
        catalog = [
            (
                "Night Owl",
                min(1, int(secret_progress.get("night_owl_sessions", 0) or 0)),
                1,
                "Write late into the night.",
            ),
            (
                "Keyboard Only",
                min(50, int(secret_progress.get("keyboard_shortcuts", 0) or 0)),
                50,
                "Lean on shortcuts for a full session.",
            ),
            (
                "Zero TODO Day",
                min(25, int(stats.get("todo_fixed", 0) or 0)),
                25,
                "Clear lingering TODO markers.",
            ),
            (
                "Focus Beast",
                min(7, int(stats.get("focus_sprints_completed", 0) or 0)),
                7,
                "Chain multiple focus sprints.",
            ),
            (
                "Explorer",
                min(5, int(stats.get("workspace_reviews", 0) or 0)),
                5,
                "Keep reviewing the workspace.",
            ),
            (
                "Plugin Tinkerer",
                min(5, int(stats.get("plugin_uses", 0) or 0)),
                5,
                "Use advanced plugin-powered flows.",
            ),
            (
                "Vault Keeper",
                min(3, int(secret_progress.get("vault_keeper_notes", 0) or 0)),
                3,
                "Protect a few sensitive notes.",
            ),
        ]
        rows: list[dict[str, str]] = []
        for title, progress, target, hint in catalog:
            unlocked = title in achievements
            rows.append(
                {
                    "title": title,
                    "progress": str(progress),
                    "target": str(target),
                    "status": "Unlocked" if unlocked else "Hidden",
                    "hint": hint,
                }
            )
        return rows

    def secret_trail_lines(self) -> list[str]:
        """Handle secret trail lines."""
        rows = self.easter_egg_snapshot()
        pending = [row for row in rows if row.get("status") != "Unlocked"]
        pending.sort(key=lambda row: int(row.get("target", "1")) - int(row.get("progress", "0")))
        preview = pending[:3] if pending else rows[:3]
        return [
            (
                f"{row.get('title', 'Secret')}: {row.get('progress', '0')}/{row.get('target', '1')}"
                f" | {row.get('hint', '')}"
            )
            for row in preview
        ]

    def next_secret_hint(self) -> str:
        """Handle next secret hint."""
        rows = self.easter_egg_snapshot()
        pending = [row for row in rows if row.get("status") != "Unlocked"]
        if not pending:
            return "Secret trail: all current hidden rewards uncovered."
        row = min(pending, key=lambda item: int(item.get("target", "1")) - int(item.get("progress", "0")))
        remaining = max(0, int(row.get("target", "1")) - int(row.get("progress", "0")))
        return f"Secret trail: {row.get('title', 'Secret')} is {remaining} step(s) away."

    def next_milestone_hint(self) -> str:
        """Handle next milestone hint."""
        state = self.state()
        stats = state.get("stats", {})
        streaks = state.get("streaks", {})
        candidates = [
            ("Writing Streak", 3 - int(streaks.get("writing_days", 0) or 0), "day(s) of writing"),
            ("Focus Chain", 3 - int(streaks.get("focus_days", 0) or 0), "focus day(s)"),
            ("Review Cadence", 5 - int(stats.get("workspace_reviews", 0) or 0), "workspace review(s)"),
            ("Kiloword", 1000 - int(stats.get("words_written", 0) or 0), "word(s)"),
            ("Cleanup Crew", 25 - int(stats.get("todo_fixed", 0) or 0), "TODO fix(es)"),
        ]
        pending = [(title, remaining, unit) for title, remaining, unit in candidates if remaining > 0]
        if not pending:
            return "Next milestone: all current milestone tracks complete."
        title, remaining, unit = min(pending, key=lambda row: row[1])
        return f"Next milestone: {title} in {remaining} more {unit}"

    def productivity_snapshot(self) -> dict[str, Any]:
        """Handle productivity snapshot."""
        state = self.state()
        payload = self.progress_snapshot()
        quests = self.quests_snapshot()
        quest_rows: list[str] = []
        for bucket_name, label in (("daily", "Daily"), ("weekly", "Weekly")):
            bucket = quests.get(bucket_name, {})
            if not isinstance(bucket, dict):
                continue
            for row in bucket.values():
                if not isinstance(row, dict):
                    continue
                quest_rows.append(
                    f"{label}: {row.get('label', 'Quest')} ({int(row.get('progress', 0))}/{int(row.get('target', 1))})"
                )
        streaks = state.get("streaks", {})
        achievements = state.get("achievements", [])
        next_unlock = self.next_unlock_hint()
        recommendation = self.recommended_action()
        routines = self.productivity_routines()
        return {
            "summary": payload["summary"],
            "streaks": (
                f"Streaks: writing {int(streaks.get('writing_days', 0))} | "
                f"focus {int(streaks.get('focus_days', 0))} | "
                f"review {int(streaks.get('review_days', 0))}"
            ),
            "next_unlock": next_unlock,
            "companion_hint": self.companion_hint(),
            "quests": quest_rows[:8],
            "recent_unlocks": list(achievements[-6:] if isinstance(achievements, list) else []),
            "briefing": self.daily_briefing(),
            "events": self.active_event_snapshot(),
            "session_review": self.session_review_lines(),
            "milestones": self.milestone_snapshot(),
            "next_milestone": self.next_milestone_hint(),
            "secret_trails": self.secret_trail_lines(),
            "next_secret": self.next_secret_hint(),
            "routines": [str(row.get("label", "")) for row in routines[:4]],
            "next_routine": self.next_routine_hint(),
            "primary_routine_label": str(routines[0].get("action_label", "") if routines else "Run Routine"),
            "routine_history": self.routine_history_lines(),
            "recommended_action_label": str(recommendation.get("label", "") or "Open Daily Briefing"),
            "recommended_action_detail": str(recommendation.get("detail", "") or "Check your next best move."),
            "activity_timeline": self.activity_timeline_lines(),
        }

    def productivity_routines(self) -> list[dict[str, str]]:
        """Handle productivity routines."""
        stats = self.state().get("stats", {})
        quests = self.quests_snapshot()
        rows: list[dict[str, str]] = []
        daily = quests.get("daily", {})
        if isinstance(daily, dict):
            write_words = daily.get("write_words", {})
            if isinstance(write_words, dict) and not bool(write_words.get("done", False)):
                remaining = max(0, int(write_words.get("target", 300)) - int(write_words.get("progress", 0)))
                rows.append(
                    {
                        "routine_id": "focus_sprint",
                        "label": f"Writing Push: clear {remaining} more word(s) with a focus sprint.",
                        "action_label": "Start Writing Push",
                    }
                )
        if int(stats.get("workspace_reviews", 0) or 0) < 1:
            rows.append(
                {
                    "routine_id": "workspace_search",
                    "label": "Workspace Sweep: scan the repo and review hotspots before editing.",
                    "action_label": "Run Workspace Sweep",
                }
            )
        if int(stats.get("plugin_uses", 0) or 0) < 2:
            rows.append(
                {
                    "routine_id": "command_palette",
                    "label": "Power Path: use the command palette to reach an advanced action quickly.",
                    "action_label": "Open Power Path",
                }
            )
        if int(stats.get("todo_fixed", 0) or 0) < 10:
            rows.append(
                {
                    "routine_id": "bug_hunt",
                    "label": "Cleanup Loop: run a bug hunt and knock out lingering TODO markers.",
                    "action_label": "Start Cleanup Loop",
                }
            )
        rows.append(
            {
                "routine_id": "daily_briefing",
                "label": "Planning Loop: review your briefing, streaks, and next unlock before the next move.",
                "action_label": "Open Planning Loop",
            }
        )
        deduped: list[dict[str, str]] = []
        seen: set[str] = set()
        for row in rows:
            routine_id = str(row.get("routine_id", "") or "").strip()
            if not routine_id or routine_id in seen:
                continue
            seen.add(routine_id)
            deduped.append(row)
        return deduped

    def next_routine_hint(self) -> str:
        """Handle next routine hint."""
        routines = self.productivity_routines()
        if not routines:
            return "Routine ready: no suggested workflow yet."
        return f"Routine ready: {str(routines[0].get('label', '') or 'Start your next workflow.')}"

    def record_routine_run(self, routine_id: str) -> dict[str, str]:
        """Record routine run."""
        state = self.state()
        key = str(routine_id or "").strip() or "daily_briefing"
        row = state["routine_stats"].get(key, {})
        if not isinstance(row, dict):
            row = {}
        row["runs"] = max(0, int(row.get("runs", 0) or 0)) + 1
        row["last_run"] = datetime.now().isoformat(timespec="seconds")
        state["routine_stats"][key] = row
        return {"routine_id": key, "runs": str(row["runs"]), "last_run": str(row["last_run"])}

    def set_secret_progress_max(self, key: str, value: int) -> int:
        """Set the maximum progress value tracked for a secret objective."""
        state = self.state()
        secret_progress = state.get("secret_progress", {})
        if not isinstance(secret_progress, dict):
            secret_progress = {}
            state["secret_progress"] = secret_progress
        name = str(key or "").strip()
        if not name:
            return 0
        current = max(0, int(secret_progress.get(name, 0) or 0))
        secret_progress[name] = max(current, max(0, int(value or 0)))
        return int(secret_progress[name])

    def routine_history_lines(self) -> list[str]:
        """Handle routine history lines."""
        stats = self.state().get("routine_stats", {})
        if not isinstance(stats, dict):
            return []
        labels = {
            "focus_sprint": "Writing Push",
            "workspace_search": "Workspace Sweep",
            "command_palette": "Power Path",
            "bug_hunt": "Cleanup Loop",
            "daily_briefing": "Planning Loop",
        }
        rows: list[tuple[int, str]] = []
        for key, label in labels.items():
            row = stats.get(key, {})
            if not isinstance(row, dict):
                continue
            runs = max(0, int(row.get("runs", 0) or 0))
            if runs <= 0:
                continue
            last_run = str(row.get("last_run", "") or "")
            stamp = last_run[11:16] if len(last_run) >= 16 else "recently"
            rows.append((runs, f"{label}: {runs} run(s) | last at {stamp}"))
        rows.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in rows[:5]]

    def next_unlock_hint(self) -> str:
        """Handle next unlock hint."""
        state = self.state()
        stats = state.get("stats", {})
        level = int(state.get("level", 1) or 1)
        focus = int(stats.get("focus_sprints_completed", 0) or 0)
        plugins = int(stats.get("plugin_uses", 0) or 0)
        reviews = int(stats.get("workspace_reviews", 0) or 0)
        todos = int(stats.get("todo_fixed", 0) or 0)
        if level < 2:
            return f"Next unlock: reach Level 2 for Sunrise Sprint theme ({XP_PER_LEVEL - int(state.get('xp', 0))} XP left)"
        if focus < 7:
            return f"Next unlock: finish {7 - focus} more focus sprint(s) for Focus Beast"
        if plugins < 5:
            return f"Next unlock: use plugin features {5 - plugins} more time(s) for Plugin Tinkerer"
        if reviews < 5:
            return f"Next unlock: run {5 - reviews} more workspace review(s) for Explorer"
        if todos < 25:
            return f"Next unlock: fix {25 - todos} more TODOs for Zero TODO Day"
        return "Next unlock: keep exploring for more hidden badges"

    def companion_hint(self) -> str:
        """Handle companion hint."""
        state = self.state()
        stats = state.get("stats", {})
        streaks = state.get("streaks", {})
        quests = self.quests_snapshot()
        daily = quests.get("daily", {})
        incomplete: list[dict[str, Any]] = []
        if isinstance(daily, dict):
            incomplete = [row for row in daily.values() if isinstance(row, dict) and not bool(row.get("done", False))]
        if incomplete:
            row = incomplete[0]
            remaining = max(0, int(row.get("target", 1)) - int(row.get("progress", 0)))
            return f"Byte says: {remaining} step(s) left for '{row.get('label', 'today')}'."
        if int(streaks.get("focus_days", 0) or 0) == 0:
            return "Byte says: try a focus sprint to wake up your weekly streak."
        if int(stats.get("workspace_reviews", 0) or 0) == 0:
            return "Byte says: run a workspace review this week for a clean momentum boost."
        if int(stats.get("plugin_uses", 0) or 0) < 2:
            return "Byte says: one plugin-powered action will move your weekly quest forward."
        return "Byte says: keep the streak alive and chase the next unlock."

    def daily_briefing(self) -> list[str]:
        """Handle daily briefing."""
        state = self.state()
        stats = state.get("stats", {})
        streaks = state.get("streaks", {})
        rows = [
            self.progress_snapshot()["quest"],
            self.next_unlock_hint(),
            f"Focus streak: {int(streaks.get('focus_days', 0) or 0)} day(s)",
        ]
        if int(stats.get("workspace_reviews", 0) or 0) == 0:
            rows.append("Suggested next move: run a workspace review.")
        elif int(stats.get("focus_sprints_completed", 0) or 0) < 3:
            rows.append("Suggested next move: finish another focus sprint.")
        else:
            rows.append("Suggested next move: craft or use a tool to keep momentum high.")
        return rows

    def event_briefing(self) -> list[str]:
        """Handle event briefing."""
        rows: list[str] = []
        for row in self.active_event_snapshot():
            rows.append(
                f"{row.get('name', '')}: {row.get('quest_label', '')} "
                f"({row.get('progress', '0')}/{row.get('target', '1')})"
            )
        if not rows:
            rows.append("No seasonal event is active right now.")
        return rows

    def record_session_review(self, *, open_tabs: int = 0, saved_session: bool = False) -> dict[str, Any]:
        """Record session review."""
        state = self.state()
        stats = state.get("stats", {})
        streaks = state.get("streaks", {})
        review = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "open_tabs": max(0, int(open_tabs or 0)),
            "saved_session": bool(saved_session),
            "words_written": int(stats.get("words_written", 0) or 0),
            "todo_fixed": int(stats.get("todo_fixed", 0) or 0),
            "focus_sprints_completed": int(stats.get("focus_sprints_completed", 0) or 0),
            "workspace_reviews": int(stats.get("workspace_reviews", 0) or 0),
            "writing_streak": int(streaks.get("writing_days", 0) or 0),
            "focus_streak": int(streaks.get("focus_days", 0) or 0),
            "review_streak": int(streaks.get("review_days", 0) or 0),
            "next_unlock": self.next_unlock_hint(),
            "companion_hint": self.companion_hint(),
        }
        state["session_review"] = review
        return review

    def session_review_lines(self) -> list[str]:
        """Handle session review lines."""
        review = self.state().get("session_review", {})
        if not isinstance(review, dict) or not review:
            return []
        lines = [
            f"Words written: {int(review.get('words_written', 0) or 0)} | TODOs fixed: {int(review.get('todo_fixed', 0) or 0)}",
            (
                f"Focus sprints: {int(review.get('focus_sprints_completed', 0) or 0)} | "
                f"Workspace reviews: {int(review.get('workspace_reviews', 0) or 0)}"
            ),
            (
                f"Streaks: writing {int(review.get('writing_streak', 0) or 0)} | "
                f"focus {int(review.get('focus_streak', 0) or 0)} | "
                f"review {int(review.get('review_streak', 0) or 0)}"
            ),
            f"Open tabs at review: {int(review.get('open_tabs', 0) or 0)}",
            f"Session saved: {'Yes' if bool(review.get('saved_session', False)) else 'No'}",
            str(review.get("next_unlock", "") or "Next unlock: keep going"),
        ]
        return lines

    def recommended_action(self) -> dict[str, str]:
        """Handle recommended action."""
        stats = self.state().get("stats", {})
        quests = self.quests_snapshot()
        daily = quests.get("daily", {})
        weekly = quests.get("weekly", {})
        if isinstance(daily, dict):
            quiz = daily.get("complete_quiz", {})
            if isinstance(quiz, dict) and not bool(quiz.get("done", False)):
                return {
                    "action_id": "daily_briefing",
                    "label": "Review Today",
                    "detail": "Check today's quest progress and finish the open quiz objective.",
                }
            write_words = daily.get("write_words", {})
            if isinstance(write_words, dict) and int(write_words.get("progress", 0) or 0) < 300:
                return {
                    "action_id": "focus_sprint",
                    "label": "Start Focus Sprint",
                    "detail": "A short writing sprint is the fastest way to move today's word quest.",
                }
        if isinstance(weekly, dict):
            review = weekly.get("workspace_review", {})
            if isinstance(review, dict) and not bool(review.get("done", False)):
                return {
                    "action_id": "workspace_search",
                    "label": "Run Workspace Review",
                    "detail": "Search the workspace and review hotspots to advance the weekly coding quest.",
                }
            plugin_use = weekly.get("plugin_use", {})
            if isinstance(plugin_use, dict) and not bool(plugin_use.get("done", False)):
                return {
                    "action_id": "command_palette",
                    "label": "Open Command Palette",
                    "detail": "Use a plugin-powered or advanced command to push weekly momentum forward.",
                }
        if int(stats.get("focus_sprints_completed", 0) or 0) < 3:
            return {
                "action_id": "focus_sprint",
                "label": "Start Focus Sprint",
                "detail": "Build momentum with another sprint and keep the focus streak alive.",
            }
        return {
            "action_id": "daily_briefing",
            "label": "Open Daily Briefing",
            "detail": "Review quests, streaks, and the next unlock before your next move.",
        }
