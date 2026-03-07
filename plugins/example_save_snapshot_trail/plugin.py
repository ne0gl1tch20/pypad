from datetime import datetime


class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Save Trail", "Open Save Trail Report", self.open_report)

    def on_after_save(self, event) -> None:
        items = list(self.api.plugin_state_get("trail", []))
        items.insert(
            0,
            {
                "when": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "title": event.get("title", "Untitled"),
                "mode": event.get("save_mode", "text"),
            },
        )
        self.api.plugin_state_set("trail", items[:30])

    def open_report(self) -> None:
        items = list(self.api.plugin_state_get("trail", []))
        lines = ["# Save Snapshot Trail", ""]
        if not items:
            lines.append("- No saves captured yet.")
        else:
            for row in items:
                lines.append(f"- {row.get('when', '?')} | {row.get('title', 'Untitled')} | mode={row.get('mode', 'text')}")
        self.api.file_new("\n".join(lines) + "\n")
