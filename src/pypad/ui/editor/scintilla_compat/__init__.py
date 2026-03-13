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
