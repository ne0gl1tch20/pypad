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


class StartupLoggingResolutionTests(unittest.TestCase):
    def test_warning_level_is_resolved_for_startup_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text(json.dumps({"logging_level": "WARNING"}), encoding="utf-8")
            self.assertEqual(resolve_persisted_log_level(path, default="INFO"), "WARNING")


if __name__ == "__main__":
    unittest.main()
