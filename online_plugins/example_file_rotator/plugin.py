class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/File Rotator", "Save All Writable Tabs", self.save_all_writable)

    def save_all_writable(self) -> None:
        total = self.api.tab_count()
        saved = 0
        start = self.api.active_tab_index()
        for i in range(total):
            idx = (start + i) % max(1, total)
            self.api.switch_to_tab(idx)
            info = self.api.active_tab_info()
            if info.get("read_only", False):
                continue
            if self.api.save_active():
                saved += 1
        if total > 0:
            self.api.switch_to_tab(start)
        self.api.notify(f"Saved {saved}/{total} tab(s).")
