class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/PyPad AI Assistant/Native", "Explain Selection", self.explain_selection)
        self.api.add_menu_action("Plugins/PyPad AI Assistant/Native", "Rewrite Selection: Shorten", self.rewrite_shorten)
        self.api.add_menu_action("Plugins/PyPad AI Assistant/Native", "Rewrite Selection: Formal", self.rewrite_formal)
        self.api.add_menu_action("Plugins/PyPad AI Assistant/Native", "Rewrite Selection: Fix Grammar", self.rewrite_grammar)
        self.api.add_menu_action("Plugins/PyPad AI Assistant/Native", "Rewrite Selection: Summarize", self.rewrite_summarize)
        self.api.add_menu_action("Plugins/PyPad AI Assistant/Native", "Review Current File", self.review_current_file)
        self.api.add_menu_action("Plugins/PyPad AI Assistant/Native", "Draft Commit Message", self.draft_commit_message)

        self.api.add_menu_action("Plugins/PyPad AI Assistant/Bridge", "AI Chat Panel", self.ai_chat_panel)
        self.api.add_menu_action("Plugins/PyPad AI Assistant/Bridge", "Ask Workspace (Citations)", self.ask_workspace_citations)
        self.api.add_menu_action("Plugins/PyPad AI Assistant/Bridge", "Review Workspace (Citations)", self.review_workspace_citations)
        self.api.add_menu_action("Plugins/PyPad AI Assistant/Bridge", "Attach Current File", self.attach_current_file)
        self.api.add_menu_action("Plugins/PyPad AI Assistant/Bridge", "Attach Selection", self.attach_selection)
        self.api.add_menu_action("Plugins/PyPad AI Assistant/Bridge", "AI Usage Summary", self.ai_usage_summary)

        self.api.register_command("explain_selection", lambda _args: self.explain_selection())
        self.api.register_command("rewrite_shorten", lambda _args: self.rewrite_shorten())
        self.api.register_command("rewrite_formal", lambda _args: self.rewrite_formal())
        self.api.register_command("rewrite_grammar", lambda _args: self.rewrite_grammar())
        self.api.register_command("rewrite_summarize", lambda _args: self.rewrite_summarize())
        self.api.register_command("review_current_file", lambda _args: self.review_current_file())
        self.api.register_command("draft_commit_message", lambda _args: self.draft_commit_message())
        self._tag_host_ai_bridge()
        self.api.notify("PyPad AI Assistant loaded (native prompts + bridge).")

    def _window(self):
        try:
            return self.api.app_window()
        except Exception:
            return None

    def _tag_host_ai_bridge(self) -> None:
        window = self._window()
        if window is None:
            return
        if hasattr(window, "ensure_ai_runtime"):
            try:
                window.ensure_ai_runtime(owner_plugin="pypad_ai_assistant")
            except Exception:
                pass
        # Special marker: this plugin is allowed to orchestrate PyPad AI host
        # components while migration away from built-in wiring is in progress.
        try:
            setattr(window, "_pypad_ai_assist_owner_plugin", "pypad_ai_assistant")
        except Exception:
            pass

    def _selection_or_text(self, max_chars: int = 12000) -> str:
        text = str(self.api.selection_text() or "").strip()
        if not text:
            text = str(self.api.current_text() or "").strip()
        if len(text) > max_chars:
            text = text[:max_chars]
        return text

    def _ask(self, instruction: str, body: str) -> None:
        if not body.strip():
            self.api.show_status("No text available for AI.", 2200)
            return
        prompt = (
            f"{instruction}\n\n"
            "Return only the final answer.\n"
            "Text:\n"
            f"{body}"
        )
        self.api.ask_ai(prompt)
        self.api.show_status("Sent to AI.", 1500)

    def explain_selection(self) -> None:
        self._ask("Explain the following text clearly and concisely.", self._selection_or_text())

    def rewrite_shorten(self) -> None:
        self._ask("Rewrite the following text to be shorter while keeping meaning.", self._selection_or_text())

    def rewrite_formal(self) -> None:
        self._ask("Rewrite the following text in a formal professional tone.", self._selection_or_text())

    def rewrite_grammar(self) -> None:
        self._ask("Fix grammar and clarity in the following text.", self._selection_or_text())

    def rewrite_summarize(self) -> None:
        self._ask("Summarize the following text using concise bullet points.", self._selection_or_text())

    def review_current_file(self) -> None:
        text = self._selection_or_text(max_chars=20000)
        self._ask("Review this file for bugs, risks, and regressions. Prioritize actionable findings.", text)

    def draft_commit_message(self) -> None:
        text = self._selection_or_text(max_chars=8000)
        self._ask("Draft a conventional commit message and short changelog based on this diff/text.", text)

    def ai_chat_panel(self) -> None:
        window = self._window()
        if window is not None and hasattr(window, "toggle_ai_chat_panel"):
            try:
                window.toggle_ai_chat_panel(True)
                return
            except Exception:
                pass
        self._run_action("ai_chat_panel_action", {"ai chat panel"})

    def ask_workspace_citations(self) -> None:
        self._run_action("ai_workspace_citations_action", {"ask workspace (citations)..."})

    def review_workspace_citations(self) -> None:
        self._run_action("ai_review_workspace_citations_action", {"review workspace snippets (citations)..."})

    def attach_current_file(self) -> None:
        self._run_action("ai_attach_current_file_chat_action", {"attach current file to ai chat"})

    def attach_selection(self) -> None:
        self._run_action("ai_attach_selection_chat_action", {"attach selection to ai chat"})

    def ai_usage_summary(self) -> None:
        self._run_action("ai_usage_summary_action", {"ai usage summary"})

    def _run_action(self, action_id: str, fallback_labels: set[str]) -> None:
        if self.api.trigger_action(action_id):
            return
        for row in self.api.list_actions():
            label = str(row.get("label", "")).strip().lower()
            if label in fallback_labels:
                candidate_id = str(row.get("action_id", "")).strip()
                if candidate_id and self.api.trigger_action(candidate_id):
                    return
        self.api.show_status(f"Built-in action unavailable: {action_id}", 2600)
