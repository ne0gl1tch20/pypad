import sys
import shutil
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypad.ui.security.note_crypto import decrypt_text, encrypt_text
from pypad.ui.security.security_controller import SecurityController
from pypad.ui.security.safe_save import build_effective_save_policy, safe_write_text


class _TextEditStub:
    def __init__(self, text: str) -> None:
        self._text = text

    def get_text(self) -> str:
        return self._text


class _TabStub:
    def __init__(self, current_file: str, text: str = "secret") -> None:
        self.current_file = current_file
        self.text_edit = _TextEditStub(text)
        self.encryption_enabled = True
        self.encryption_password = "pw123"
        self.trust_state = "trusted"


class _WindowStub:
    def __init__(self) -> None:
        self.settings = {
            "security_profile_id": "balanced",
            "safe_save_backup_on_overwrite": True,
            "safe_save_atomic_replace": True,
        }

    def _resolved_security_policy(self):
        class _Policy:
            save_policy = "safe_default"
            profile_id = "balanced"
        return _Policy()

    def _is_tab_untrusted(self, _tab) -> bool:
        return False


class EncryptedNotePolicyTests(unittest.TestCase):
    def test_encrypted_notes_can_use_plain_file_extension(self) -> None:
        controller = SecurityController(_WindowStub())
        tab = _TabStub("C:/tmp/demo.txt")
        payload = controller.build_payload_for_save(tab)
        self.assertIn("PYPAD_ENCNOTE_BEGIN", payload)

    def test_encrypted_payload_uses_pypad_armored_layout(self) -> None:
        controller = SecurityController(_WindowStub())
        tab = _TabStub("C:/tmp/demo.encnote", text="secret body")
        payload = controller.build_payload_for_save(tab)
        self.assertIn("PYPAD_ENCNOTE_BEGIN", payload)
        self.assertIn("This file has been encrypted by PyPad.", payload)
        self.assertIn("version:2", payload)
        self.assertIn("aead:aes-256-gcm", payload)
        self.assertIn("encrypted_contents:", payload)
        self.assertIn("encrypted_password:", payload)
        self.assertIn("encrypted_marker:pypad", payload)
        self.assertEqual(decrypt_text(payload or "", "pw123"), "secret body")

    def test_encrypt_text_roundtrip_uses_current_aead_format(self) -> None:
        payload = encrypt_text("hello world", "pw123")
        self.assertIn("version:2", payload)
        self.assertIn("aead:aes-256-gcm", payload)
        self.assertEqual(decrypt_text(payload, "pw123"), "hello world")

    def test_encrypted_safe_save_does_not_create_bak(self) -> None:
        window = _WindowStub()
        tab = _TabStub("C:/tmp/demo.txt")
        policy = build_effective_save_policy(window, tab)
        self.assertFalse(policy["backup_on_overwrite"])
        tmp = ROOT / "tests_tmp" / f"encsave_{time.time_ns()}"
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            target = tmp / "demo.txt"
            target.write_text("old", encoding="utf-8")
            safe_write_text(str(target), "new", "utf-8", atomic_replace=True, backup_on_overwrite=bool(policy["backup_on_overwrite"]))
            self.assertEqual(target.read_text(encoding="utf-8"), "new")
            self.assertFalse((tmp / "demo.txt.bak").exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
