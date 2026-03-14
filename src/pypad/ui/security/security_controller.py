"""Coordinate privacy, locking, and security-related UI workflows.

This module belongs to the note privacy and security UI layer. It helps explain how `pypad.ui.security` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QInputDialog, QLineEdit

from pypad.ui.security.note_crypto import decrypt_text, encrypt_text, is_encrypted_payload
from pypad.ui.editor.editor_tab import EditorTab


class SecurityController:
    """Security workflow helper for encrypted notes and password-driven file operations."""
    def __init__(self, window) -> None:
        """Bind the security controller to the owning main window."""
        self.window = window

    def prompt_password(self, title: str, label: str) -> str | None:
        """Show a password prompt and return the entered secret when confirmed."""
        password, ok = QInputDialog.getText(self.window, title, label, QLineEdit.Password)
        if not ok or not password:
            return None
        return password

    def load_text_from_path(self, path: str, encoding: str = "utf-8") -> tuple[str, bool, str | None]:
        """Load plain or encrypted note text, prompting for a password when required."""
        with open(path, "r", encoding=encoding, errors="replace") as f:
            raw = f.read()
        encrypted = is_encrypted_payload(raw) or Path(path).suffix.lower() == ".encnote"
        if not encrypted:
            return raw, False, None
        password = self.prompt_password("Encrypted Note", "Enter password:")
        if password is None:
            raise ValueError("Password required")
        plain = decrypt_text(raw, password)
        return plain, True, password

    def build_payload_for_save(self, tab: EditorTab) -> str | None:
        """Build the text payload to save, encrypting it when the tab requires encryption."""
        payload = tab.text_edit.get_text()
        if not tab.encryption_enabled:
            return payload
        password = tab.encryption_password or self.prompt_password("Encrypted Save", "Enter note password:")
        if not password:
            return None
        tab.encryption_password = password
        return encrypt_text(payload, password)

    def enable_note_encryption(self) -> None:
        """Enable encryption on the active tab and capture the initial note password."""
        tab = self.window.active_tab()
        if tab is None:
            return
        if tab.encryption_enabled:
            self.change_note_password()
            return
        password = self.prompt_password("Enable Encryption", "Set note password:")
        if not password:
            return
        tab.encryption_enabled = True
        tab.encryption_password = password
        self.window.update_action_states()
        self.window._refresh_tab_title(tab)

    def disable_note_encryption(self) -> None:
        """Disable encryption on the active tab and clear its stored note password."""
        tab = self.window.active_tab()
        if tab is None:
            return
        tab.encryption_enabled = False
        tab.encryption_password = None
        self.window.update_action_states()
        self.window._refresh_tab_title(tab)

    def change_note_password(self) -> None:
        """Change the password used for the active encrypted note."""
        tab = self.window.active_tab()
        if tab is None or not tab.encryption_enabled:
            return
        password = self.prompt_password("Change Password", "New note password:")
        if not password:
            return
        tab.encryption_password = password
        tab.text_edit.set_modified(True)

