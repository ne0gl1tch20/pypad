"""Password generator dialog."""

from __future__ import annotations

import secrets
import string
from typing import Any

from PySide6.QtWidgets import QCheckBox, QFormLayout, QGroupBox, QLabel, QMessageBox, QPushButton, QSpinBox

from .base_dialog import ToolDialogBase

AMBIGUOUS_CHARS = set("0O1lI|")


def build_password(
    *,
    length: int,
    use_upper: bool,
    use_lower: bool,
    use_digits: bool,
    use_symbols: bool,
    exclude_ambiguous: bool,
) -> str:
    """Build a random password that satisfies the requested policy."""
    pools: list[str] = []
    if use_upper:
        pools.append(string.ascii_uppercase)
    if use_lower:
        pools.append(string.ascii_lowercase)
    if use_digits:
        pools.append(string.digits)
    if use_symbols:
        pools.append("!@#$%^&*()-_=+[]{}:,.?")
    if not pools:
        raise ValueError("Choose at least one character group.")
    alphabet = "".join(pools)
    if exclude_ambiguous:
        alphabet = "".join(ch for ch in alphabet if ch not in AMBIGUOUS_CHARS)
        pools = ["".join(ch for ch in pool if ch not in AMBIGUOUS_CHARS) for pool in pools]
        pools = [pool for pool in pools if pool]
        if not pools:
            raise ValueError("The selected options left no usable characters.")
    required = [secrets.choice(pool) for pool in pools]
    remaining = [secrets.choice(alphabet) for _ in range(max(0, length - len(required)))]
    chars = required + remaining
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars[:length])


def password_strength(password: str) -> str:
    """Return a compact password-strength label."""
    score = 0
    if len(password) >= 12:
        score += 2
    elif len(password) >= 8:
        score += 1
    if any(ch.islower() for ch in password):
        score += 1
    if any(ch.isupper() for ch in password):
        score += 1
    if any(ch.isdigit() for ch in password):
        score += 1
    if any(not ch.isalnum() for ch in password):
        score += 1
    if score <= 2:
        return "Weak"
    if score <= 4:
        return "Moderate"
    return "Strong"


class PasswordToolDialog(ToolDialogBase):
    """Generate insertable or copyable passwords."""

    def __init__(self, parent) -> None:
        super().__init__(
            parent,
            tool_id="password_generator",
            title="Password Generator",
            help_text=(
                "Generate a local password using selected character groups. Passwords are never "
                "sent anywhere; copy or insert them only when you intend to."
            ),
        )
        group = QGroupBox("Generator", self)
        form = QFormLayout(group)
        self.length_spin = QSpinBox(group)
        self.length_spin.setRange(4, 128)
        self.length_spin.setValue(20)
        self.upper_check = QCheckBox("Uppercase", group)
        self.upper_check.setChecked(True)
        self.lower_check = QCheckBox("Lowercase", group)
        self.lower_check.setChecked(True)
        self.digits_check = QCheckBox("Digits", group)
        self.digits_check.setChecked(True)
        self.symbols_check = QCheckBox("Symbols", group)
        self.symbols_check.setChecked(True)
        self.exclude_ambiguous_check = QCheckBox("Exclude ambiguous characters", group)
        self.exclude_ambiguous_check.setChecked(True)
        self.generate_btn = QPushButton("Generate", group)
        self.generate_btn.clicked.connect(self.generate_output)
        self.strength_label = QLabel("-", group)
        form.addRow("Length:", self.length_spin)
        form.addRow("", self.upper_check)
        form.addRow("", self.lower_check)
        form.addRow("", self.digits_check)
        form.addRow("", self.symbols_check)
        form.addRow("", self.exclude_ambiguous_check)
        form.addRow("Strength:", self.strength_label)
        form.addRow("", self.generate_btn)
        self.add_section(group)
        self.load_persisted_state()

    def generate_output(self) -> None:
        try:
            value = build_password(
                length=int(self.length_spin.value()),
                use_upper=self.upper_check.isChecked(),
                use_lower=self.lower_check.isChecked(),
                use_digits=self.digits_check.isChecked(),
                use_symbols=self.symbols_check.isChecked(),
                exclude_ambiguous=self.exclude_ambiguous_check.isChecked(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, self.windowTitle(), str(exc))
            return
        self.output.setPlainText(value)
        self.strength_label.setText(password_strength(value))

    def state(self) -> dict[str, Any]:
        return {
            "length": self.length_spin.value(),
            "upper": self.upper_check.isChecked(),
            "lower": self.lower_check.isChecked(),
            "digits": self.digits_check.isChecked(),
            "symbols": self.symbols_check.isChecked(),
            "exclude_ambiguous": self.exclude_ambiguous_check.isChecked(),
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.length_spin.setValue(max(4, min(128, int(state.get("length", 20)))))
        self.upper_check.setChecked(bool(state.get("upper", True)))
        self.lower_check.setChecked(bool(state.get("lower", True)))
        self.digits_check.setChecked(bool(state.get("digits", True)))
        self.symbols_check.setChecked(bool(state.get("symbols", True)))
        self.exclude_ambiguous_check.setChecked(bool(state.get("exclude_ambiguous", True)))
