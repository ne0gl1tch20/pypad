import time


class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/PyPad Power User/Native", "Sort Selected Lines", self.sort_selected_lines)
        self.api.add_menu_action("Plugins/PyPad Power User/Native", "Unique Selected Lines", self.unique_selected_lines)
        self.api.add_menu_action("Plugins/PyPad Power User/Native", "Trim Trailing Spaces", self.trim_trailing_spaces)
        self.api.add_menu_action("Plugins/PyPad Power User/Native", "Tabs Snapshot Report", self.tabs_snapshot_report)
        self.api.add_menu_action("Plugins/PyPad Power User/Native", "Workspace Snapshot Report", self.workspace_snapshot_report)

        self.api.add_menu_action("Plugins/PyPad Power User/Bridge", "Command Palette", self.command_palette)
        self.api.add_menu_action("Plugins/PyPad Power User/Bridge", "Open Workspace Folder", self.open_workspace_folder)
        self.api.add_menu_action("Plugins/PyPad Power User/Bridge", "Workspace Files", self.workspace_files)
        self.api.add_menu_action("Plugins/PyPad Power User/Bridge", "Search Workspace", self.search_workspace)
        self.api.add_menu_action("Plugins/PyPad Power User/Bridge", "Start Macro Recording", self.start_macro_recording)
        self.api.add_menu_action("Plugins/PyPad Power User/Bridge", "Stop Macro Recording", self.stop_macro_recording)
        self.api.add_menu_action("Plugins/PyPad Power User/Bridge", "Playback Macro", self.play_macro)
        self.api.add_menu_action("Plugins/PyPad Power User/Bridge", "Save Recorded Macro", self.save_recorded_macro)
        self.api.add_menu_action("Plugins/PyPad Power User/Bridge", "Run Macro Multiple Times", self.run_macro_multiple_times)
        self.api.add_menu_action("Plugins/PyPad Power User/Bridge", "Manage Macro Shortcuts", self.manage_macro_shortcuts)
        self.api.add_menu_action("Plugins/PyPad Power User/Bridge", "Column Mode", self.column_mode)
        self.api.add_menu_action("Plugins/PyPad Power User/Bridge", "Multi-Caret", self.multi_caret)
        self.api.add_menu_action("Plugins/PyPad Power User/Bridge", "Quiz Mode", self.quiz_mode)

        self.api.register_command("tabs_snapshot_report", lambda _args: self.tabs_snapshot_report())
        self.api.register_command("workspace_snapshot_report", lambda _args: self.workspace_snapshot_report())
        self.api.notify("PyPad Power User loaded (native + bridge).")

    def _selection_or_full(self) -> tuple[str, bool]:
        selected = str(self.api.selection_text() or "")
        if selected:
            return selected, True
        return str(self.api.current_text() or ""), False

    def sort_selected_lines(self) -> None:
        text, was_selection = self._selection_or_full()
        if not text:
            self.api.show_status("Nothing to sort.", 2000)
            return
        out = "\n".join(sorted(text.splitlines(), key=lambda x: x.lower()))
        if was_selection:
            self.api.replace_selection(out)
        else:
            self.api.replace_text(out)
        self.api.show_status("Lines sorted.", 1800)

    def unique_selected_lines(self) -> None:
        text, was_selection = self._selection_or_full()
        if not text:
            self.api.show_status("Nothing to deduplicate.", 2000)
            return
        seen = set()
        out_lines = []
        for line in text.splitlines():
            if line in seen:
                continue
            seen.add(line)
            out_lines.append(line)
        out = "\n".join(out_lines)
        if was_selection:
            self.api.replace_selection(out)
        else:
            self.api.replace_text(out)
        self.api.show_status("Duplicate lines removed.", 1800)

    def trim_trailing_spaces(self) -> None:
        text = str(self.api.current_text() or "")
        if not text:
            return
        out = "\n".join(line.rstrip(" \t") for line in text.splitlines())
        self.api.replace_text(out)
        self.api.show_status("Trailing spaces trimmed.", 1800)

    def tabs_snapshot_report(self) -> None:
        rows = self.api.open_tabs()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        lines = [f"# Tabs Snapshot", f"Generated: {now}", ""]
        if not rows:
            lines.append("- No open tabs")
        for i, row in enumerate(rows, start=1):
            lines.append(f"{i}. {row.get('title', '')} :: {row.get('path', '')}")
        self.api.file_new("\n".join(lines))
        self.api.show_status("Tabs snapshot opened in new tab.", 2200)

    def workspace_snapshot_report(self) -> None:
        root = str(self.api.workspace_root() or "")
        status = self.api.workspace_index_status()
        files = self.api.workspace_files()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "# Workspace Snapshot",
            f"Generated: {now}",
            f"Root: {root or '-'}",
            f"Index Ready: {bool(status.get('ready', False))}",
            f"Index Scanning: {bool(status.get('scanning', False))}",
            f"Indexed Count: {int(status.get('count', 0) or 0)}",
            "",
            "## Files",
        ]
        if not files:
            lines.append("- No workspace files")
        for path in files[:200]:
            lines.append(f"- {path}")
        self.api.file_new("\n".join(lines))
        self.api.show_status("Workspace snapshot opened in new tab.", 2200)

    def command_palette(self) -> None:
        self._run_action("command_palette_action", {"command palette..."})

    def open_workspace_folder(self) -> None:
        self._run_action("open_workspace_action", {"open workspace folder..."})

    def workspace_files(self) -> None:
        self._run_action("workspace_files_action", {"workspace files..."})

    def search_workspace(self) -> None:
        self._run_action("workspace_search_action", {"search workspace..."})

    def start_macro_recording(self) -> None:
        self._run_action("start_macro_recording_action", {"start recording"})

    def stop_macro_recording(self) -> None:
        self._run_action("stop_macro_recording_action", {"stop recording"})

    def play_macro(self) -> None:
        self._run_action("play_macro_action", {"playback macro"})

    def save_recorded_macro(self) -> None:
        self._run_action("save_current_macro_action", {"save current recorded macro..."})

    def run_macro_multiple_times(self) -> None:
        self._run_action("run_macro_multiple_times_action", {"run a macro multiple times..."})

    def manage_macro_shortcuts(self) -> None:
        self._run_action("modify_macro_shortcut_delete_action", {"modify shortcut/delete macro..."})

    def column_mode(self) -> None:
        self._run_action("column_mode_action", {"column mode"})

    def multi_caret(self) -> None:
        self._run_action("multi_caret_action", {"multi-caret"})

    def quiz_mode(self) -> None:
        self._run_action("quiz_action", {"quiz mode"})

    def _run_action(self, action_id: str, fallback_labels: set[str]) -> None:
        if self.api.trigger_action(action_id):
            return
        for row in self.api.list_actions():
            label = str(row.get("label", "")).strip().lower()
            if label in fallback_labels:
                candidate_id = str(row.get("action_id", "")).strip()
                if candidate_id and self.api.trigger_action(candidate_id):
                    return
        self.api.show_status(f"Built-in action unavailable: {action_id}", 2600)
