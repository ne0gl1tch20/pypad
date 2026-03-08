class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Hook Logger", "Show Hook Counters", self.show_counters)
        self.api.notify("Hook Logger loaded.")

    def on_event(self, name, _event) -> None:
        key = f"hook_count:{name}"
        count = int(self.api.plugin_state_get(key, 0) or 0) + 1
        self.api.plugin_state_set(key, count)

    def show_counters(self) -> None:
        keys = [
            "on_open",
            "on_close",
            "on_change",
            "on_tab_changed",
            "on_before_save",
            "on_after_save",
            "on_window_focus",
            "on_window_blur",
        ]
        parts = []
        for key in keys:
            count = int(self.api.plugin_state_get(f"hook_count:{key}", 0) or 0)
            if count > 0:
                parts.append(f"{key}={count}")
        self.api.notify("Hook counters: " + (", ".join(parts) if parts else "(none yet)"))
