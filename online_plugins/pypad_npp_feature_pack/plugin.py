import base64
import binascii
import hashlib
import json


class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/PyPad NPP Feature Pack/Native", "Base64 Encode", self.base64_encode)
        self.api.add_menu_action("Plugins/PyPad NPP Feature Pack/Native", "Base64 Decode", self.base64_decode)
        self.api.add_menu_action("Plugins/PyPad NPP Feature Pack/Native", "JSON Pretty", self.json_pretty)
        self.api.add_menu_action("Plugins/PyPad NPP Feature Pack/Native", "JSON Minify", self.json_minify)
        self.api.add_menu_action("Plugins/PyPad NPP Feature Pack/Native", "SHA256 Digest", self.sha256_digest)
        self.api.add_menu_action("Plugins/PyPad NPP Feature Pack/Native", "Sort Lines", self.sort_lines)
        self.api.add_menu_action("Plugins/PyPad NPP Feature Pack/Native", "Unique Lines", self.unique_lines)

        self.api.add_menu_action("Plugins/PyPad NPP Feature Pack/Bridge", "MIME Tools", self._open_mime_tools)
        self.api.add_menu_action("Plugins/PyPad NPP Feature Pack/Bridge", "Converter", self._open_converter_tools)
        self.api.add_menu_action("Plugins/PyPad NPP Feature Pack/Bridge", "NPP Export", self._open_npp_export_tools)

        self.api.register_command("base64_encode", lambda _args: self.base64_encode())
        self.api.register_command("base64_decode", lambda _args: self.base64_decode())
        self.api.register_command("json_pretty", lambda _args: self.json_pretty())
        self.api.register_command("json_minify", lambda _args: self.json_minify())
        self.api.register_command("sha256_digest", lambda _args: self.sha256_digest())
        self.api.notify("PyPad NPP Feature Pack loaded (native + bridge).")

    def _selected_or_full(self) -> tuple[str, bool]:
        selected = str(self.api.selection_text() or "")
        if selected:
            return selected, True
        return str(self.api.current_text() or ""), False

    def _replace_target(self, text: str, was_selection: bool) -> None:
        if was_selection:
            self.api.replace_selection(text)
            return
        self.api.replace_text(text)

    def base64_encode(self) -> None:
        text, was_selection = self._selected_or_full()
        if not text:
            self.api.show_status("Nothing to encode.", 2000)
            return
        out = base64.b64encode(text.encode("utf-8")).decode("ascii")
        self._replace_target(out, was_selection)
        self.api.show_status("Base64 encoded.", 1800)

    def base64_decode(self) -> None:
        text, was_selection = self._selected_or_full()
        if not text.strip():
            self.api.show_status("Nothing to decode.", 2000)
            return
        try:
            raw = base64.b64decode(text.strip().encode("ascii"), validate=True)
            out = raw.decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            self.api.show_status("Invalid Base64 input.", 2400)
            return
        self._replace_target(out, was_selection)
        self.api.show_status("Base64 decoded.", 1800)

    def json_pretty(self) -> None:
        text, was_selection = self._selected_or_full()
        if not text.strip():
            self.api.show_status("No JSON to format.", 2000)
            return
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            self.api.show_status("Invalid JSON.", 2200)
            return
        out = json.dumps(parsed, indent=2, ensure_ascii=False)
        self._replace_target(out, was_selection)
        self.api.show_status("JSON formatted.", 1800)

    def json_minify(self) -> None:
        text, was_selection = self._selected_or_full()
        if not text.strip():
            self.api.show_status("No JSON to minify.", 2000)
            return
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            self.api.show_status("Invalid JSON.", 2200)
            return
        out = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
        self._replace_target(out, was_selection)
        self.api.show_status("JSON minified.", 1800)

    def sha256_digest(self) -> None:
        text, _was_selection = self._selected_or_full()
        if not text:
            self.api.show_status("Nothing to hash.", 2000)
            return
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.api.insert_text(f"\nSHA256: {digest}")
        self.api.show_status("SHA256 appended.", 1800)

    def sort_lines(self) -> None:
        text, was_selection = self._selected_or_full()
        if not text:
            return
        lines = text.splitlines()
        out = "\n".join(sorted(lines, key=lambda x: x.lower()))
        self._replace_target(out, was_selection)
        self.api.show_status("Lines sorted.", 1800)

    def unique_lines(self) -> None:
        text, was_selection = self._selected_or_full()
        if not text:
            return
        out_lines = []
        seen = set()
        for line in text.splitlines():
            if line in seen:
                continue
            seen.add(line)
            out_lines.append(line)
        self._replace_target("\n".join(out_lines), was_selection)
        self.api.show_status("Duplicate lines removed.", 1800)

    def _open_mime_tools(self) -> None:
        self._run_action("mime_tools_action", {"mime tools..."})

    def _open_converter_tools(self) -> None:
        self._run_action("converter_tools_action", {"converter..."})

    def _open_npp_export_tools(self) -> None:
        self._run_action("npp_export_tools_action", {"npp export..."})

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
