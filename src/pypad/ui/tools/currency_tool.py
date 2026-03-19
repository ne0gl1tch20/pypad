"""Offline-first currency converter with manual cache refresh."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QInputDialog, QLineEdit, QMessageBox, QPushButton

from .base_dialog import ToolDialogBase
from .finance_tool import extract_numeric_values

DEFAULT_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.78,
    "JPY": 155.0,
    "CAD": 1.34,
    "AUD": 1.52,
    "INR": 83.1,
}


def convert_currency(amount: float, from_code: str, to_code: str, rates: dict[str, float]) -> float:
    """Convert via cached base-USD rates."""
    if from_code not in rates or to_code not in rates:
        raise ValueError("Missing rate in local cache.")
    usd_amount = amount / float(rates[from_code])
    return usd_amount * float(rates[to_code])


class CurrencyToolDialog(ToolDialogBase):
    """Convert currencies using a visible local cache."""

    def __init__(self, parent, initial_text: str = "") -> None:
        super().__init__(
            parent,
            tool_id="currency_converter",
            title="Cached Currency Tools",
            help_text=(
                "Convert currencies using a local rate cache. Refresh is manual and offline-safe: "
                "you can edit or paste your own rates, and the dialog shows when the cache was last updated."
            ),
        )
        group = QGroupBox("Converter", self)
        form = QFormLayout(group)
        self.amount_edit = QLineEdit(group)
        self.amount_edit.setPlaceholderText("100")
        self.from_combo = QComboBox(group)
        self.to_combo = QComboBox(group)
        self.status_edit = QLineEdit(group)
        self.status_edit.setReadOnly(True)
        self.convert_btn = QPushButton("Convert", group)
        self.refresh_btn = QPushButton("Edit Cache", group)
        self.rates = self._load_rates()
        for combo in (self.from_combo, self.to_combo):
            combo.addItems(sorted(self.rates))
        if "EUR" in self.rates:
            self.to_combo.setCurrentText("EUR")
        self.convert_btn.clicked.connect(self.convert)
        self.refresh_btn.clicked.connect(self.edit_cache)
        form.addRow("Amount:", self.amount_edit)
        form.addRow("From:", self.from_combo)
        form.addRow("To:", self.to_combo)
        form.addRow("Cache:", self.status_edit)
        form.addRow("", self.convert_btn)
        form.addRow("", self.refresh_btn)
        self.add_section(group)
        self._refresh_status()
        self.load_persisted_state()
        values = extract_numeric_values(initial_text)
        if values:
            self.amount_edit.setText(f"{values[0]:.12g}")

    def _load_rates(self) -> dict[str, float]:
        raw = self.window.settings.get("currency_rates_cache", {})
        if not isinstance(raw, dict) or not raw:
            self.window.settings["currency_rates_cache"] = {k: str(v) for k, v in DEFAULT_RATES.items()}
            return dict(DEFAULT_RATES)
        rates: dict[str, float] = {}
        for key, value in raw.items():
            try:
                rates[str(key).upper()] = float(value)
            except Exception:
                continue
        return rates or dict(DEFAULT_RATES)

    def _refresh_status(self) -> None:
        stamp = str(self.window.settings.get("currency_rates_last_sync", "") or "local defaults")
        self.status_edit.setText(stamp)

    def convert(self) -> None:
        try:
            amount = float(self.amount_edit.text() or 0)
            value = convert_currency(amount, self.from_combo.currentText(), self.to_combo.currentText(), self.rates)
        except Exception as exc:
            QMessageBox.warning(self, self.windowTitle(), str(exc))
            return
        self.output.setPlainText(f"{amount:.4f} {self.from_combo.currentText()} = {value:.4f} {self.to_combo.currentText()}")

    def edit_cache(self) -> None:
        seed = "\n".join(f"{code}={rate}" for code, rate in sorted(self.rates.items()))
        text, ok = QInputDialog.getMultiLineText(self, self.windowTitle(), "Edit cached rates (base USD):", seed)
        if not ok:
            return
        updated: dict[str, float] = {}
        for line in text.splitlines():
            if "=" not in line:
                continue
            code, value = line.split("=", 1)
            try:
                updated[code.strip().upper()] = float(value.strip())
            except Exception:
                continue
        if not updated:
            QMessageBox.warning(self, self.windowTitle(), "No valid rates were provided.")
            return
        self.rates = updated
        self.window.settings["currency_rates_cache"] = {k: str(v) for k, v in updated.items()}
        self.window.settings["currency_rates_last_sync"] = datetime.now().isoformat(timespec="seconds")
        saver = getattr(self.window, "save_settings_to_disk", None)
        if callable(saver):
            saver()
        for combo in (self.from_combo, self.to_combo):
            current = combo.currentText()
            combo.clear()
            combo.addItems(sorted(self.rates))
            combo.setCurrentText(current if current in self.rates else combo.itemText(0))
        self._refresh_status()

    def state(self) -> dict[str, Any]:
        return {"amount": self.amount_edit.text(), "from": self.from_combo.currentText(), "to": self.to_combo.currentText()}

    def restore_state(self, state: dict[str, Any]) -> None:
        self.amount_edit.setText(str(state.get("amount", "")))
        for combo, value in ((self.from_combo, state.get("from", "USD")), (self.to_combo, state.get("to", "EUR"))):
            idx = combo.findText(str(value))
            if idx >= 0:
                combo.setCurrentIndex(idx)
