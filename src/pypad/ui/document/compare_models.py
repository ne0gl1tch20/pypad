"""Define the lightweight data structures used by the compare workflow.

These models keep comparison and merge state separate from the Qt dialog code so
the underlying diff behavior stays easier to test and explain.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompareSource:
    """Describe one side of a compare session using a user-facing label and text."""

    label: str
    text: str


@dataclass(frozen=True)
class DiffHunk:
    """Describe one contiguous changed block between the left and right sources."""

    index: int
    title: str
    left_text: str
    right_text: str
    summary: str
