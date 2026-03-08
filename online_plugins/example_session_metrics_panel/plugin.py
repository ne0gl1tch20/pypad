from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class Plugin:
    def __init__(self, api) -> None:
        self.api = api
        self.label = None

    def on_load(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        self.label = QLabel("Session metrics: loading")
        layout.addWidget(self.label)
        self.api.add_panel("Session Metrics", panel)
        self.api.start_timer(5000, self.refresh)
        self.refresh()

    def on_change(self, _event) -> None:
        self._bump("changes")

    def on_save(self, _event) -> None:
        self._bump("saves")

    def on_tab_changed(self, _event) -> None:
        self._bump("tab_changes")

    def _bump(self, key: str) -> None:
        self.api.plugin_state_set(key, int(self.api.plugin_state_get(key, 0) or 0) + 1)

    def refresh(self) -> None:
        if self.label is None:
            return
        changes = int(self.api.plugin_state_get("changes", 0) or 0)
        saves = int(self.api.plugin_state_get("saves", 0) or 0)
        tabs = int(self.api.plugin_state_get("tab_changes", 0) or 0)
        self.label.setText(f"Changes: {changes} | Saves: {saves} | Tab switches: {tabs}")
