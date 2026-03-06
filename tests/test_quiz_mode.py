import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from pypad.ui.main_window.misc import MiscMixin
except ModuleNotFoundError:
    from notepadclone.ui.main_window.misc import MiscMixin


class _QuizHarness(MiscMixin):
    pass


class _FakeAnnotationWidget:
    def __init__(self) -> None:
        self.annotations: dict[int, str] = {}

    def annotationClearAll(self) -> None:
        self.annotations.clear()

    def annotationSetText(self, line: int, text: str) -> None:
        self.annotations[int(line)] = str(text)


class _FakeTextEdit:
    def __init__(self, text: str, widget: _FakeAnnotationWidget) -> None:
        self._text = text
        self.widget = widget

    def get_text(self) -> str:
        return self._text


class _FakeTab:
    def __init__(self, text: str, quiz_items: list[dict]) -> None:
        self.quiz_mode_enabled = True
        self.quiz_items = quiz_items
        self.quiz_user_answers: dict[int, str] = {}
        self.text_edit = _FakeTextEdit(text, _FakeAnnotationWidget())


class QuizModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.h = _QuizHarness()

    def test_parse_quiz_blocks_mixed_types(self) -> None:
        text = (
            "1. Capital of France? {answer:B}\n"
            "A. Berlin\n"
            "B. Paris\n\n"
            "Q2: The sky is blue. [answer=true]\n"
            "A) True\n"
            "B) False\n\n"
            "- Explain photosynthesis {keywords: chlorophyll|sunlight|glucose}\n"
        )
        items = self.h._parse_quiz_blocks(text)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["type"], "mcq")
        self.assertEqual(items[1]["type"], "tf")
        self.assertEqual(items[2]["type"], "short")

    def test_parse_accepts_metadata_styles(self) -> None:
        text = (
            "1. Pick one (correct: C)\n"
            "A. One\n"
            "B. Two\n"
            "C. Three\n\n"
            "2. Statement [answer=F]\n"
            "A) True\n"
            "B) False\n"
        )
        items = self.h._parse_quiz_blocks(text)
        self.assertEqual(items[0]["answer"], "C")
        self.assertEqual(items[1]["answer"], "F")

    def test_parse_detects_metadata_started_question_without_number_prefix(self) -> None:
        text = "The moon is made of rock. {answer:true}\n"
        items = self.h._parse_quiz_blocks(text)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["type"], "tf")

    def test_parse_ignores_non_gradable_help_bullets(self) -> None:
        text = (
            "- Question can start with: 1. / Q1: / -\n"
            "- Options can be: A. / B. / C.\n"
            "- Answer metadata accepted:\n"
        )
        items = self.h._parse_quiz_blocks(text)
        self.assertEqual(items, [])

    def test_scoring_tf_tokens_and_partial_keywords(self) -> None:
        items = [
            {"number": 1, "type": "tf", "answer": "F", "keywords": [], "points": 1.0},
            {"number": 2, "type": "short", "answer": "", "keywords": ["alpha", "beta", "gamma"], "points": 2.0},
        ]
        user_answers = {1: "false", 2: "alpha"}
        result = self.h._score_quiz_items(items, user_answers)
        self.assertEqual(result["counts"]["correct"], 1)
        self.assertEqual(result["counts"]["partial"], 1)
        self.assertAlmostEqual(result["earned"], 2.0)
        self.assertAlmostEqual(result["max"], 3.0)

    def test_collect_user_answers_skips_options_and_prompt_text(self) -> None:
        items = [
            {
                "number": 1,
                "type": "mcq",
                "prompt": "1. Capital?",
                "block_start": 0,
                "block_end": 4,
                "option_lines": [1, 2, 3],
                "options": [("A", "Rome", 1), ("B", "Paris", 2), ("C", "Berlin", 3)],
            }
        ]
        text = "1. Capital? B\nA. Rome\nB. Paris\nC. Berlin\n"
        tab = _FakeTab(text, items)
        answers = self.h._collect_user_answers(tab)
        self.assertEqual(answers[1].upper(), "B")

    def test_scoring_mcq_accepts_option_text(self) -> None:
        items = [
            {
                "number": 1,
                "type": "mcq",
                "answer": "B",
                "keywords": [],
                "points": 1.0,
                "options": [("A", "Rome", 1), ("B", "Paris", 2), ("C", "Berlin", 3)],
            }
        ]
        result = self.h._score_quiz_items(items, {1: "Paris"})
        self.assertEqual(result["counts"]["correct"], 1)

    def test_user_anchor_sets_placeholder_and_collects_answer(self) -> None:
        items = [
            {
                "number": 1,
                "type": "short",
                "prompt": "Explain X",
                "block_start": 0,
                "block_end": 3,
                "option_lines": [],
                "user_anchor_line": 1,
                "options": [],
            }
        ]
        text = "1. Explain X\nmy typed answer\n"
        tab = _FakeTab(text, items)
        self.h._refresh_quiz_placeholders_for_tab(tab)
        # Answer exists, so placeholder should not show on anchor.
        self.assertNotIn(1, tab.text_edit.widget.annotations)
        answers = self.h._collect_user_answers(tab)
        self.assertEqual(answers[1], "my typed answer")

    def test_placeholder_shown_only_for_unanswered(self) -> None:
        items = [
            {
                "number": 1,
                "type": "short",
                "prompt": "1. Question one",
                "block_start": 0,
                "block_end": 2,
                "option_lines": [],
                "options": [],
            },
            {
                "number": 2,
                "type": "short",
                "prompt": "2. Question two",
                "block_start": 2,
                "block_end": 4,
                "option_lines": [],
                "options": [],
            },
        ]
        # Q1 has typed answer; Q2 blank.
        text = "1. Question one typed answer\n\n2. Question two\n\n"
        tab = _FakeTab(text, items)
        self.h._refresh_quiz_placeholders_for_tab(tab)
        annotations = tab.text_edit.widget.annotations
        self.assertNotIn(0, annotations)
        self.assertEqual(annotations.get(2), "Your answer...")


if __name__ == "__main__":
    unittest.main()
