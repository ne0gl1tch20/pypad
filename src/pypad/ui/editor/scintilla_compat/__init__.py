"""Mark this directory as a Python package and describe the role of the package in the larger application.

This module belongs to the Scintilla compatibility layer used when native QScintilla is unavailable. It helps explain how `pypad.ui.editor.scintilla_compat.__init__` is structured and where this file fits into the runtime workflow.
"""

from .editor import ScintillaCompatEditor
from .metadata import ScintillaCommandMetadata, load_command_metadata
from .models import (
    ColumnBlock,
    FoldRegion,
    HotspotRange,
    IndicatorRange,
    MultiSelectionRange,
    UndoFrame,
    LexerWindow,
    CompatLexerProtocol,
    ScintillaEngineState,
    ScintillaNotification,
)

__all__ = [
    "ScintillaCompatEditor",
    "FoldRegion",
    "ColumnBlock",
    "HotspotRange",
    "IndicatorRange",
    "MultiSelectionRange",
    "UndoFrame",
    "LexerWindow",
    "CompatLexerProtocol",
    "ScintillaEngineState",
    "ScintillaNotification",
    "ScintillaCommandMetadata",
    "load_command_metadata",
]
