"""Define normalized timeline rows for folder and workspace review surfaces.

This model keeps the folder/workspace timeline independent from the current-file
timeline so each feature can evolve without mixing restore-specific behavior
with broader activity browsing.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WorkspaceTimelineEntry:
    """Describe one folder or workspace activity row shown in the timeline dialog."""

    entry_id: str
    source_kind: str
    title: str
    timestamp: str
    summary: str
    file_path: str
    preview_text: str
    group_label: str = ""
    badge_text: str = ""
    author: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
