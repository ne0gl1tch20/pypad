"""Built-in offline productivity tools exposed through the Tools menu."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .registry import BuiltInToolsController, ToolDescriptor

__all__ = ["BuiltInToolsController", "ToolDescriptor"]


def __getattr__(name: str):
    if name in {"BuiltInToolsController", "ToolDescriptor"}:
        from .registry import BuiltInToolsController, ToolDescriptor

        return {
            "BuiltInToolsController": BuiltInToolsController,
            "ToolDescriptor": ToolDescriptor,
        }[name]
    raise AttributeError(name)
