import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypad.ui.features.gamification_system import GamificationSystem


class GamificationSystemTests(unittest.TestCase):
    def test_progress_snapshot_prefers_incomplete_daily_quest(self) -> None:
        system = GamificationSystem({})
        system.quests_snapshot()
        payload = system.progress_snapshot()
        self.assertIn("LVL 1", payload["summary"])
        self.assertIn("Today:", payload["quest"])
        self.assertIn("(0/", payload["quest"])

    def test_progress_snapshot_reflects_xp_and_achievements(self) -> None:
        settings = {}
        system = GamificationSystem(settings)
        system.award_xp(240, "Deep work", skill_branch="writing")
        system.add_achievement("Night Owl")
        payload = system.progress_snapshot()
        self.assertIn("LVL 3", payload["summary"])
        self.assertIn("Achievements: 1", payload["tooltip"])

    def test_productivity_snapshot_includes_streaks_and_unlock_hint(self) -> None:
        system = GamificationSystem({})
        system.record_activity_day("writing_days")
        system.sync_active_event_progress()
        payload = system.productivity_snapshot()
        self.assertIn("writing 1", payload["streaks"])
        self.assertTrue(payload["next_unlock"].startswith("Next unlock:"))
        self.assertGreaterEqual(len(payload["quests"]), 1)
        self.assertIn("Byte says:", payload["companion_hint"])
        self.assertGreaterEqual(len(payload["briefing"]), 3)
        self.assertIn("events", payload)
        self.assertIn("routines", payload)
        self.assertTrue(payload["next_routine"].startswith("Routine ready:"))

    def test_active_event_snapshot_tracks_progress_and_badges(self) -> None:
        system = GamificationSystem(
            {
                "gamification_custom_events": [
                    {
                        "name": "Custom Sprint",
                        "start": "2026-03-01",
                        "end": "2026-03-31",
                        "theme_pack": "Paper Sprint",
                        "badge": "Markdown Maven",
                        "quest_label": "Write and sprint",
                        "progress_key": "markdown_week",
                        "target": 2,
                    }
                ]
            }
        )
        system.add_written_words(500)
        system.mark_focus_sprint_completed()
        unlocked = system.sync_active_event_progress()
        snapshot = system.active_event_snapshot()
        self.assertTrue(any(row["name"] == "Custom Sprint" for row in snapshot))
        custom = next(row for row in snapshot if row["name"] == "Custom Sprint")
        self.assertEqual(custom["progress"], "2")
        self.assertIn("Markdown Maven", unlocked)

    def test_active_event_badge_is_not_granted_before_event_objective_is_done(self) -> None:
        system = GamificationSystem(
            {
                "gamification_custom_events": [
                    {
                        "name": "Custom Sprint",
                        "start": "2026-03-01",
                        "end": "2026-03-31",
                        "theme_pack": "Paper Sprint",
                        "badge": "Markdown Maven",
                        "quest_label": "Write and sprint",
                        "progress_key": "markdown_week",
                        "target": 2,
                    }
                ]
            }
        )
        unlocked = system.sync_active_event_progress()
        state = system.state()
        snapshot = system.active_event_snapshot()
        self.assertEqual(unlocked, [])
        self.assertNotIn("Markdown Maven", state["event_badges"])
        custom = next(row for row in snapshot if row["name"] == "Custom Sprint")
        self.assertEqual(custom["progress"], "0")
        self.assertEqual(custom["done"], "No")

    def test_session_review_lines_capture_summary(self) -> None:
        system = GamificationSystem({})
        system.add_written_words(220)
        system.add_todo_fixed(4)
        system.mark_focus_sprint_completed()
        review = system.record_session_review(open_tabs=3, saved_session=True)
        self.assertEqual(review["open_tabs"], 3)
        lines = system.session_review_lines()
        self.assertTrue(any("Words written" in line for line in lines))
        self.assertTrue(any("Session saved: Yes" in line for line in lines))

    def test_recommended_action_prioritizes_open_quest(self) -> None:
        system = GamificationSystem({})
        recommendation = system.recommended_action()
        self.assertEqual(recommendation["action_id"], "daily_briefing")
        system.mark_quiz_finished()
        system.add_written_words(300)
        recommendation = system.recommended_action()
        self.assertIn(recommendation["action_id"], {"workspace_search", "command_palette", "focus_sprint", "daily_briefing"})

    def test_activity_timeline_keeps_recent_entries(self) -> None:
        system = GamificationSystem({})
        for idx in range(25):
            system.push_activity(f"Step {idx}", "detail")
        lines = system.activity_timeline_lines()
        self.assertLessEqual(len(lines), 8)
        self.assertTrue(any("Step 24" in line for line in lines))

    def test_milestone_snapshot_and_next_hint_reflect_progress(self) -> None:
        system = GamificationSystem({})
        system.add_written_words(1000)
        system.add_todo_fixed(25)
        unlocked = system.sync_milestones()
        snapshot = system.milestone_snapshot()
        self.assertTrue(any("Kiloword" in row and "Complete" in row for row in snapshot))
        self.assertTrue(any("Cleanup Crew" in row and "Complete" in row for row in snapshot))
        self.assertTrue(any("Kiloword" in row for row in unlocked))
        self.assertTrue(system.next_milestone_hint().startswith("Next milestone:"))

    def test_easter_egg_snapshot_and_secret_hint_reflect_progress(self) -> None:
        system = GamificationSystem({})
        system.add_todo_fixed(10)
        system.mark_focus_sprint_completed()
        system.set_secret_progress_max("keyboard_shortcuts", 12)
        snapshot = system.easter_egg_snapshot()
        self.assertTrue(any(row["title"] == "Zero TODO Day" and row["progress"] == "10" for row in snapshot))
        self.assertTrue(any(row["title"] == "Focus Beast" and row["progress"] == "1" for row in snapshot))
        self.assertTrue(any(row["title"] == "Keyboard Only" and row["progress"] == "12" for row in snapshot))
        self.assertTrue(system.next_secret_hint().startswith("Secret trail:"))
        trails = system.secret_trail_lines()
        self.assertGreaterEqual(len(trails), 1)

    def test_productivity_routines_prioritize_practical_workflows(self) -> None:
        system = GamificationSystem({})
        routines = system.productivity_routines()
        self.assertGreaterEqual(len(routines), 1)
        self.assertEqual(routines[0]["routine_id"], "focus_sprint")
        system.add_written_words(300)
        routines = system.productivity_routines()
        self.assertIn(routines[0]["routine_id"], {"workspace_search", "command_palette", "bug_hunt", "daily_briefing"})

    def test_routine_history_tracks_runs(self) -> None:
        system = GamificationSystem({})
        record = system.record_routine_run("focus_sprint")
        self.assertEqual(record["routine_id"], "focus_sprint")
        self.assertEqual(record["runs"], "1")
        system.record_routine_run("focus_sprint")
        history = system.routine_history_lines()
        self.assertTrue(any("Writing Push: 2 run(s)" in row for row in history))
        payload = system.productivity_snapshot()
        self.assertIn("routine_history", payload)

    def test_add_written_words_buffers_until_25_words_before_awarding_xp(self) -> None:
        system = GamificationSystem({})
        result, notes = system.add_written_words(1)
        self.assertIsNone(result)
        self.assertEqual(notes, [])
        self.assertEqual(system.state()["stats"]["writing_xp_buffer"], 1)
        result, notes = system.add_written_words(24)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.xp_added, 1)
        self.assertEqual(notes, [])
        self.assertEqual(system.state()["stats"]["writing_xp_buffer"], 0)

    def test_state_coercion_handles_invalid_persisted_values(self) -> None:
        system = GamificationSystem(
            {
                "gamification_state": {
                    "xp": "oops",
                    "level": None,
                    "stats": {"words_written": "bad", "todo_fixed": "-3"},
                    "streaks": {"writing_days": "nan"},
                    "routine_stats": {"focus_sprint": {"runs": "x"}},
                    "secret_progress": {"keyboard_shortcuts": "??"},
                    "skill_tree": {"writing": {"xp": "bad", "tier": "?", "unlocks": ["Draft Flow"]}},
                    "events_state": {"markdown_week": {"progress": "oops", "target": "bad", "done": "yes"}},
                }
            }
        )
        state = system.state()
        snapshot = system.active_event_snapshot()
        self.assertEqual(state["xp"], 0)
        self.assertEqual(state["level"], 1)
        self.assertEqual(state["stats"]["words_written"], 0)
        self.assertEqual(state["stats"]["todo_fixed"], 0)
        self.assertEqual(state["streaks"]["writing_days"], 0)
        self.assertEqual(state["routine_stats"]["focus_sprint"]["runs"], 0)
        self.assertEqual(state["secret_progress"]["keyboard_shortcuts"], 0)
        self.assertEqual(state["skill_tree"]["writing"]["xp"], 0)
        self.assertEqual(state["skill_tree"]["writing"]["tier"], 1)
        self.assertEqual(snapshot, [])

    def test_progress_snapshot_tolerates_invalid_quest_numbers(self) -> None:
        system = GamificationSystem({})
        quests = system.quests_snapshot()
        quests["daily"]["write_words"]["progress"] = "bad"
        quests["daily"]["write_words"]["target"] = "also-bad"
        payload = system.progress_snapshot()
        self.assertIn("Today:", payload["quest"])


if __name__ == "__main__":
    unittest.main()
