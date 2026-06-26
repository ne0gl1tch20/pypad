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

    # North America
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Phoenix",
    "America/Toronto",
    "America/Vancouver",
    "America/Mexico_City",

    # South America
    "America/Sao_Paulo",
    "America/Buenos_Aires",
    "America/Lima",
    "America/Bogota",
    "America/Santiago",

    # Europe
    "Europe/London",
    "Europe/Dublin",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Madrid",
    "Europe/Rome",
    "Europe/Amsterdam",
    "Europe/Warsaw",
    "Europe/Athens",
    "Europe/Helsinki",
    "Europe/Istanbul",
    "Europe/Moscow",

    # Africa
    "Africa/Cairo",
    "Africa/Johannesburg",
    "Africa/Lagos",
    "Africa/Nairobi",
    "Africa/Casablanca",

    # Middle East
    "Asia/Dubai",
    "Asia/Riyadh",
    "Asia/Jerusalem",
    "Asia/Tehran",
    "Asia/Qatar",

    # Asia
    "Asia/Karachi",
    "Asia/Kolkata",
    "Asia/Dhaka",
    "Asia/Bangkok",
    "Asia/Jakarta",
    "Asia/Singapore",
    "Asia/Kuala_Lumpur",
    "Asia/Manila",
    "Asia/Hong_Kong",
    "Asia/Shanghai",
    "Asia/Taipei",
    "Asia/Tokyo",
    "Asia/Seoul",

    # Oceania
    "Australia/Perth",
    "Australia/Adelaide",
    "Australia/Darwin",
    "Australia/Brisbane",
    "Australia/Sydney",
    "Pacific/Auckland",
    "Pacific/Fiji",
    "Pacific/Honolulu",
]

FALLBACK_ZONES = {
    "UTC": timezone.utc,

    # North America
    "America/New_York": timezone(timedelta(hours=-5), "UTC-05"),
    "America/Chicago": timezone(timedelta(hours=-6), "UTC-06"),
    "America/Denver": timezone(timedelta(hours=-7), "UTC-07"),
    "America/Los_Angeles": timezone(timedelta(hours=-8), "UTC-08"),
    "America/Phoenix": timezone(timedelta(hours=-7), "UTC-07"),
    "America/Toronto": timezone(timedelta(hours=-5), "UTC-05"),
    "America/Vancouver": timezone(timedelta(hours=-8), "UTC-08"),
    "America/Mexico_City": timezone(timedelta(hours=-6), "UTC-06"),

    # South America
    "America/Sao_Paulo": timezone(timedelta(hours=-3), "UTC-03"),
    "America/Buenos_Aires": timezone(timedelta(hours=-3), "UTC-03"),
    "America/Lima": timezone(timedelta(hours=-5), "UTC-05"),
    "America/Bogota": timezone(timedelta(hours=-5), "UTC-05"),
    "America/Santiago": timezone(timedelta(hours=-4), "UTC-04"),

    # Europe
    "Europe/London": timezone(timedelta(hours=0), "UTC+00"),
    "Europe/Dublin": timezone(timedelta(hours=0), "UTC+00"),
    "Europe/Paris": timezone(timedelta(hours=1), "UTC+01"),
    "Europe/Berlin": timezone(timedelta(hours=1), "UTC+01"),
    "Europe/Madrid": timezone(timedelta(hours=1), "UTC+01"),
    "Europe/Rome": timezone(timedelta(hours=1), "UTC+01"),
    "Europe/Amsterdam": timezone(timedelta(hours=1), "UTC+01"),
    "Europe/Warsaw": timezone(timedelta(hours=1), "UTC+01"),
    "Europe/Athens": timezone(timedelta(hours=2), "UTC+02"),
    "Europe/Helsinki": timezone(timedelta(hours=2), "UTC+02"),
    "Europe/Istanbul": timezone(timedelta(hours=3), "UTC+03"),
    "Europe/Moscow": timezone(timedelta(hours=3), "UTC+03"),

    # Africa
    "Africa/Cairo": timezone(timedelta(hours=2), "UTC+02"),
    "Africa/Johannesburg": timezone(timedelta(hours=2), "UTC+02"),
    "Africa/Lagos": timezone(timedelta(hours=1), "UTC+01"),
    "Africa/Nairobi": timezone(timedelta(hours=3), "UTC+03"),
    "Africa/Casablanca": timezone(timedelta(hours=1), "UTC+01"),

    # Middle East
    "Asia/Dubai": timezone(timedelta(hours=4), "UTC+04"),
    "Asia/Riyadh": timezone(timedelta(hours=3), "UTC+03"),
    "Asia/Jerusalem": timezone(timedelta(hours=2), "UTC+02"),
    "Asia/Tehran": timezone(timedelta(hours=3, minutes=30), "UTC+03:30"),
    "Asia/Qatar": timezone(timedelta(hours=3), "UTC+03"),

    # Asia
    "Asia/Karachi": timezone(timedelta(hours=5), "UTC+05"),
    "Asia/Kolkata": timezone(timedelta(hours=5, minutes=30), "UTC+05:30"),
    "Asia/Dhaka": timezone(timedelta(hours=6), "UTC+06"),
    "Asia/Bangkok": timezone(timedelta(hours=7), "UTC+07"),
    "Asia/Jakarta": timezone(timedelta(hours=7), "UTC+07"),
    "Asia/Singapore": timezone(timedelta(hours=8), "UTC+08"),
    "Asia/Kuala_Lumpur": timezone(timedelta(hours=8), "UTC+08"),
    "Asia/Manila": timezone(timedelta(hours=8), "UTC+08"),
    "Asia/Hong_Kong": timezone(timedelta(hours=8), "UTC+08"),
    "Asia/Shanghai": timezone(timedelta(hours=8), "UTC+08"),
    "Asia/Taipei": timezone(timedelta(hours=8), "UTC+08"),
    "Asia/Tokyo": timezone(timedelta(hours=9), "UTC+09"),
    "Asia/Seoul": timezone(timedelta(hours=9), "UTC+09"),

    # Oceania
    "Australia/Perth": timezone(timedelta(hours=8), "UTC+08"),
    "Australia/Adelaide": timezone(timedelta(hours=9, minutes=30), "UTC+09:30"),
    "Australia/Darwin": timezone(timedelta(hours=9, minutes=30), "UTC+09:30"),
    "Australia/Brisbane": timezone(timedelta(hours=10), "UTC+10"),
    "Australia/Sydney": timezone(timedelta(hours=10), "UTC+10"),
    "Pacific/Auckland": timezone(timedelta(hours=12), "UTC+12"),
    "Pacific/Fiji": timezone(timedelta(hours=12), "UTC+12"),
    "Pacific/Honolulu": timezone(timedelta(hours=-10), "UTC-10"),
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
