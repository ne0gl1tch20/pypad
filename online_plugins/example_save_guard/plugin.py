class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Save Guard", "Show Last Save Check", self.show_last)

    def on_before_save(self, event) -> None:
        text = self.api.current_text()
        issues = []
        if "TODO" in text or "FIXME" in text:
            issues.append("Contains TODO/FIXME markers")
        trailing = sum(1 for line in text.splitlines() if line.rstrip(" ") != line)
        if trailing > 0:
            issues.append(f"Trailing spaces on {trailing} line(s)")
        title = event.get("title", "Untitled")
        payload = {"title": title, "issues": issues}
        self.api.plugin_state_set("last_save_check", payload)
        if issues:
            self.api.notify(f"Save Guard: {title} -> " + "; ".join(issues))

    def show_last(self) -> None:
        last = self.api.plugin_state_get("last_save_check", {})
        self.api.notify(f"Last save check: {last}")
