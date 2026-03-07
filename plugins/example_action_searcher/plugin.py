class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Action Searcher", "Find 'Format' Actions", self.find_format_actions)
        self.api.add_menu_action("Plugins/Action Searcher", "Trigger First 'Format'", self.trigger_first_format)

    def _find(self, term: str):
        t = term.lower().strip()
        return [a for a in self.api.list_actions() if t in str(a.get("label", "")).lower()]

    def find_format_actions(self) -> None:
        matches = self._find("format")
        preview = ", ".join(m.get("label", "") for m in matches[:8]) or "(none)"
        self.api.notify(f"Found {len(matches)} format action(s): {preview}")

    def trigger_first_format(self) -> None:
        matches = self._find("format")
        if not matches:
            self.api.notify("No matching actions.")
            return
        aid = matches[0].get("action_id", "")
        if self.api.trigger_action(aid):
            self.api.show_status(f"Triggered: {matches[0].get('label', aid)}", 1500)
        else:
            self.api.notify("Could not trigger action.")
