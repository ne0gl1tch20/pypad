from PySide6.QtWidgets import QLabel


class Plugin:
    def __init__(self, api) -> None:
        self.api = api
        self._count = 0
        self._label = None

    def on_load(self) -> None:
        self._label = QLabel("Plugin Example Pack\nChanges observed: 0")
        self.api.add_panel("Plugin Example Pack", self._label)
        self.api.add_menu_action("Plugins/Plugin Example Pack", "Show Overview", self.show_overview)
        self.api.add_menu_action("Help/Plugin Example Pack", "How Plugin Menus Work", self.show_help_example)
        self.api.add_menu_action("Tools/Plugin Example Pack", "Insert Example Note", self.insert_example_note)
        self.api.add_toolbar_action("Main", "Example Pack", self.insert_example_note)
        self.api.start_timer(2000, self._heartbeat)
        self.api.notify("Plugin Example Pack loaded.")

    def on_event(self, name, event) -> None:
        self._count += 1
        if self._label is not None:
            self._label.setText(
                "Plugin Example Pack\n"
                f"Changes observed: {self._count}\n"
                f"Last event: {name}"
            )

    def _heartbeat(self) -> None:
        self.api.show_status("Plugin Example Pack heartbeat", 1200)

    def show_overview(self) -> None:
        info = self.api.app_info()
        self.api.notify(
            "Plugin Example Pack\n"
            f"App: {info.get('app_name', 'PyPad')}\n"
            f"Version: {info.get('version', '-')}\n"
            f"Open tabs: {self.api.tab_count()}"
        )

    def show_help_example(self) -> None:
        self.api.notify("Top-level menus like Help can host plugin actions now.")

    def insert_example_note(self) -> None:
        text = (
            "## Plugin Example Pack\n\n"
            "- Menu example: Plugins / Help / Tools\n"
            "- Topbar example: Main toolbar button\n"
            "- Panel example: dock panel added on load\n"
            "- Hook example: event counter updates live\n"
        )
        self.api.file_new(text=text)
