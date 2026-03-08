from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypad.services.updater_helpers import is_newer_version, parse_update_feed
from pypad.ui.editor.quick_open_dialog import score_quick_open_match
from pypad.ui.system.autosave import AutoSaveStore


class ProductivityHardeningTests(unittest.TestCase):
    def test_release_metadata_consistency(self) -> None:
        version_text = (ROOT / "assets" / "version.txt").read_text(encoding="utf-8").strip()
        xml_text = (ROOT / "update.xml").read_text(encoding="utf-8")
        info = parse_update_feed(xml_text)
        self.assertIsNotNone(info)
        assert info is not None
        self.assertIn(version_text, info.title)
        self.assertTrue(info.version.strip())
        self.assertTrue(info.pub_date.strip())
        self.assertTrue(info.download_url.strip())

    def test_version_comparison_prefers_stable_over_prerelease(self) -> None:
        self.assertTrue(is_newer_version("1.8.0", "1.8.0-rc1"))
        self.assertFalse(is_newer_version("1.8.0-beta1", "1.8.0"))
        self.assertTrue(is_newer_version("1.8.1", "1.8.0"))

    def test_quick_open_scoring_prefers_basename_and_path_segment(self) -> None:
        exact_base = score_quick_open_match("main.py", "src/app/main.py")
        path_contains = score_quick_open_match("app/main", "src/app/main.py")
        fuzzy = score_quick_open_match("mnpy", "src/app/main.py")
        self.assertGreater(exact_base, path_contains)
        self.assertGreater(path_contains, fuzzy)

    def test_autosave_store_survives_index_write_and_reload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            store = AutoSaveStore(base)
            autosave_id = "abc123"
            autosave_file = store.autosave_file(autosave_id)
            autosave_file.write_text("hello", encoding="utf-8")
            store.upsert(autosave_id, str(autosave_file), "", "Untitled")
            store.save()

            reloaded = AutoSaveStore(base)
            reloaded.load()
            self.assertIn(autosave_id, reloaded.entries)


if __name__ == "__main__":
    unittest.main()
