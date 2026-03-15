from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypad.app_settings.coercion import migrate_settings
from pypad.app_settings.defaults import build_default_settings
from pypad.ui.editor.offline_writing_tools import analyze_writing, estimate_ai_likelihood, humanize_text, paraphrase_text


class OfflineWritingToolsTests(unittest.TestCase):
    def test_defaults_include_writing_tool_settings(self) -> None:
        settings = build_default_settings(default_style="Windows", font_family="Segoe UI", font_size=11)
        self.assertIn("writing_tools_ai_detector_sensitivity", settings)
        self.assertTrue(settings["writing_tools_detect_repeated_words"])

    def test_migrate_coerces_writing_tool_settings(self) -> None:
        migrated = migrate_settings(
            {
                "settings_schema_version": 2,
                "writing_tools_use_language_tool": "false",
                "writing_tools_detect_repeated_words": "yes",
                "writing_tools_ai_detector_sensitivity": "9",
                "writing_tools_ai_sentence_threshold": "2",
                "writing_tools_ai_unique_ratio_threshold": "4",
            }
        )
        self.assertFalse(migrated["writing_tools_use_language_tool"])
        self.assertTrue(migrated["writing_tools_detect_repeated_words"])
        self.assertEqual(migrated["writing_tools_ai_detector_sensitivity"], 1.5)
        self.assertEqual(migrated["writing_tools_ai_sentence_threshold"], 8)
        self.assertEqual(migrated["writing_tools_ai_unique_ratio_threshold"], 0.9)

    def test_analyze_writing_flags_repeated_words(self) -> None:
        result = analyze_writing("this is is a test. this sentence starts badly.")
        messages = [row.message for row in result.suggestions]
        self.assertTrue(any("Repeated word" in row for row in messages))
        self.assertTrue(any("capitalization" in row.lower() for row in messages))

    def test_paraphrase_and_humanize_transform_text(self) -> None:
        self.assertIn("to", paraphrase_text("In order to improve, we use data."))
        humanized = humanize_text("However, individuals utilize numerous tools.")
        self.assertIn("people", humanized.lower())
        self.assertIn("use", humanized.lower())

    def test_ai_detector_returns_explanatory_signals(self) -> None:
        score, signals = estimate_ai_likelihood(
            "Furthermore, this system provides additional value. "
            "Moreover, it offers consistency. Therefore, overall, the result is predictable."
        )
        self.assertGreaterEqual(score, 1)
        self.assertTrue(signals)


if __name__ == "__main__":
    unittest.main()
