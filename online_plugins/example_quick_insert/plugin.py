from datetime import datetime


class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Quick Insert", "Insert Date Header", self.insert_date_header)
        self.api.add_menu_action("Plugins/Quick Insert", "Insert Ticket Template", self.insert_ticket_template)
        self.api.add_menu_action("Plugins/Quick Insert", "Insert Changelog Entry", self.insert_changelog_entry)

    def insert_date_header(self) -> None:
        self.api.insert_text(f"\n## {datetime.now().strftime('%Y-%m-%d')}\n\n")

    def insert_ticket_template(self) -> None:
        self.api.insert_text("\n### Ticket\n- ID: \n- Summary: \n- Owner: \n- Status: \n\n")

    def insert_changelog_entry(self) -> None:
        self.api.insert_text("\n### Added\n- \n")
