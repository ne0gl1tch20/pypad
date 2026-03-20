"""Detect and describe portable-mode storage for PyPad.

This module keeps portable-mode rules out of the main window and general path
helpers so startup code can ask one clear question: should app data live next
to the executable or in roaming storage?
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PortableModeState:
    """Describe whether portable mode is active and where portable data is stored."""

    enabled: bool
    root: Path | None
    reason: str = ""


def _runtime_base_dir() -> Path:
    """Return the directory that should host portable markers and local app data."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def _portable_marker_candidates(base_dir: Path) -> list[Path]:
    """List supported marker files that explicitly enable portable mode."""

    return [
        base_dir / "portable.mode",
        base_dir / "portable.txt",
        base_dir / "data" / "portable.mode",
    ]


def get_portable_mode_state() -> PortableModeState:
    """Return whether the current runtime should store app data locally."""

    base_dir = _runtime_base_dir()
    for marker in _portable_marker_candidates(base_dir):
        if marker.exists():
            return PortableModeState(enabled=True, root=base_dir / "data", reason=f"marker:{marker.name}")
    return PortableModeState(enabled=False, root=None, reason="")
