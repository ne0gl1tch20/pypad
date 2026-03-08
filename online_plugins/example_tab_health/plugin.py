class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Tab Health", "Show Health Snapshot", self.show_snapshot)
        self.api.start_timer(25000, self._tick)

    def on_tab_changed(self, _event) -> None:
        self.api.plugin_state_set(
            "tab_switches",
            int(self.api.plugin_state_get("tab_switches", 0) or 0) + 1,
        )

    def _tick(self) -> None:
        ticks = int(self.api.plugin_state_get("health_ticks", 0) or 0) + 1
        self.api.plugin_state_set("health_ticks", ticks)
        if ticks % 2 == 0:
            self.show_snapshot()

    def show_snapshot(self) -> None:
        info = self.api.active_tab_info()
        switches = int(self.api.plugin_state_get("tab_switches", 0) or 0)
        self.api.notify(
            f"Tabs={self.api.tab_count()} current={info.get('title', 'Untitled')} switches={switches}"
        )
