from datetime import datetime


class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Session Notes", "Append Session Note", self.append_note)
        self.api.add_menu_action("Plugins/Session Notes", "Show Session Stats", self.show_stats)
        self.api.notify("Session Notes loaded.")

    def append_note(self) -> None:
        created = self.api.file_new()
        if not created:
            self.api.notify("Could not create a new note tab.")
            return
        note_no = int(self.api.plugin_state_get("notes_created", 0) or 0) + 1
        self.api.plugin_state_set("notes_created", note_no)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.api.replace_text(f"# Session Note {note_no}\n\nCreated: {stamp}\n\n- ")
        self.api.show_status(f"Created session note #{note_no}", 2200)

    def show_stats(self) -> None:
        note_no = int(self.api.plugin_state_get("notes_created", 0) or 0)
        self.api.notify(f"Session notes created: {note_no}")
