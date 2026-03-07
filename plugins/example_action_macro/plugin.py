class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Action Macro", "Run Find Macro", self.run_find_macro)
        self.api.add_menu_action("Plugins/Action Macro", "Show Open Tab Count", self.show_tab_count)
        self.api.notify("Action Macro loaded.")

    def run_find_macro(self) -> None:
        actions = self.api.list_actions()
        wanted = ["find", "find and replace", "replace"]
        hits = 0
        for label in wanted:
            match = next((a for a in actions if (a.get("label", "").strip().lower() == label)), None)
            if match and self.api.trigger_action(match.get("action_id", "")):
                hits += 1
        self.api.show_status(f"Macro triggered {hits} action(s)", 2000)

    def show_tab_count(self) -> None:
        self.api.notify(f"Open tabs: {self.api.tab_count()}")
