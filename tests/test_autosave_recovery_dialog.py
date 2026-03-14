import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from pypad.ui.system.autosave import AutoSaveEntry, AutoSaveRecoveryDialog


class AutoSaveRecoveryDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_dialog_stays_owned_by_parent_even_if_parent_hidden(self) -> None:
        owner = QWidget()
        owner.hide()
        dialog = AutoSaveRecoveryDialog(
            owner,
            [
                AutoSaveEntry(
                    autosave_id="1",
                    autosave_path="missing.txt",
                    original_path="",
                    title="Untitled",
                    saved_at="2026-03-14 19:37:15",
                )
            ],
        )
        self.assertIs(dialog.parentWidget(), owner)
        self.assertEqual(dialog.windowModality(), Qt.WindowModal)


if __name__ == "__main__":
    unittest.main()
