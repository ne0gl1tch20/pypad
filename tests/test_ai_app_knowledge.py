import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypad.ai_app_knowledge import get_default_ai_app_knowledge, resolve_ai_app_knowledge


class AIKnowledgeTests(unittest.TestCase):
    def test_user_knowledge_is_appended_not_replacing_base(self) -> None:
        resolved = resolve_ai_app_knowledge("Custom user note", include_ui_appendix=False)
        self.assertIn("built-in assistant", resolved)
        self.assertIn("[PYPAD_USER_KNOWLEDGE_OVERRIDE]", resolved)
        self.assertIn("Custom user note", resolved)

    def test_compact_mode_excludes_generated_appendix(self) -> None:
        compact = get_default_ai_app_knowledge(include_ui_appendix=False)
        full = get_default_ai_app_knowledge(include_ui_appendix=True)
        self.assertNotIn("Generated appendix", compact)
        self.assertIn("Generated appendix", full)

    def test_user_knowledge_limit_truncates_large_override(self) -> None:
        resolved = resolve_ai_app_knowledge("x" * 500, include_ui_appendix=False, user_knowledge_char_limit=200)
        self.assertIn("truncated locally", resolved)


if __name__ == "__main__":
    unittest.main()
