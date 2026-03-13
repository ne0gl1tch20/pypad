import sys
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypad.ui.editor.editor_widget import EditorWidget


class EditorWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_replace_selection_at_end_of_document_replaces_instead_of_appending(self) -> None:
        editor = EditorWidget()
        editor.set_text("helalo")
        editor.set_selection_by_index(0, len("helalo"))
        editor.replace_selection("hello")
        self.assertEqual(editor.get_text(), "hello")


if __name__ == "__main__":
    unittest.main()
