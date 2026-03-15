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

from pypad.ui.security.note_trust import classify_note_trust
from pypad.ui.security.security_profile import resolve_security_policy


class NoteTrustFlowTests(unittest.TestCase):
    def test_external_file_defaults_to_untrusted(self) -> None:
        policy = resolve_security_policy({"security_profile_id": "balanced"})
        decision = classify_note_trust(
            path="C:/tmp/example.txt",
            open_origin="file_dialog",
            workspace_root="",
            trust_known_workspace_files=True,
            persisted_record=None,
            policy=policy,
        )
        self.assertEqual(decision.state, "untrusted")

    def test_workspace_file_can_be_trusted(self) -> None:
        tmp = ROOT / "tests_tmp" / f"note_trust_{time.time_ns()}"
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            path = tmp / "example.txt"
            path.write_text("x", encoding="utf-8")
            policy = resolve_security_policy({"security_profile_id": "balanced"})
            decision = classify_note_trust(
                path=str(path),
                open_origin="workspace",
                workspace_root=str(tmp),
                trust_known_workspace_files=True,
                persisted_record=None,
                policy=policy,
            )
            self.assertEqual(decision.state, "trusted")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_startup_arg_defaults_to_untrusted(self) -> None:
        policy = resolve_security_policy({"security_profile_id": "balanced"})
        decision = classify_note_trust(
            path="C:/tmp/example.txt",
            open_origin="startup_arg",
            workspace_root="",
            trust_known_workspace_files=True,
            persisted_record=None,
            policy=policy,
        )
        self.assertEqual(decision.state, "untrusted")


if __name__ == "__main__":
    unittest.main()
