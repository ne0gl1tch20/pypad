from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypad.ui.editor.language_tool_installer import parse_package_download_info


class LanguageToolInstallerTests(unittest.TestCase):
    def test_parse_package_download_info_picks_latest_2x_release(self) -> None:
        payload = {
            "releases": {
                "3.0.0": [{"filename": "skip.whl", "size": 99, "packagetype": "bdist_wheel", "url": "https://example/skip"}],
                "2.8.1": [{"filename": "a.tar.gz", "size": 100, "packagetype": "sdist", "url": "https://example/a"}],
                "2.9.0": [{"filename": "b-py3-none-any.whl", "size": 250, "packagetype": "bdist_wheel", "url": "https://example/b"}],
            }
        }
        info = parse_package_download_info(payload)
        self.assertEqual(info.version, "2.9.0")
        self.assertEqual(info.size_bytes, 250)
        self.assertEqual(info.filename, "b-py3-none-any.whl")


if __name__ == "__main__":
    unittest.main()
