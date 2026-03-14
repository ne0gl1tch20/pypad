"""Mark this directory as a Python package and describe the role of the package in the larger application.

This module belongs to the main-window orchestration layer that ties together menus, actions, state, and dialogs. It helps explain how `pypad.ui.main_window.__init__` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .window import Notepad as Notepad

__all__ = ["Notepad"]


def __getattr__(name: str):
    """Internal helper for `__getattr__`."""
    if name == "Notepad":
        from .window import Notepad as _Notepad

        return _Notepad
    raise AttributeError(name)
