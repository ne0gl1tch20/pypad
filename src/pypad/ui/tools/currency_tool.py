"""Offline-first currency converter with optional live rate refresh."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QWidget,
)

from .base_dialog import ToolDialogBase
from .finance_tool import extract_numeric_values

try:
    from forex_python.converter import CurrencyRates
except Exception:  # pragma: no cover - optional dependency
    CurrencyRates = None

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


def _normalize_rates(raw: dict[str, Any]) -> dict[str, float]:
    rates: dict[str, float] = {}
    for key, value in raw.items():
        try:
            rates[str(key).upper()] = float(value)
        except Exception:
            continue
    if "USD" not in rates:
        rates["USD"] = 1.0
    return rates


class _CurrencyRefreshWorker(QObject):
    """Refresh live exchange rates away from the UI thread."""

    finished = Signal(dict)
    failed = Signal(str)

    def run(self) -> None:
        if CurrencyRates is None:
            self.failed.emit("Live refresh is unavailable because the forex-python package is not installed.")
            return
        try:
            rates = CurrencyRates(force_decimal=False).get_rates("USD")
        except Exception as exc:
            self.failed.emit(str(exc) or "Could not fetch live rates.")
            return
        normalized = _normalize_rates(rates if isinstance(rates, dict) else {})
        if len(normalized) <= 1:
            self.failed.emit("Live refresh returned no usable rates.")
            return
        self.finished.emit({code: float(value) for code, value in normalized.items()})


class CurrencyToolDialog(ToolDialogBase):
    """Convert currencies using cached or live-refreshed rates."""

    def __init__(self, parent, initial_text: str = "") -> None:
        super().__init__(
            parent,
            tool_id="currency_converter",
            title="Currency Converter",
            help_text=(
                "Convert currencies using bundled defaults, your saved cache, or a manual live refresh. "
                "Live refresh is optional and failures fall back to cached or bundled rates."
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
        self.refresh_btn = QPushButton("Refresh Live Rates", group)
        self.edit_cache_btn = QPushButton("Edit Cached Rates", group)
        self.rates, self._rate_source = self._load_rates()
        for combo in (self.from_combo, self.to_combo):
            combo.addItems(sorted(self.rates))
        if "EUR" in self.rates:
            self.to_combo.setCurrentText("EUR")
        self.convert_btn.clicked.connect(self.convert)
        self.refresh_btn.clicked.connect(self.refresh_live_rates)
        self.edit_cache_btn.clicked.connect(self.edit_cache)
        form.addRow("Amount:", self.amount_edit)
        form.addRow("From:", self.from_combo)
        form.addRow("To:", self.to_combo)
        form.addRow("Rates:", self.status_edit)
        button_row = QWidget(group)
        button_layout = QHBoxLayout(button_row)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(self.convert_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.edit_cache_btn)
        form.addRow("", button_row)
        self.add_section(group)
        self._refresh_worker_thread: QThread | None = None
        self._refresh_worker: _CurrencyRefreshWorker | None = None
        self._refresh_status()
        self.load_persisted_state()
        values = extract_numeric_values(initial_text)
        if values:
            self.amount_edit.setText(f"{values[0]:.12g}")

    def _load_rates(self) -> tuple[dict[str, float], str]:
        raw = self.window.settings.get("currency_rates_cache", {})
        if not isinstance(raw, dict) or not raw:
            self.window.settings["currency_rates_cache"] = {k: str(v) for k, v in DEFAULT_RATES.items()}
            self.window.settings["currency_rates_source"] = "bundled"
            return dict(DEFAULT_RATES), "bundled"
        rates = _normalize_rates(raw)
        source = str(self.window.settings.get("currency_rates_source", "cached") or "cached").strip().lower()
        return rates or dict(DEFAULT_RATES), source or "cached"

    def _refresh_status(self) -> None:
        stamp = str(self.window.settings.get("currency_rates_last_sync", "") or "").strip()
        source = str(self.window.settings.get("currency_rates_source", self._rate_source) or self._rate_source).strip().lower()
        if source == "live":
            prefix = "Using live rates"
        elif source == "cached":
            prefix = "Using cached rates"
        else:
            prefix = "Using bundled default rates"
        self.status_edit.setText(f"{prefix} | Last sync: {stamp or 'never'}")

    def _persist_rates(self, rates: dict[str, float], *, source: str, update_timestamp: bool) -> None:
        self.rates = dict(rates)
        self._rate_source = source
        self.window.settings["currency_rates_cache"] = {k: str(v) for k, v in self.rates.items()}
        self.window.settings["currency_rates_source"] = source
        if update_timestamp:
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
        self._persist_rates(updated, source="cached", update_timestamp=True)

    def refresh_live_rates(self) -> None:
        if self._refresh_worker_thread is not None:
            return
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Refreshing...")
        self.output.setPlainText("Refreshing live rates...")
        worker = _CurrencyRefreshWorker()
        thread = QThread(self)
        self._refresh_worker = worker
        self._refresh_worker_thread = thread
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_live_rates_ready)
        worker.finished.connect(thread.quit)
        worker.failed.connect(self._on_live_rates_failed)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_refresh_worker)
        thread.start()

    def _clear_refresh_worker(self) -> None:
        self._refresh_worker = None
        self._refresh_worker_thread = None
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Refresh Live Rates")

    def _on_live_rates_ready(self, rates: dict[str, float]) -> None:
        self._persist_rates(rates, source="live", update_timestamp=True)
        self.output.setPlainText("Live currency rates refreshed successfully.")

    def _on_live_rates_failed(self, message: str) -> None:
        self._refresh_status()
        self.output.setPlainText("Live refresh failed. Existing rates remain available.")
        QMessageBox.information(
            self,
            self.windowTitle(),
            f"Could not refresh live rates.\n\nUsing existing cached/default rates.\n\nDetails:\n{message}",
        )

    def state(self) -> dict[str, Any]:
        return {"amount": self.amount_edit.text(), "from": self.from_combo.currentText(), "to": self.to_combo.currentText()}

    def restore_state(self, state: dict[str, Any]) -> None:
        self.amount_edit.setText(str(state.get("amount", "")))
        for combo, value in ((self.from_combo, state.get("from", "USD")), (self.to_combo, state.get("to", "EUR"))):
            idx = combo.findText(str(value))
            if idx >= 0:
                combo.setCurrentIndex(idx)
