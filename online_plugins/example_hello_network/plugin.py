class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Network", "Say Hello (Network)", self.say_hello_network)
        self.api.add_menu_action("Plugins/Network", "Show Action Count", self.show_action_count)
        self.api.start_timer(30000, self._heartbeat)
        self.say_hello_network()

    def say_hello_network(self) -> None:
        # This validates that the plugin has the `network` permission.
        if self.api.network_allowed():
            total = int(self.api.plugin_state_get("hello_count", 0) or 0) + 1
            self.api.plugin_state_set("hello_count", total)
            self.api.show_status(f"Hello from network-enabled plugin. Count: {total}", 2600)

    def on_save(self, event) -> None:
        title = event.get("title", "Untitled")
        self.api.notify(f"Saved: {title}")

    def _heartbeat(self) -> None:
        if self.api.network_allowed():
            beats = int(self.api.plugin_state_get("heartbeat_count", 0) or 0) + 1
            self.api.plugin_state_set("heartbeat_count", beats)
            if beats % 2 == 0:
                self.api.show_status("Network permission check: ok.", 1600)

    def show_action_count(self) -> None:
        actions = self.api.list_actions()
        self.api.notify(f"Discovered {len(actions)} actions from controller API.")
