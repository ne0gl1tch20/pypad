"""Collect timeline entries for the current file from local and Git-backed sources.

Phase 1 focuses on the current-file timeline. The controller normalizes the
available sources into one list so the UI can feel more like a serious editor
review surface and less like a one-off local-history popup.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pypad.ui.system.timeline_models import TimelineEntry


class TimelineController:
    """Build normalized timeline entries for the active tab."""

    def __init__(self, window) -> None:
        """Bind the controller to the main window that owns Git and file helpers."""

        self.window = window

    def entries_for_tab(self, tab) -> list[TimelineEntry]:
        """Return the current-file timeline entries for the supplied tab."""

        entries: list[TimelineEntry] = []
        current_text = tab.text_edit.get_text()
        entries.append(
            TimelineEntry(
                entry_id="current",
                source_kind="current",
                label="Current Unsaved Version",
                timestamp="Now",
                summary="Current in-editor text",
                text=current_text,
                group_label="Current",
                badge_text="Current",
                readonly=False,
            )
        )
        current_file = str(getattr(tab, "current_file", "") or "").strip()
        if current_file and Path(current_file).exists():
            saved_text = self._load_saved_text(current_file, getattr(tab, "encoding", None))
            if saved_text is not None:
                entries.append(
                    TimelineEntry(
                        entry_id="saved",
                        source_kind="saved_file",
                        label="Saved on Disk",
                        timestamp="Saved file",
                        summary="Last saved file contents on disk",
                        text=saved_text,
                        group_label="Saved File",
                        badge_text="Saved",
                    )
                )
        entries.extend(self._autosave_entries_for_tab(tab, current_file))
        entries.extend(self._recovery_entries_for_tab(tab, current_file))
        for index, entry in enumerate(reversed(getattr(getattr(tab, "version_history", None), "entries", [])), start=1):
            entries.append(
                TimelineEntry(
                    entry_id=f"local-{index}",
                    source_kind="local_history",
                    label=str(getattr(entry, "label", "Snapshot") or "Snapshot"),
                    timestamp=str(getattr(entry, "timestamp", "") or ""),
                    summary="Local history snapshot",
                    text=str(getattr(entry, "text", "") or ""),
                    group_label=self._group_label_for_timestamp(str(getattr(entry, "timestamp", "") or "")),
                    badge_text="Local",
                )
            )
        entries.extend(self._git_entries_for_path(current_file))
        return self._sort_entries(entries)

    def _autosave_entries_for_tab(self, tab, current_file: str) -> list[TimelineEntry]:
        """Return autosave entries that belong to the active document."""

        store = getattr(self.window, "autosave_store", None)
        if store is None:
            return []
        tab_autosave_id = str(getattr(tab, "autosave_id", "") or "")
        rows: list[TimelineEntry] = []
        for autosave_id, entry in getattr(store, "entries", {}).items():
            original_path = str(getattr(entry, "original_path", "") or "")
            if current_file:
                if not original_path or Path(original_path) != Path(current_file):
                    continue
            elif tab_autosave_id:
                if autosave_id != tab_autosave_id:
                    continue
            else:
                continue
            text = self._read_utf8_text(str(getattr(entry, "autosave_path", "") or ""))
            if text is None:
                continue
            stamp = str(getattr(entry, "saved_at", "") or "")
            rows.append(
                TimelineEntry(
                    entry_id=f"autosave-{autosave_id}",
                    source_kind="autosave",
                    label=str(getattr(entry, "title", "Autosave draft") or "Autosave draft"),
                    timestamp=stamp,
                    summary="Autosave draft stored for recovery",
                    text=text,
                    group_label=self._group_label_for_timestamp(stamp),
                    badge_text="Autosave",
                    metadata={"autosave_id": autosave_id},
                )
            )
        return rows

    def _recovery_entries_for_tab(self, tab, current_file: str) -> list[TimelineEntry]:
        """Return crash-recovery snapshots that match the active document."""

        store = getattr(self.window, "recovery_state_store", None)
        if store is None or not hasattr(store, "load_crash_snapshot"):
            return []
        try:
            payload = store.load_crash_snapshot()
        except Exception:
            return []
        if not isinstance(payload, dict):
            return []
        saved_at = str(payload.get("saved_at", "") or "")
        rows: list[TimelineEntry] = []
        for index, row in enumerate(payload.get("tabs", []), start=1):
            if not isinstance(row, dict):
                continue
            file_path = str(row.get("file_path", "") or row.get("path", "") or "")
            text = str(row.get("text", "") or "")
            title = str(row.get("title", "Recovered tab") or "Recovered tab")
            autosave_id = str(row.get("autosave_id", "") or "")
            if not text:
                continue
            if current_file:
                if not file_path or Path(file_path) != Path(current_file):
                    continue
            elif autosave_id:
                if autosave_id != str(getattr(tab, "autosave_id", "") or ""):
                    continue
            elif title.strip().lower() != str(getattr(tab, "title", "") or "").strip().lower():
                continue
            rows.append(
                TimelineEntry(
                    entry_id=f"recovery-{index}",
                    source_kind="recovery",
                    label=title,
                    timestamp=saved_at,
                    summary="Crash recovery snapshot",
                    text=text,
                    group_label=self._group_label_for_timestamp(saved_at),
                    badge_text="Recovery",
                    metadata={"active_file": str(payload.get("active_file", "") or "")},
                )
            )
        return rows

    def _load_saved_text(self, path: str, encoding: str | None) -> str | None:
        """Read the saved file using the window's existing file-loading helpers."""

        try:
            active_encoding = encoding or self.window._encoding_for_path(path)
            text, _encrypted, _password = self.window._load_text_from_path(path, encoding=active_encoding)
            return text
        except Exception:
            return None

    def _git_entries_for_path(self, path: str) -> list[TimelineEntry]:
        """Return a small set of file-history entries when the path belongs to a Git repo."""

        if not path or not hasattr(self.window, "_run_git_capture"):
            return []
        repo_root = self._git_repo_root(path)
        if repo_root is None:
            return []
        rel_path = self._repo_relative_path(path, repo_root)
        if not rel_path:
            return []
        rc, out, _err = self.window._run_git_capture(
            ["log", "--date=iso", "--pretty=format:%H%x1f%ad%x1f%an%x1f%s", "-12", "--", path],
            timeout=8.0,
        )
        if rc != 0 or not out.strip():
            return []
        rows: list[TimelineEntry] = []
        for idx, line in enumerate(out.splitlines(), start=1):
            parts = line.split("\x1f")
            if len(parts) != 4:
                continue
            commit_id, stamp, author, subject = parts
            text = self._git_show_file(repo_root, commit_id, rel_path)
            if text is None:
                continue
            rows.append(
                TimelineEntry(
                    entry_id=f"git-{commit_id}",
                    source_kind="git_commit",
                    label=subject or f"Commit {commit_id[:7]}",
                    timestamp=stamp,
                    summary=f"Git commit {commit_id[:7]} by {author}",
                    text=text,
                    group_label=self._group_label_for_timestamp(stamp),
                    badge_text="Git",
                    author=author,
                    metadata={"commit_id": commit_id, "relative_path": rel_path},
                )
            )
        return rows

    def _git_repo_root(self, path: str) -> str | None:
        """Return the Git repository root for the supplied file path when available."""

        rc, out, _err = self.window._run_git_capture(["rev-parse", "--show-toplevel"], timeout=5.0, cwd=str(Path(path).parent))
        if rc != 0:
            return None
        root = str(out.strip() or "")
        return root or None

    @staticmethod
    def _repo_relative_path(path: str, repo_root: str) -> str:
        """Return a Git-friendly repository-relative path using forward slashes."""

        try:
            return Path(path).resolve().relative_to(Path(repo_root).resolve()).as_posix()
        except Exception:
            return ""

    def _git_show_file(self, repo_root: str, commit_id: str, rel_path: str) -> str | None:
        """Return file contents for one commit/path pair when Git can provide them."""

        rc, out, _err = self.window._run_git_capture(
            ["show", f"{commit_id}:{rel_path}"],
            timeout=8.0,
            cwd=repo_root,
        )
        if rc != 0:
            return None
        return out

    @staticmethod
    def _read_utf8_text(path: str) -> str | None:
        """Read one UTF-8 text file for timeline preview when it still exists."""

        if not path:
            return None
        try:
            return Path(path).read_text(encoding="utf-8")
        except Exception:
            return None

    @staticmethod
    def _group_label_for_timestamp(timestamp: str) -> str:
        """Return a compact date group label for one timeline timestamp."""

        stamp = timestamp.strip()
        if not stamp or stamp.lower() in {"now", "saved file"}:
            return "Current"
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S%z"):
            try:
                return datetime.strptime(stamp, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return stamp[:10] if len(stamp) >= 10 else stamp

    @staticmethod
    def _sort_entries(entries: list[TimelineEntry]) -> list[TimelineEntry]:
        """Keep current/saved entries first, then sort dated entries from newest to oldest."""

        priority = {
            "current": 0,
            "saved_file": 1,
            "autosave": 2,
            "recovery": 3,
            "local_history": 4,
            "git_commit": 5,
        }

        def sort_key(entry: TimelineEntry) -> tuple[int, str, str]:
            return (
                priority.get(entry.source_kind, 9),
                entry.timestamp or "",
                entry.entry_id,
            )

        ordered = sorted(entries, key=sort_key)
        dated = [entry for entry in ordered if entry.source_kind not in {"current", "saved_file"}]
        fixed = [entry for entry in ordered if entry.source_kind in {"current", "saved_file"}]
        dated.reverse()
        return fixed + dated
