class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Action Bookmarks", "Bookmark First 3 Actions", self.bookmark_some)
        self.api.add_menu_action("Plugins/Action Bookmarks", "Replay Bookmarks", self.replay)

    def bookmark_some(self) -> None:
        actions = self.api.list_actions()
        picks = [a.get("action_id", "") for a in actions[:3] if a.get("action_id")]
        self.api.plugin_state_set("bookmarks", picks)
        self.api.notify(f"Bookmarked {len(picks)} action(s).")

    def replay(self) -> None:
        bookmarks = self.api.plugin_state_get("bookmarks", [])
        ran = 0
        for aid in bookmarks:
            if self.api.trigger_action(str(aid)):
                ran += 1
        self.api.show_status(f"Replayed {ran}/{len(bookmarks)} bookmarked action(s)", 2200)
