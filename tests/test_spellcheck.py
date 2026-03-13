import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypad.ui.editor import spellcheck


class _FakeSpellChecker:
    def __init__(self, language: str = "en") -> None:
        self.language = language
        self.word_frequency = type(
            "_WordFrequency",
            (),
            {"dictionary": {"typed": 10, "nothing": 5, "note": 2}},
        )()

    def unknown(self, words):
        return set(words)

    def candidates(self, word: str):
        if word.lower() == "typo":
            return None
        return {"fixed", "typed"}

    def correction(self, word: str):
        if word.lower() == "typo":
            return ""
        return "fixed"


class SpellcheckTests(unittest.TestCase):
    def test_unknown_words_tolerates_none_candidates(self) -> None:
        with patch.object(spellcheck, "SpellChecker", _FakeSpellChecker):
            spellcheck._spellchecker_for_language.cache_clear()
            rows = spellcheck.unknown_words("typo other", language="en")
        self.assertEqual(rows[0]["suggestions"], ["typed"])
        self.assertEqual(rows[1]["suggestions"], ["fixed", "typed"])

    def test_suggestions_for_word_tolerates_none_candidates(self) -> None:
        with patch.object(spellcheck, "SpellChecker", _FakeSpellChecker):
            spellcheck._spellchecker_for_language.cache_clear()
            self.assertEqual(spellcheck.suggestions_for_word("typo", language="en"), ["typed"])


if __name__ == "__main__":
    unittest.main()
