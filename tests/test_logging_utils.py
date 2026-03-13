import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypad.logging_utils import resolve_persisted_log_level


class LoggingUtilsTests(unittest.TestCase):
    def test_resolve_persisted_log_level_reads_valid_setting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text(json.dumps({"logging_level": "debug"}), encoding="utf-8")
            self.assertEqual(resolve_persisted_log_level(path), "DEBUG")

    def test_resolve_persisted_log_level_falls_back_for_missing_or_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.json"
            self.assertEqual(resolve_persisted_log_level(missing, default="WARNING"), "WARNING")
            broken = Path(tmp) / "broken.json"
            broken.write_text("{", encoding="utf-8")
            self.assertEqual(resolve_persisted_log_level(broken, default="ERROR"), "ERROR")


if __name__ == "__main__":
    unittest.main()
