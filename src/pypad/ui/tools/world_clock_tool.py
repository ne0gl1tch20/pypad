"""World clock dialog."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QListWidget, QMessageBox, QPushButton

from .base_dialog import ToolDialogBase

COMMON_ZONES = [
    "UTC",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "Europe/London",
    "Europe/Paris",
    "Asia/Tokyo",
    "Asia/Seoul",
    "Australia/Sydney",
]

FALLBACK_ZONES = {
    "UTC": timezone.utc,
    "America/New_York": timezone(timedelta(hours=-5), "UTC-05"),
    "America/Chicago": timezone(timedelta(hours=-6), "UTC-06"),
    "America/Denver": timezone(timedelta(hours=-7), "UTC-07"),
    "America/Los_Angeles": timezone(timedelta(hours=-8), "UTC-08"),
    "Europe/London": timezone(timedelta(hours=0), "UTC+00"),
    "Europe/Paris": timezone(timedelta(hours=1), "UTC+01"),
    "Asia/Tokyo": timezone(timedelta(hours=9), "UTC+09"),
    "Asia/Seoul": timezone(timedelta(hours=9), "UTC+09"),
    "Australia/Sydney": timezone(timedelta(hours=10), "UTC+10"),
}


def _resolve_zone(zone_name: str):
    """Resolve a time zone with a fixed-offset fallback when tzdata is unavailable."""
    try:
        return ZoneInfo(zone_name)
    except ZoneInfoNotFoundError:
        fallback = FALLBACK_ZONES.get(zone_name)
        if fallback is not None:
            return fallback
        raise


def format_world_clock_rows(zones: list[str], now: datetime | None = None) -> list[str]:
    """Format world clock rows for the supplied time zones."""
    now = now or datetime.now()
    rows: list[str] = []
    for zone_name in zones:
        zone = _resolve_zone(zone_name)
        rows.append(f"{zone_name} | {now.astimezone(zone).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    return rows


class WorldClockToolDialog(ToolDialogBase):
    """Show multiple local time zones without network access."""

    def __init__(self, parent) -> None:
        super().__init__(
            parent,
            tool_id="world_clock",
            title="World Clock",
            help_text="Save a few time zones locally and keep them updated live. Copy the current list or insert it into the active note.",
        )
        group = QGroupBox("Saved Zones", self)
        form = QFormLayout(group)
        self.zone_combo = QComboBox(group)
        self.zone_combo.setEditable(True)
        self.zone_combo.addItems(COMMON_ZONES)
        self.add_btn = QPushButton("Add Zone", group)
        self.remove_btn = QPushButton("Remove Selected", group)
        self.list_widget = QListWidget(group)
        self.list_widget.setAccessibleName("World clock zones list")
        self.add_btn.clicked.connect(self.add_zone)
        self.remove_btn.clicked.connect(self.remove_selected_zone)
        form.addRow("Time zone:", self.zone_combo)
        form.addRow("", self.add_btn)
        form.addRow("", self.remove_btn)
        form.addRow(self.list_widget)
        self.add_section(group)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh_output)
        self.load_persisted_state()
        self._timer.start()
        self.refresh_output()

    def _saved_zones(self) -> list[str]:
        return [self.list_widget.item(row).text() for row in range(self.list_widget.count())]

    def add_zone(self) -> None:
        zone_name = self.zone_combo.currentText().strip()
        if not zone_name:
            return
        try:
            _resolve_zone(zone_name)
        except Exception:
            QMessageBox.warning(self, self.windowTitle(), f"Unknown time zone: {zone_name}")
            return
        if zone_name not in self._saved_zones():
            self.list_widget.addItem(zone_name)
        self.refresh_output()

    def remove_selected_zone(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            return
        self.list_widget.takeItem(self.list_widget.row(item))
        self.refresh_output()

    def refresh_output(self) -> None:
        zones = self._saved_zones() or ["UTC"]
        self.output.setPlainText("\n".join(format_world_clock_rows(zones)))

    def state(self) -> dict[str, Any]:
        zones = self._saved_zones()
        if isinstance(getattr(self.window, "settings", None), dict):
            self.window.settings["world_clock_zones"] = list(zones)
        return {"zones": zones}

    def restore_state(self, state: dict[str, Any]) -> None:
        zones = state.get("zones")
        if not isinstance(zones, list) or not zones:
            settings_zones = getattr(self.window, "settings", {}).get("world_clock_zones", [])
            zones = settings_zones if isinstance(settings_zones, list) and settings_zones else ["UTC"]
        for zone_name in zones:
            text = str(zone_name).strip()
            if text:
                self.list_widget.addItem(text)
