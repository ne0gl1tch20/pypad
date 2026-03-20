"""Define normalized timeline data used by the current-file history workflow.

The timeline overhaul needs one shared model so local history, saved-file
state, and Git entries can appear in the same review surface without each UI
path inventing its own row structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TimelineEntry:
    """Describe one visible item in the timeline review surface."""

    entry_id: str
    source_kind: str
    label: str
    timestamp: str
    summary: str
    text: str
    group_label: str = ""
    badge_text: str = ""
    author: str = ""
    readonly: bool = True
    metadata: dict[str, str] = field(default_factory=dict)
