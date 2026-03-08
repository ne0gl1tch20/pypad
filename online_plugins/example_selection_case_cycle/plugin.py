class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Selection Case", "Cycle Selection Case", self.cycle_case, "Ctrl+Alt+K")

    def cycle_case(self) -> None:
        text = self.api.selection_text()
        if not text:
            self.api.notify("Select text first.")
            return
        mode = int(self.api.plugin_state_get("mode", 0) or 0)
        if mode == 0:
            out = text.lower()
            label = "lower"
        elif mode == 1:
            out = text.upper()
            label = "upper"
        else:
            out = text.title()
            label = "title"
        self.api.replace_selection(out)
        self.api.plugin_state_set("mode", (mode + 1) % 3)
        self.api.show_status(f"Selection case -> {label}", 1400)
