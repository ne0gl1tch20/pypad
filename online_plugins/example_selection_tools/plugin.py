from datetime import datetime


class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Selection Tools", "Quote Selection", self.quote_selection)
        self.api.add_menu_action("Plugins/Selection Tools", "Insert Timestamp", self.insert_timestamp)
        self.api.notify("Selection Tools loaded.")

    def quote_selection(self) -> None:
        selected = self.api.selection_text()
        if selected.strip():
            quoted = "\n".join(f"> {line}" if line.strip() else ">" for line in selected.splitlines())
            self.api.replace_selection(quoted)
        else:
            self.api.insert_text("> ")
        count = int(self.api.plugin_state_get("quote_ops", 0) or 0) + 1
        self.api.plugin_state_set("quote_ops", count)
        self.api.show_status(f"Quote operation #{count}", 1800)

    def insert_timestamp(self) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.api.insert_text(f"[{stamp}] ")
