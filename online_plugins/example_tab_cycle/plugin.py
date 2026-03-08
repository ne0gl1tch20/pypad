class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Tab Cycle", "Next Tab", self.next_tab, "Ctrl+Alt+]")
        self.api.add_menu_action("Plugins/Tab Cycle", "Show Active Tab Info", self.show_active_info)
        self.api.start_timer(20000, self._heartbeat)
        self.api.notify("Tab Cycle loaded.")

    def next_tab(self) -> None:
        count = self.api.tab_count()
        if count <= 1:
            self.api.notify("Need at least two tabs to cycle.")
            return
        idx = self.api.active_tab_index()
        next_idx = (idx + 1) % count
        self.api.switch_to_tab(next_idx)
        self.show_active_info()

    def show_active_info(self) -> None:
        info = self.api.active_tab_info()
        title = info.get("title", "Untitled")
        index = int(info.get("index", -1)) + 1
        self.api.show_status(f"Tab {index}: {title}", 1800)

    def _heartbeat(self) -> None:
        beats = int(self.api.plugin_state_get("heartbeat", 0) or 0) + 1
        self.api.plugin_state_set("heartbeat", beats)
