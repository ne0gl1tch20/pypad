from datetime import datetime


class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Workspace Report", "Create Workspace Report", self.create_report)
        self.api.notify("Workspace Report loaded.")

    def create_report(self) -> None:
        root = self.api.workspace_root() or "(none)"
        files = self.api.workspace_files()
        status = self.api.workspace_index_status()
        sample = files[:20]
        body = [
            "# Workspace Report",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Root: {root}",
            f"Index ready: {bool(status.get('ready', False))}",
            f"Index scanning: {bool(status.get('scanning', False))}",
            f"Indexed files: {int(status.get('count', 0) or 0)}",
            "",
            "## Sample Files",
        ]
        if sample:
            body.extend(f"- {path}" for path in sample)
        else:
            body.append("- (none)")
        if self.api.file_new("\n".join(body) + "\n"):
            made = int(self.api.plugin_state_get("reports_created", 0) or 0) + 1
            self.api.plugin_state_set("reports_created", made)
            self.api.show_status(f"Workspace report created ({made})", 2200)
        else:
            self.api.notify("Could not open report tab.")
