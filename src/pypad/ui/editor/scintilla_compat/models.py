"""Define structured data models shared by the Scintilla compatibility layer.

This module belongs to the Scintilla compatibility layer used when native QScintilla is unavailable. It helps explain how `pypad.ui.editor.scintilla_compat` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class FoldRegion:
    """Represent the fold region."""
    start: int
    end: int
    level: int


@dataclass
class ColumnBlock:
    """Represent the column block."""
    line_lo: int
    line_hi: int
    col_lo: int
    col_hi: int


@dataclass
class HotspotRange:
    """Represent the hotspot range."""
    start: int
    end: int
    payload: str = ""


@dataclass
class IndicatorRange:
    """Represent the indicator range."""
    start: int
    end: int
    payload: str = ""
    value: int = 0


@dataclass
class MultiSelectionRange:
    """Represent the multi selection range."""
    anchor: int
    caret: int
    virtual_space_anchor: int = 0
    virtual_space_caret: int = 0

    @property
    def start(self) -> int:
        """Start."""
        return min(int(self.anchor), int(self.caret))

    @property
    def end(self) -> int:
        """End."""
        return max(int(self.anchor), int(self.caret))


@dataclass
class ScintillaNotification:
    """Represent the scintilla notification."""
    code: str
    position: int = -1
    line: int = -1
    text: str = ""
    value: int = 0
    metadata: dict[str, Any] | None = None


@dataclass
class ScintillaEngineState:
    """Compact state-bank used to emulate a richer Scintilla-like runtime."""

    variables: list[int]
    toggles: list[bool]
    channels: list[int]
    checksums: list[int]
    generation: int = 0

    @classmethod
    def create_default(cls) -> "ScintillaEngineState":
        """Create default."""
        return cls(
            variables=[0] * 512,
            toggles=[False] * 128,
            channels=[0] * 64,
            checksums=[0] * 16,
            generation=0,
        )


@dataclass
class UndoFrame:
    """Represent the undo frame."""
    before_text: str
    after_text: str
    before_cursor: int
    after_cursor: int
    op: str = ""
    pos_start: int = 0
    pos_end_before: int = 0
    pos_end_after: int = 0


@dataclass
class LexerWindow:
    """Represent the lexer window."""
    start: int
    end: int
    prev_state: int = 0


class CompatLexerProtocol(Protocol):
    """Represent the compat lexer protocol."""
    def lex_incremental(self, text: str, start: int, end: int, prev_state: int = 0) -> tuple[list[tuple[int, int, int]], dict[int, FoldRegion], int]:
        """Lex incremental."""
        ...
