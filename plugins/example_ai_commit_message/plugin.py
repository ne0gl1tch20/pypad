class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/AI Commit", "Draft Commit Message", self.draft_commit_message)

    def draft_commit_message(self) -> None:
        text = self.api.selection_text().strip() or self.api.current_text().strip()
        if not text:
            self.api.notify("No text to summarize for commit message.")
            return
        prompt = (
            "Create 5 concise git commit message options (imperative mood).\n"
            "Output as bullets.\n\n"
            f"Changes:\n{text[:12000]}"
        )
        self.api.ask_ai(prompt)
        self.api.plugin_state_set(
            "ai_requests",
            int(self.api.plugin_state_get("ai_requests", 0) or 0) + 1,
        )
