"""Collect folder and workspace timeline entries from filesystem, recovery, and Git sources.

This controller powers the broader timeline surface that appears from Explorer
for folders and the workspace root. The goal is a review-friendly activity view
instead of a plain text dump.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pypad.ui.system.workspace_timeline_models import WorkspaceTimelineEntry


class WorkspaceTimelineController:
    """Build timeline rows for a folder or the active workspace."""

    def __init__(self, window) -> None:
        """Bind the controller to the main window for store and Git access."""

        self.window = window

    def entries_for_scope(self, selected: Path) -> tuple[str, list[WorkspaceTimelineEntry]]:
        """Return a scope label and merged timeline rows for the selected path."""

        scope = selected if selected.is_dir() else selected.parent
        scope_label = self._scope_label(scope)
        entries: list[WorkspaceTimelineEntry] = []
        entries.extend(self._filesystem_entries(scope))
        entries.extend(self._autosave_entries(scope))
        entries.extend(self._recovery_entries(scope))
        entries.extend(self._git_entries(scope))
        return scope_label, self._sort_entries(entries)

    def _filesystem_entries(self, scope: Path) -> list[WorkspaceTimelineEntry]:
        """Collect recently changed files inside the requested scope."""

        candidates: list[Path] = []
        try:
            iterator = scope.rglob("*") if scope.exists() else []
            for child in iterator:
                if not child.is_file():
                    continue
                candidates.append(child)
        except Exception:
            return []
        candidates.sort(key=lambda child: child.stat().st_mtime, reverse=True)
        rows: list[WorkspaceTimelineEntry] = []
        for index, path in enumerate(candidates[:120], start=1):
            try:
                stat = path.stat()
            except Exception:
                continue
            stamp = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            rows.append(
                WorkspaceTimelineEntry(
                    entry_id=f"fs-{index}",
                    source_kind="filesystem",
                    title=path.name,
                    timestamp=stamp,
                    summary=f"Recently changed file in {scope.name or 'workspace'}",
                    file_path=str(path),
                    preview_text=self._build_file_preview(path, stat.st_size),
                    group_label=self._group_label_for_timestamp(stamp),
                    badge_text="File",
                    metadata={"relative_path": self._workspace_relative_path(path)},
                )
            )
        return rows

    def _autosave_entries(self, scope: Path) -> list[WorkspaceTimelineEntry]:
        """Collect autosave snapshots that belong to files inside the scope."""

        store = getattr(self.window, "autosave_store", None)
        if store is None:
            return []
        rows: list[WorkspaceTimelineEntry] = []
        for autosave_id, entry in getattr(store, "entries", {}).items():
            original_path = str(getattr(entry, "original_path", "") or "")
            if not self._path_in_scope(original_path, scope):
                continue
            text = self._read_utf8_text(str(getattr(entry, "autosave_path", "") or ""))
            if text is None:
                continue
            stamp = str(getattr(entry, "saved_at", "") or "")
            rows.append(
                WorkspaceTimelineEntry(
                    entry_id=f"autosave-{autosave_id}",
                    source_kind="autosave",
                    title=str(getattr(entry, "title", "Autosave draft") or "Autosave draft"),
                    timestamp=stamp,
                    summary="Autosave draft stored for recovery",
                    file_path=original_path,
                    preview_text=text,
                    group_label=self._group_label_for_timestamp(stamp),
                    badge_text="Autosave",
                    metadata={"autosave_id": autosave_id, "relative_path": self._workspace_relative_path(Path(original_path))},
                )
            )
        return rows

    def _recovery_entries(self, scope: Path) -> list[WorkspaceTimelineEntry]:
        """Collect crash recovery tabs that belong to the current scope."""

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
        rows: list[WorkspaceTimelineEntry] = []
        for index, item in enumerate(payload.get("tabs", []), start=1):
            if not isinstance(item, dict):
                continue
            file_path = str(item.get("file_path", "") or item.get("path", "") or "")
            text = str(item.get("text", "") or "")
            if not text or not self._path_in_scope(file_path, scope):
                continue
            title = str(item.get("title", Path(file_path).name if file_path else "Recovered tab") or "Recovered tab")
            rows.append(
                WorkspaceTimelineEntry(
                    entry_id=f"recovery-{index}",
                    source_kind="recovery",
                    title=title,
                    timestamp=saved_at,
                    summary="Crash recovery snapshot for a file in this scope",
                    file_path=file_path,
                    preview_text=text,
                    group_label=self._group_label_for_timestamp(saved_at),
                    badge_text="Recovery",
                    metadata={"relative_path": self._workspace_relative_path(Path(file_path)) if file_path else title},
                )
            )
        return rows

    def _git_entries(self, scope: Path) -> list[WorkspaceTimelineEntry]:
        """Collect recent Git commits that affected the selected folder or workspace."""

        if not hasattr(self.window, "_run_git_capture"):
            return []
        rel_scope = self._relative_git_scope(scope)
        args = ["log", "--date=iso", "--name-only", "--pretty=format:%H%x1f%ad%x1f%an%x1f%s", "-40"]
        if rel_scope:
            args.extend(["--", rel_scope])
        rc, out, _err = self.window._run_git_capture(args, timeout=8.0)
        if rc != 0 or not out.strip():
            return []
        rows: list[WorkspaceTimelineEntry] = []
        commit_id = ""
        stamp = ""
        author = ""
        subject = ""
        changed_files: list[str] = []
        commit_index = 0
        for raw in out.splitlines() + [""]:
            line = raw.strip()
            if "\x1f" in line:
                if commit_id:
                    built = self._build_git_entry(commit_index, commit_id, stamp, author, subject, changed_files, rel_scope)
                    if built is not None:
                        rows.append(built)
                commit_index += 1
                parts = line.split("\x1f")
                commit_id, stamp, author, subject = (parts + ["", "", "", ""])[:4]
                changed_files = []
                continue
            if line:
                changed_files.append(line)
        if commit_id:
            built = self._build_git_entry(commit_index, commit_id, stamp, author, subject, changed_files, rel_scope)
            if built is not None:
                rows.append(built)
        return rows

    def _build_git_entry(
        self,
        index: int,
        commit_id: str,
        stamp: str,
        author: str,
        subject: str,
        changed_files: list[str],
        rel_scope: str,
    ) -> WorkspaceTimelineEntry | None:
        """Create one Git timeline entry from parsed log output."""

        preview_lines = self._git_commit_preview(commit_id, rel_scope)
        if not preview_lines:
            preview_lines = [f"Commit: {commit_id[:7]}", f"Author: {author}", f"Date: {stamp}", "", subject or ""]
            if changed_files:
                preview_lines.extend(["", "Files"])
                preview_lines.extend(changed_files[:20])
        primary_file = changed_files[0] if changed_files else ""
        return WorkspaceTimelineEntry(
            entry_id=f"git-{commit_id}",
            source_kind="git_commit",
            title=subject or f"Commit {commit_id[:7]}",
            timestamp=stamp,
            summary=f"Git commit {commit_id[:7]} touched {len(changed_files)} file(s)",
            file_path=self._absolute_workspace_path(primary_file),
            preview_text="\n".join(preview_lines),
            group_label=self._group_label_for_timestamp(stamp),
            badge_text="Git",
            author=author,
            metadata={"commit_id": commit_id, "changed_files": str(len(changed_files))},
        )

    def _git_commit_preview(self, commit_id: str, rel_scope: str) -> list[str]:
        """Return a readable commit preview with stats and a bounded patch excerpt."""

        args = ["show", "--stat", "--summary", "--patch", "--format=fuller", "--unified=3", commit_id]
        if rel_scope:
            args.extend(["--", rel_scope])
        rc, out, _err = self.window._run_git_capture(args, timeout=10.0)
        if rc != 0 or not out.strip():
            return []
        lines = out.splitlines()
        if len(lines) > 220:
            lines = lines[:220] + ["", "... patch preview truncated ..."]
        return lines

    def _build_file_preview(self, path: Path, size_bytes: int) -> str:
        """Return a compact file preview used in the details panel."""

        header = [
            f"File: {path.name}",
            f"Path: {self._workspace_relative_path(path)}",
            f"Size: {size_bytes} bytes",
            "",
        ]
        if size_bytes > 256_000:
            header.append("Preview omitted because the file is large.")
            return "\n".join(header)
        text = self._read_text_with_fallback(path)
        if text is None:
            header.append("Preview unavailable for this file.")
            return "\n".join(header)
        lines = text.splitlines()
        header.extend(lines[:80] if lines else ["(Empty file)"])
        return "\n".join(header)

    @staticmethod
    def _read_text_with_fallback(path: Path) -> str | None:
        """Read text using several common encodings so previews stay resilient."""

        for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
            try:
                return path.read_text(encoding=encoding, errors="replace")
            except Exception:
                continue
        return None

    @staticmethod
    def _read_utf8_text(path: str) -> str | None:
        """Read one UTF-8 text file if it still exists."""

        if not path:
            return None
        try:
            return Path(path).read_text(encoding="utf-8")
        except Exception:
            return None

    def _workspace_relative_path(self, path: Path) -> str:
        """Return a workspace-relative path when possible."""

        root = str(self.window.settings.get("workspace_root", "") or "").strip()
        if not root:
            return str(path)
        try:
            return str(path.resolve().relative_to(Path(root).resolve()))
        except Exception:
            return str(path)

    def _absolute_workspace_path(self, rel_path: str) -> str:
        """Resolve a Git relative path back into an absolute workspace path."""

        if not rel_path:
            return ""
        root = str(self.window.settings.get("workspace_root", "") or "").strip()
        if not root:
            return rel_path
        return str((Path(root) / rel_path).resolve())

    def _relative_git_scope(self, scope: Path) -> str:
        """Return the repository-relative scope path when available."""

        root = str(self.window.settings.get("workspace_root", "") or "").strip()
        if not root:
            return ""
        try:
            return scope.resolve().relative_to(Path(root).resolve()).as_posix()
        except Exception:
            return ""

    @staticmethod
    def _path_in_scope(path_text: str, scope: Path) -> bool:
        """Return whether a filesystem path belongs to the selected scope."""

        if not path_text:
            return False
        try:
            return Path(path_text).resolve().is_relative_to(scope.resolve())
        except AttributeError:
            try:
                Path(path_text).resolve().relative_to(scope.resolve())
                return True
            except Exception:
                return False
        except Exception:
            return False

    @staticmethod
    def _group_label_for_timestamp(timestamp: str) -> str:
        """Return a compact date group label for one timeline timestamp."""

        stamp = timestamp.strip()
        if not stamp:
            return "Undated"
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S%z"):
            try:
                return datetime.strptime(stamp, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return stamp[:10] if len(stamp) >= 10 else stamp

    @staticmethod
    def _scope_label(scope: Path) -> str:
        """Return a friendly label for the current scope."""

        name = scope.name.strip() or str(scope)
        return f"{name} Timeline"

    @staticmethod
    def _sort_entries(entries: list[WorkspaceTimelineEntry]) -> list[WorkspaceTimelineEntry]:
        """Sort timeline entries so recent activity stays near the top."""

        priority = {"autosave": 0, "recovery": 1, "filesystem": 2, "git_commit": 3}
        ordered = sorted(
            entries,
            key=lambda entry: (priority.get(entry.source_kind, 9), entry.timestamp or "", entry.entry_id),
        )
        dynamic = [entry for entry in ordered if entry.source_kind not in {"filesystem"}]
        static = [entry for entry in ordered if entry.source_kind == "filesystem"]
        dynamic.reverse()
        return dynamic + static
