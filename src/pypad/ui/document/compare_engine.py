"""Build review-friendly compare data from pairs of plain-text document sources.

This module keeps diff generation and merge decisions independent from the dialog
layer so the compare workflow can evolve without burying logic inside widget code.
"""

from __future__ import annotations

import difflib
from typing import Iterable

from .compare_models import DiffHunk


def build_diff_hunks(left_text: str, right_text: str) -> list[DiffHunk]:
    """Return grouped diff hunks suitable for a compare dialog review surface."""
    matcher = difflib.SequenceMatcher(None, left_text.splitlines(), right_text.splitlines())
    hunks: list[DiffHunk] = []
    for index, (tag, i1, i2, j1, j2) in enumerate(matcher.get_opcodes(), start=1):
        if tag == "equal":
            continue
        left_chunk = left_text.splitlines()[i1:i2]
        right_chunk = right_text.splitlines()[j1:j2]
        summary = _build_hunk_summary(tag, len(left_chunk), len(right_chunk))
        hunks.append(
            DiffHunk(
                index=index,
                title=f"Change {index}",
                left_text="\n".join(left_chunk),
                right_text="\n".join(right_chunk),
                summary=summary,
            )
        )
    return hunks


def build_unified_diff(left_text: str, right_text: str, *, left_label: str, right_label: str) -> str:
    """Render a unified diff string for secondary copy/export and detailed review."""
    return "\n".join(
        difflib.unified_diff(
            left_text.splitlines(),
            right_text.splitlines(),
            fromfile=left_label,
            tofile=right_label,
            lineterm="",
        )
    )


def apply_hunk_choices(
    left_text: str,
    right_text: str,
    *,
    use_left_hunks: Iterable[int],
    use_right_hunks: Iterable[int],
) -> str:
    """Merge changed blocks by choosing the left or right version per hunk index.

    Any hunk not explicitly selected falls back to the right-side content so the
    merged result matches the reviewed destination by default.
    """
    left_lines = left_text.splitlines()
    right_lines = right_text.splitlines()
    matcher = difflib.SequenceMatcher(None, left_lines, right_lines)
    selected_left = set(int(idx) for idx in use_left_hunks)
    selected_right = set(int(idx) for idx in use_right_hunks)
    out_lines: list[str] = []
    hunk_index = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            out_lines.extend(left_lines[i1:i2])
            continue
        hunk_index += 1
        if hunk_index in selected_left:
            out_lines.extend(left_lines[i1:i2])
        elif hunk_index in selected_right or hunk_index not in selected_left:
            out_lines.extend(right_lines[j1:j2])
    return "\n".join(out_lines)


def _build_hunk_summary(tag: str, left_count: int, right_count: int) -> str:
    """Produce a readable status summary so color is not the only diff signal."""
    labels = {
        "replace": "Modified",
        "delete": "Removed from left side",
        "insert": "Added on right side",
    }
    heading = labels.get(tag, "Changed")
    return f"{heading}: left {left_count} line(s), right {right_count} line(s)"
