import os
import sys
import shutil
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypad.ui.security.safe_save import safe_write_text


class SafeSaveTests(unittest.TestCase):
    def test_safe_write_text_atomic_and_backup(self) -> None:
        tmp = ROOT / "tests_tmp" / f"safe_save_{time.time_ns()}"
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            target = tmp / "demo.txt"
            target.write_text("old", encoding="utf-8")
            safe_write_text(str(target), "new", "utf-8", atomic_replace=True, backup_on_overwrite=True)
            self.assertEqual(target.read_text(encoding="utf-8"), "new")
            self.assertEqual((target.with_suffix(".txt.bak")).read_text(encoding="utf-8"), "old")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
