import sys
import unittest
import shutil
import time
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypad.core.crypto_helpers import (
    b64encode_bytes,
    derive_key_pbkdf2,
    hmac_counter_keystream,
    hmac_digest,
    xor_bytes,
)
from pypad.ui.security.note_crypto import decrypt_text
from pypad.ui.security.security_controller import SecurityController


class _TextEditStub:
    def __init__(self, text: str) -> None:
        self._text = text
        self.modified = False

    def get_text(self) -> str:
        return self._text

    def set_modified(self, value: bool) -> None:
        self.modified = value

    def is_modified(self) -> bool:
        return self.modified


class _TabStub:
    def __init__(self, text: str, current_file: str | None = None) -> None:
        self.text_edit = _TextEditStub(text)
        self.encryption_enabled = False
        self.encryption_password = None
        self.current_file = current_file


class _WindowStub:
    def __init__(self) -> None:
        self._tab = _TabStub("hello")
        self.saved = False
        self.saved_as = False
        self.status_messages: list[str] = []

    def active_tab(self):
        return self._tab

    def update_action_states(self) -> None:
        return

    def _refresh_tab_title(self, _tab) -> None:
        return

    def show_status_message(self, text: str, _timeout: int = 0) -> None:
        self.status_messages.append(text)

    def file_save_tab(self, _tab) -> bool:
        self.saved = True
        return True

    def file_save_as_tab(self, _tab) -> bool:
        self.saved_as = True
        return True


class SecurityControllerTests(unittest.TestCase):
    def _build_legacy_json_payload(self, plain_text: str, password: str) -> str:
        salt = b"0123456789abcdef"
        nonce = b"abcdef0123456789"
        key = derive_key_pbkdf2(password, salt, rounds=200_000, dklen=32)
        plain = plain_text.encode("utf-8")
        stream = hmac_counter_keystream(key, nonce, len(plain))
        cipher = xor_bytes(plain, stream)
        mac_key = hmac_digest(key, b"mac")
        tag = hmac_digest(mac_key, nonce + cipher)
        payload = {
            "v": 1,
            "s": b64encode_bytes(salt),
            "n": b64encode_bytes(nonce),
            "c": b64encode_bytes(cipher),
            "t": b64encode_bytes(tag),
        }
        return "ENCNOTE1\n" + json.dumps(payload, separators=(",", ":"))

    def test_build_payload_plain(self) -> None:
        controller = SecurityController(_WindowStub())
        tab = _TabStub("hello")
        self.assertEqual(controller.build_payload_for_save(tab), "hello")

    def test_build_payload_encrypted_roundtrip(self) -> None:
        controller = SecurityController(_WindowStub())
        tab = _TabStub("secret body")
        tab.encryption_enabled = True
        tab.encryption_password = "pw123"
        payload = controller.build_payload_for_save(tab)
        self.assertIsInstance(payload, str)
        self.assertEqual(decrypt_text(payload or "", "pw123"), "secret body")

    def test_load_text_from_encrypted_path(self) -> None:
        controller = SecurityController(_WindowStub())
        controller.prompt_password = lambda _title, _label: "pw123"
        tab = _TabStub("from file")
        tab.encryption_enabled = True
        tab.encryption_password = "pw123"
        payload = controller.build_payload_for_save(tab)
        self.assertIsNotNone(payload)
        tmp_root = ROOT / "tests_tmp"
        tmp = tmp_root / f"security_{time.time_ns()}"
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            path = tmp / "note.encnote"
            path.write_text(payload or "", encoding="utf-8")
            text, encrypted, password = controller.load_text_from_path(str(path))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(text, "from file")
        self.assertTrue(encrypted)
        self.assertEqual(password, "pw123")

    def test_decrypt_text_accepts_legacy_json_payload(self) -> None:
        payload = self._build_legacy_json_payload("legacy body", "pw123")
        self.assertEqual(decrypt_text(payload, "pw123"), "legacy body")

    def test_enable_encryption_marks_dirty_and_uses_save_as_for_plain_file(self) -> None:
        window = _WindowStub()
        window._tab = _TabStub("secret", current_file="C:/tmp/demo.txt")
        controller = SecurityController(window)
        controller.prompt_password = lambda _title, _label: "pw123"
        controller.enable_note_encryption()
        self.assertTrue(window._tab.encryption_enabled)
        self.assertTrue(window.saved)
        self.assertFalse(window.saved_as)

    def test_enable_encryption_rolls_back_on_cancelled_save(self) -> None:
        window = _WindowStub()
        window._tab = _TabStub("secret", current_file="C:/tmp/demo.txt")
        window.file_save_tab = lambda _tab: False
        controller = SecurityController(window)
        controller.prompt_password = lambda _title, _label: "pw123"
        controller.enable_note_encryption()
        self.assertFalse(window._tab.encryption_enabled)
        self.assertIn("Encryption canceled", " ".join(window.status_messages))

    def test_disable_encryption_rewrites_current_file_via_save(self) -> None:
        window = _WindowStub()
        window._tab = _TabStub("secret", current_file="C:/tmp/demo.txt")
        window._tab.encryption_enabled = True
        window._tab.encryption_password = "pw123"
        controller = SecurityController(window)
        controller.disable_note_encryption()
        self.assertFalse(window._tab.encryption_enabled)
        self.assertTrue(window.saved)
        self.assertIn("Encryption disabled", " ".join(window.status_messages))

    def test_disable_encryption_rolls_back_on_failed_save(self) -> None:
        window = _WindowStub()
        window._tab = _TabStub("secret", current_file="C:/tmp/demo.txt")
        window._tab.encryption_enabled = True
        window._tab.encryption_password = "pw123"
        window.file_save_tab = lambda _tab: False
        controller = SecurityController(window)
        controller.disable_note_encryption()
        self.assertTrue(window._tab.encryption_enabled)
        self.assertEqual(window._tab.encryption_password, "pw123")
        self.assertIn("file remains encrypted", " ".join(window.status_messages))


if __name__ == "__main__":
    unittest.main()
