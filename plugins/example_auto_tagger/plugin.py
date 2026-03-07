import re


class Plugin:
    def __init__(self, api) -> None:
        self.api = api
        self.rules = {
            "python": r"\b(def|class|import|from)\b",
            "markdown": r"(^#\s)|(^- \[.\])",
            "todo": r"\b(TODO|FIXME|BUG)\b",
            "url": r"https?://",
        }

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Auto Tagger", "Tag Current Document", self.tag_current_document)
        self.api.add_menu_action("Plugins/Auto Tagger", "Show Tag Stats", self.show_stats)

    def tag_current_document(self) -> None:
        text = self.api.current_text()
        matched = []
        lower = text.lower()
        for tag, pattern in self.rules.items():
            if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
                matched.append(tag)
            elif tag in lower:
                matched.append(tag)
        matched = sorted(set(matched))
        self.api.plugin_state_set("last_tags", matched)
        for tag in matched:
            key = f"tag_count:{tag}"
            self.api.plugin_state_set(key, int(self.api.plugin_state_get(key, 0) or 0) + 1)
        self.api.notify("Detected tags: " + (", ".join(matched) if matched else "none"))

    def show_stats(self) -> None:
        last = self.api.plugin_state_get("last_tags", [])
        all_tags = sorted(self.rules.keys())
        stats = [f"{t}={int(self.api.plugin_state_get(f'tag_count:{t}', 0) or 0)}" for t in all_tags]
        self.api.notify(f"Last tags: {last} | totals: {', '.join(stats)}")
