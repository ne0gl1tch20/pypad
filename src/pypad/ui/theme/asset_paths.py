"""Resolve bundled asset locations so icons, fonts, and splash resources can be loaded reliably.

This module belongs to the theme and asset resolution layer. It helps explain how `pypad.ui.theme` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

import sys
from pathlib import Path


def resolve_asset_path(*parts: str) -> Path | None:
    """Resolve asset path."""
    for root in _candidate_asset_roots():
        candidate = root.joinpath(*parts)
        if candidate.exists():
            return candidate
    return None


def _candidate_asset_roots() -> list[Path]:
    """Handle candidate asset roots."""
    roots: list[Path] = []

    # PyInstaller onefile extracts bundled data into _MEIPASS.
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        roots.append(Path(meipass) / "assets")

    # Dist folder layout: run.exe next to assets/.
    executable = Path(sys.executable).resolve()
    roots.append(executable.parent / "assets")

    # Development layout: <repo>/src/run.py and <repo>/assets/.
    ui_dir = Path(__file__).resolve().parent
    roots.append(ui_dir.parents[3] / "assets")

    # Backward compatibility with old icon location in source tree.
    roots.append(ui_dir / "icons")
    roots.append(ui_dir)

    return roots
