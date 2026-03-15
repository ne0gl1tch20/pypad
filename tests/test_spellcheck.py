import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypad.ui.editor import spellcheck

TEST_ROOT = ROOT / "tests_tmp" / "spellcheck"


class _FakeSymSpellEngine:
    def __init__(self, language: str = "en") -> None:
        if language != "en":
            raise RuntimeError("unsupported")
        self.language = language
        self.word_frequency = type("_WordFrequency", (), {"dictionary": {"typed": 10, "fixed": 4, "note": 2}})()

    def unknown(self, words):
        return set(words)

    def candidates(self, word: str):
        if word.lower() == "typo":
            return None
        return ["fixed", "typed"]

    def correction(self, word: str):
        if word.lower() == "typo":
            return ""
        return "fixed"


class _FakeHunspellEngine:
    def __init__(self, language: str = "en") -> None:
        self.language = language
        self.word_frequency = type("_WordFrequency", (), {"dictionary": {"typed": 10, "fixed": 4, "hola": 2}})()

    def unknown(self, words):
        return set(words)

    def candidates(self, word: str):
        if word.lower() == "typo":
            return None
        return ["fixed", "typed"]

    def correction(self, word: str):
        if word.lower() == "typo":
            return ""
        return "fixed"


class SpellcheckTests(unittest.TestCase):
    def setUp(self) -> None:
        TEST_ROOT.mkdir(parents=True, exist_ok=True)

    def test_unknown_words_tolerates_none_candidates(self) -> None:
        with patch.object(spellcheck, "_english_spell_engine", return_value=_FakeSymSpellEngine("en")):
            spellcheck._english_spell_engine.cache_clear()
            spellcheck._spellchecker_for_language.cache_clear()
            rows = spellcheck.unknown_words("typo other", language="en")
        self.assertEqual(rows[0]["suggestions"], ["typed"])
        self.assertEqual(rows[1]["suggestions"], ["fixed", "typed"])

    def test_suggestions_for_word_tolerates_none_candidates(self) -> None:
        with patch.object(spellcheck, "_english_spell_engine", return_value=_FakeSymSpellEngine("en")):
            spellcheck._english_spell_engine.cache_clear()
            spellcheck._spellchecker_for_language.cache_clear()
            self.assertEqual(spellcheck.suggestions_for_word("typo", language="en"), ["typed"])

    def test_spellcheck_available_accepts_either_backend(self) -> None:
        with patch.object(spellcheck, "SymSpell", object()), patch.object(spellcheck, "Hunspell", None):
            self.assertTrue(spellcheck.spellcheck_available())
        with patch.object(spellcheck, "SymSpell", None), patch.object(spellcheck, "Hunspell", object()):
            self.assertTrue(spellcheck.spellcheck_available())

    def test_english_prefers_symspell_accelerator(self) -> None:
        seen = []

        def _english():
            seen.append("english")
            return _FakeSymSpellEngine("en")

        with patch.object(spellcheck, "_english_spell_engine", side_effect=_english), patch.object(
            spellcheck, "_HunspellEngine", side_effect=RuntimeError("unused")
        ):
            spellcheck._english_spell_engine.cache_clear()
            spellcheck._spellchecker_for_language.cache_clear()
            engine = spellcheck._spellchecker_for_language("en")
        self.assertEqual(seen, ["english"])
        self.assertIsInstance(engine, _FakeSymSpellEngine)

    def test_non_english_uses_hunspell(self) -> None:
        seen = []

        def _factory(language: str = "en"):
            seen.append(language)
            return _FakeHunspellEngine(language)

        with patch.object(spellcheck, "_HunspellEngine", side_effect=_factory), patch.object(
            spellcheck, "_english_spell_engine", return_value=_FakeSymSpellEngine("en")
        ):
            spellcheck._english_spell_engine.cache_clear()
            spellcheck._spellchecker_for_language.cache_clear()
            engine = spellcheck._spellchecker_for_language("es")
        self.assertIsNotNone(engine)
        self.assertEqual(seen, ["es"])

    def test_normalize_language_prefers_bundled_dictionary_names(self) -> None:
        self.assertEqual(spellcheck._normalize_language("es"), "es")
        self.assertEqual(spellcheck._normalize_language("en-US"), "en")
        self.assertEqual(spellcheck._normalize_language("en_GB"), "en-GB")
        self.assertEqual(spellcheck._normalize_language("pt-PT"), "pt-PT")
        self.assertEqual(spellcheck._normalize_language("ja"), "ja")

    def test_find_hunspell_data_dir_supports_bundled_dictionary_layout(self) -> None:
        root = TEST_ROOT / "bundled_case"
        bundled = root / "dictionaries" / "es"
        bundled.mkdir(parents=True, exist_ok=True)
        (bundled / "index.aff").write_text("SET UTF-8\n", encoding="utf-8")
        (bundled / "index.dic").write_text("1\nhola\n", encoding="utf-8")
        with patch.object(spellcheck, "resolve_asset_path", return_value=root / "dictionaries"), patch.object(
            spellcheck, "get_spellcheck_dictionaries_dir_path", return_value=root / "custom"
        ):
            found = spellcheck._find_hunspell_data_dir("es")
        self.assertEqual(found, bundled)

    def test_dictionary_file_path_supports_index_files(self) -> None:
        directory = TEST_ROOT / "index_case"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "index.dic").write_text("1\nbonjour\n", encoding="utf-8")
        words = spellcheck._load_dictionary_wordlist("fr", directory)
        self.assertEqual(words, ["bonjour"])

    def test_suggestions_preserve_capitalization_patterns(self) -> None:
        with patch.object(spellcheck, "_english_spell_engine", return_value=_FakeSymSpellEngine("en")):
            spellcheck._english_spell_engine.cache_clear()
            spellcheck._spellchecker_for_language.cache_clear()
            self.assertEqual(spellcheck.suggestions_for_word("WAHT", language="en"), ["FIXED", "TYPED"])
            spellcheck._spellchecker_for_language.cache_clear()
            self.assertEqual(spellcheck.suggestions_for_word("tset", language="en"), ["fixed", "typed"])
            spellcheck._spellchecker_for_language.cache_clear()
            self.assertEqual(spellcheck.suggestions_for_word("Tset", language="en"), ["Fixed", "Typed"])


if __name__ == "__main__":
    unittest.main()
