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


class _RecoveryHarness(MiscMixin):
    pass


class _FakeTab:
    def __init__(self, *, typing_test: bool) -> None:
        self.typing_test_mode_enabled = typing_test


class TypingSpeedTestRecoveryTests(unittest.TestCase):
    def test_typing_test_tabs_are_excluded_from_recovery(self) -> None:
        harness = _RecoveryHarness()
        self.assertTrue(harness._exclude_tab_from_recovery(_FakeTab(typing_test=True)))
        self.assertFalse(harness._exclude_tab_from_recovery(_FakeTab(typing_test=False)))


if __name__ == "__main__":
    unittest.main()
