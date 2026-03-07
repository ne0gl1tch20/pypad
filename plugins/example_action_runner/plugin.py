class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Action Runner", "List Top Actions", self.list_top_actions)
        self.api.add_menu_action("Plugins/Action Runner", "Run Save Action", self.run_save_action)
        self.api.notify("Action Runner loaded.")

    def list_top_actions(self) -> None:
        actions = self.api.list_actions()
        preview = ", ".join(a.get("label", "") for a in actions[:8]) or "(none)"
        self.api.show_status(f"Actions: {len(actions)} total", 2500)
        self.api.notify(f"First actions: {preview}")

    def run_save_action(self) -> None:
        actions = self.api.list_actions()
        for item in actions:
            aid = (item.get("action_id", "") or "").lower()
            label = (item.get("label", "") or "").lower()
            if "save" in aid or label.startswith("save"):
                if self.api.trigger_action(item.get("action_id", "")):
                    self.api.notify(f"Triggered action: {item.get('label', item.get('action_id', 'unknown'))}")
                    return
        self.api.notify("No save-like action found.")
