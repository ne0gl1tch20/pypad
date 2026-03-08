import random


class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Workspace Sampler", "Create Sample Report", self.create_report)

    def create_report(self) -> None:
        files = self.api.workspace_files()
        if not files:
            self.api.notify("No indexed workspace files yet.")
            return
        random.shuffle(files)
        sample = files[: min(25, len(files))]
        body = ["# Workspace Sample", ""]
        body.append(f"Total indexed: {len(files)}")
        body.append(f"Sample size: {len(sample)}")
        body.append("")
        body.extend(f"- {path}" for path in sample)
        self.api.file_new("\n".join(body) + "\n")
        self.api.plugin_state_set("last_sample_size", len(sample))
