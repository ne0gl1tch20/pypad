import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypad.ui.main_window.misc import MiscMixin


class _TypingHarness(MiscMixin):
    pass


class TypingSpeedTestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.h = _TypingHarness()

    def test_parse_words_handles_spaces_commas_and_newlines(self) -> None:
        words = self.h._typing_test_parse_words("alpha, beta\ngamma delta-2")
        self.assertEqual(words, ["alpha", "beta", "gamma", "delta-2"])

    def test_build_prompt_words_repeats_in_sequence_mode(self) -> None:
        prompt = self.h._typing_test_build_prompt_words(
            {
                "custom_words": ["red", "blue"],
                "word_count": 10,
                "randomize_words": False,
            }
        )
        self.assertEqual(prompt, ["red", "blue", "red", "blue", "red", "blue", "red", "blue", "red", "blue"])

    def test_extract_typed_text_returns_suffix_after_marker(self) -> None:
        text = "Typing Speed Test\n\nType here:\nhello world"
        self.assertEqual(self.h._typing_test_extract_typed_text(text), "hello world")

    def test_score_reports_accuracy_and_word_counts(self) -> None:
        result = self.h._typing_test_score(
            ["alpha", "beta", "gamma"],
            "alpha beta typo",
            elapsed_sec=30,
            case_sensitive=False,
        )
        self.assertEqual(result["typed_words"], 3)
        self.assertEqual(result["correct_words"], 2)
        self.assertEqual(result["mistakes"], 1)
        self.assertLess(result["accuracy"], 100.0)
        self.assertGreater(result["gross_wpm"], 0.0)

    def test_score_honors_case_sensitive_mode(self) -> None:
        insensitive = self.h._typing_test_score(
            ["Alpha"],
            "alpha",
            elapsed_sec=20,
            case_sensitive=False,
        )
        sensitive = self.h._typing_test_score(
            ["Alpha"],
            "alpha",
            elapsed_sec=20,
            case_sensitive=True,
        )
        self.assertEqual(insensitive["correct_words"], 1)
        self.assertEqual(sensitive["correct_words"], 0)


if __name__ == "__main__":
    unittest.main()
