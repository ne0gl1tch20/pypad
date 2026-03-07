class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.notify("I downloaded a plugin!")
        self.api.add_menu_action(
            "Plugins/Online Example",
            "Say Online Hello",
            self.say_hello,
        )

    def say_hello(self) -> None:
        self.api.show_status("I downloaded a plugin!", 2200)
