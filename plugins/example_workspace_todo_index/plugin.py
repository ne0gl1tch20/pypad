from pathlib import Path


class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Workspace TODO", "Generate TODO Index", self.generate_index)

    def generate_index(self) -> None:
        self.api.run_background(self._build_report, name="todo-index")
        self.api.show_status("TODO index running in background...", 1600)

    def _build_report(self) -> None:
        root = self.api.workspace_root()
        files = self.api.workspace_files()
        rows = []
        for path in files[:1500]:
            p = Path(path)
            try:
                text = p.read_text(encoding="utf-8")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), start=1):
                upper = line.upper()
                if "TODO" in upper or "FIXME" in upper:
                    rows.append((path, i, line.strip()))
                    if len(rows) >= 300:
                        break
            if len(rows) >= 300:
                break
        body = ["# Workspace TODO Index", "", f"Root: {root or '(none)'}", f"Matches: {len(rows)}", ""]
        for path, line_no, line in rows:
            body.append(f"- {path}:{line_no} | {line}")
        if not rows:
            body.append("- No TODO/FIXME found in scanned files.")
        self.api.file_new("\n".join(body) + "\n")
        self.api.plugin_state_set("last_todo_count", len(rows))
