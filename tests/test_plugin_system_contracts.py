import os
import shutil
import sys
import time
import unittest
import zipfile
import threading
import json
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMainWindow, QToolBar

from pypad.ui.features.advanced_features import PluginAPI, PluginHost, PluginRecord


class _FakeTextEdit:
    def __init__(self, text: str = "hello world") -> None:
        self._text = text
        self._selection = "hello"
        self._modified = False
        self._read_only = False

    def get_text(self) -> str:
        return self._text

    def selected_text(self) -> str:
        return self._selection

    def selection_range(self):
        return (0, len(self._selection))

    def is_read_only(self) -> bool:
        return self._read_only

    def is_modified(self) -> bool:
        return self._modified

    def set_text(self, text: str) -> None:
        self._text = str(text)

    def set_modified(self, value: bool) -> None:
        self._modified = bool(value)

    def insert_text(self, text: str) -> None:
        self._text += str(text)

    def has_selection(self) -> bool:
        return bool(self._selection)

    def replace_selection(self, text: str) -> None:
        self._selection = str(text)


class _FakeTab:
    def __init__(self, name: str = "Untitled") -> None:
        self.current_file = name
        self.text_edit = _FakeTextEdit()


class _FakeTabWidget:
    def __init__(self, owner) -> None:
        self._owner = owner

    def count(self) -> int:
        return len(self._owner._tabs)

    def currentIndex(self) -> int:
        return int(getattr(self._owner, "_idx", 0))

    def setCurrentIndex(self, idx: int) -> None:
        self._owner._idx = int(idx)

    def widget(self, idx: int):
        return self._owner._tabs[int(idx)]


class _FakeWorkspaceController:
    def __init__(self) -> None:
        self._index_ready = True
        self._index_scanning = False
        self._index_files = ["a.py", "b.md"]

    def workspace_root(self) -> str:
        return str(ROOT)

    def workspace_files(self) -> list[str]:
        return [str(ROOT / "README.md"), str(ROOT / "CHANGELOG.md")]

    def _start_background_scan(self, force: bool = False) -> None:
        self._index_scanning = bool(force)


class _FakeAIController:
    def _start_generation(self, prompt: str, title: str, *, action_name: str = "") -> None:
        _ = (prompt, title, action_name)


class _PluginTestWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = {
            "enabled_plugins": [],
            "trusted_plugin_hashes": {},
            "quarantined_plugins": [],
            "plugin_permission_overrides": {},
            "plugin_startup_safe_mode": False,
            "defer_plugin_load_on_startup": False,
            "plugin_startup_defer_ms": 0,
            "plugin_allow_unsafe_ui_bridge": False,
        }
        self.messages: list[str] = []
        self.logs: list[str] = []
        self.tab_widget = _FakeTabWidget(self)
        self.main_toolbar = QToolBar("Main", self)
        self.addToolBar(self.main_toolbar)
        self.workspace_controller = _FakeWorkspaceController()
        self.ai_controller = _FakeAIController()
        self._tabs = [_FakeTab("one.txt"), _FakeTab("two.txt")]

    def active_tab(self):
        return self._tabs[getattr(self, "_idx", 0)]

    def _tab_display_name(self, tab) -> str:
        return str(getattr(tab, "current_file", "Untitled"))

    def show_status_message(self, text: str, timeout_ms: int = 0) -> None:
        _ = timeout_ms
        self.messages.append(str(text))

    def log_event(self, level: str, text: str) -> None:
        self.logs.append(f"{level}:{text}")

    def save_settings_to_disk(self) -> None:
        return

    def file_new(self) -> None:
        self._tabs.append(_FakeTab("new.txt"))
        self._idx = len(self._tabs) - 1

    def file_save(self) -> bool:
        return True

    def _open_file_path(self, _path: str) -> bool:
        return True


class PluginAPIContractsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = _PluginTestWindow()
        self.record = PluginRecord(
            plugin_id="contract_plugin",
            name="Contract Plugin",
            description="",
            permissions={"file", "ui", "menu"},
            path=ROOT,
            enabled=True,
            digest="x",
        )
        self.api = PluginAPI(self.window, self.record)

    def test_unsafe_ui_bridge_blocked_by_default(self) -> None:
        with self.assertRaises(RuntimeError):
            self.api.app_window()
        with self.assertRaises(RuntimeError):
            self.api.active_tab()

    def test_unsafe_ui_bridge_allowed_when_enabled(self) -> None:
        self.window.settings["plugin_allow_unsafe_ui_bridge"] = True
        self.assertIsNotNone(self.api.app_window())
        self.assertIsNotNone(self.api.active_tab())

    def test_unsafe_ui_bridge_allowed_for_privileged_tag(self) -> None:
        self.window.settings["plugin_allow_unsafe_ui_bridge"] = False
        self.record.tags = {"pypad_internal_access"}
        self.assertIsNotNone(self.api.app_window())
        self.assertIsNotNone(self.api.active_tab())

    def test_plugin_state_roundtrip(self) -> None:
        self.api.plugin_state_set("k", {"n": 1})
        value = self.api.plugin_state_get("k", {})
        self.assertEqual(value, {"n": 1})

    def test_tab_and_file_flow_methods(self) -> None:
        before = self.api.tab_count()
        self.assertTrue(self.api.file_new("abc"))
        self.assertEqual(self.api.tab_count(), before + 1)
        self.assertTrue(self.api.switch_to_tab(0))
        info = self.api.active_tab_info()
        self.assertIn("title", info)
        self.assertTrue(self.api.save_active())


class PluginExamplesSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_discover_and_load_all_example_plugins(self) -> None:
        src_plugins = ROOT / "plugins"
        tmp_root = ROOT / "tests_tmp"
        tmp_plugins = tmp_root / f"plugins_smoke_{time.time_ns()}"
        shutil.copytree(src_plugins, tmp_plugins)
        window = _PluginTestWindow()
        try:
            with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=tmp_plugins):
                host = PluginHost(window)
                discovered = host.discover()
                self.assertGreaterEqual(len(discovered), 10)
                window.settings["enabled_plugins"] = [rec.plugin_id for rec in discovered]
                window.settings["trusted_plugin_hashes"] = {rec.plugin_id: rec.digest.lower() for rec in discovered}
                with patch.object(PluginHost, "_trust_prompt", return_value=True):
                    host.reload()
                loaded = [rec for rec in host.records if rec.enabled and rec.instance is not None]
                blocked = [rec for rec in host.records if rec.enabled and rec.instance is None]
                self.assertGreaterEqual(len(loaded), 3)
                self.assertEqual(len(loaded) + len(blocked), len(discovered))
                host._unload_all()
        finally:
            shutil.rmtree(tmp_plugins, ignore_errors=True)


class PluginScaffoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_scaffold_plugin_creates_manifest_and_script(self) -> None:
        tmp_root = ROOT / "tests_tmp"
        tmp_plugins = tmp_root / f"plugins_scaffold_{time.time_ns()}"
        tmp_plugins.mkdir(parents=True, exist_ok=True)
        window = _PluginTestWindow()
        try:
            with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=tmp_plugins):
                host = PluginHost(window)
                path = host.scaffold_plugin(
                    plugin_id="demo_scaffold",
                    name="Demo Scaffold",
                    description="scaffold test",
                    permissions={"menu", "file"},
                )
                self.assertTrue((path / "plugin.json").exists())
                self.assertTrue((path / "plugin.py").exists())
                manifest = (path / "plugin.json").read_text(encoding="utf-8")
                self.assertIn('"id": "demo_scaffold"', manifest)
        finally:
            shutil.rmtree(tmp_plugins, ignore_errors=True)

    def test_scaffold_plugin_rejects_invalid_id(self) -> None:
        tmp_root = ROOT / "tests_tmp"
        tmp_plugins = tmp_root / f"plugins_scaffold_bad_{time.time_ns()}"
        tmp_plugins.mkdir(parents=True, exist_ok=True)
        window = _PluginTestWindow()
        try:
            with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=tmp_plugins):
                host = PluginHost(window)
                with self.assertRaises(ValueError):
                    host.scaffold_plugin(plugin_id="X", name="Bad")
        finally:
            shutil.rmtree(tmp_plugins, ignore_errors=True)

    def test_export_plugin_creates_zip_bundle(self) -> None:
        tmp_root = ROOT / "tests_tmp"
        tmp_plugins = tmp_root / f"plugins_export_{time.time_ns()}"
        tmp_plugins.mkdir(parents=True, exist_ok=True)
        window = _PluginTestWindow()
        try:
            with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=tmp_plugins):
                host = PluginHost(window)
                host.scaffold_plugin(plugin_id="demo_export", name="Demo Export", permissions={"menu"})
                out_zip = tmp_root / f"demo_export_{time.time_ns()}.zip"
                try:
                    host.export_plugin("demo_export", out_zip)
                    self.assertTrue(out_zip.exists())
                    with zipfile.ZipFile(out_zip, "r") as zf:
                        names = zf.namelist()
                    self.assertTrue(any(name.endswith("/plugin.json") for name in names))
                    self.assertTrue(any(name.endswith("/plugin.py") for name in names))
                finally:
                    try:
                        out_zip.unlink(missing_ok=True)
                    except Exception:
                        pass
        finally:
            shutil.rmtree(tmp_plugins, ignore_errors=True)

    def test_install_plugin_archive_imports_zip(self) -> None:
        tmp_root = ROOT / "tests_tmp"
        src_plugins = tmp_root / f"plugins_install_src_{time.time_ns()}"
        dst_plugins = tmp_root / f"plugins_install_dst_{time.time_ns()}"
        src_plugins.mkdir(parents=True, exist_ok=True)
        dst_plugins.mkdir(parents=True, exist_ok=True)
        window = _PluginTestWindow()
        zip_path = tmp_root / f"install_me_{time.time_ns()}.zip"
        try:
            with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=src_plugins):
                src_host = PluginHost(window)
                src_host.scaffold_plugin(plugin_id="install_me", name="Install Me", permissions={"menu"})
                src_host.export_plugin("install_me", zip_path)
            with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=dst_plugins):
                dst_host = PluginHost(window)
                installed = dst_host.install_plugin_archive(zip_path)
                self.assertTrue((installed / "plugin.json").exists())
                self.assertTrue((installed / "plugin.py").exists())
        finally:
            shutil.rmtree(src_plugins, ignore_errors=True)
            shutil.rmtree(dst_plugins, ignore_errors=True)
            try:
                zip_path.unlink(missing_ok=True)
            except Exception:
                pass

    def test_inspect_plugin_archive_reports_metadata(self) -> None:
        tmp_root = ROOT / "tests_tmp"
        src_plugins = tmp_root / f"plugins_inspect_src_{time.time_ns()}"
        src_plugins.mkdir(parents=True, exist_ok=True)
        window = _PluginTestWindow()
        zip_path = tmp_root / f"inspect_me_{time.time_ns()}.zip"
        try:
            with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=src_plugins):
                host = PluginHost(window)
                host.scaffold_plugin(plugin_id="inspect_me", name="Inspect Me", permissions={"menu"})
                host.export_plugin("inspect_me", zip_path)
                info = host.inspect_plugin_archive(zip_path)
                self.assertEqual(info.get("plugin_id"), "inspect_me")
                self.assertIn("requested_permissions", info)
                self.assertIn("issues", info)
        finally:
            shutil.rmtree(src_plugins, ignore_errors=True)
            try:
                zip_path.unlink(missing_ok=True)
            except Exception:
                pass


class PluginCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_incompatible_plugin_is_discovered_but_not_loaded(self) -> None:
        tmp_root = ROOT / "tests_tmp"
        tmp_plugins = tmp_root / f"plugins_compat_{time.time_ns()}"
        tmp_plugins.mkdir(parents=True, exist_ok=True)
        bad = tmp_plugins / "compat_bad"
        bad.mkdir(parents=True, exist_ok=True)
        (bad / "plugin.json").write_text(
            (
                '{\n'
                '  "id": "compat_bad",\n'
                '  "name": "Compat Bad",\n'
                '  "version": "1.0.0",\n'
                '  "min_app_version": "999.0.0",\n'
                '  "permissions": ["menu"]\n'
                '}\n'
            ),
            encoding="utf-8",
        )
        (bad / "plugin.py").write_text(
            "class Plugin:\n"
            "    def __init__(self, api) -> None:\n"
            "        self.api = api\n",
            encoding="utf-8",
        )
        window = _PluginTestWindow()
        try:
            with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=tmp_plugins):
                host = PluginHost(window)
                found = host.discover()
                rec = next((x for x in found if x.plugin_id == "compat_bad"), None)
                self.assertIsNotNone(rec)
                assert rec is not None
                self.assertTrue(bool(rec.compatibility_issues))
                window.settings["enabled_plugins"] = ["compat_bad"]
                window.settings["trusted_plugin_hashes"] = {"compat_bad": rec.digest.lower()}
                host.reload()
                runtime = next((x for x in host.records if x.plugin_id == "compat_bad"), None)
                self.assertIsNotNone(runtime)
                assert runtime is not None
                self.assertIsNone(runtime.instance)
        finally:
            shutil.rmtree(tmp_plugins, ignore_errors=True)

    def test_incompatible_plugin_api_version_is_blocked(self) -> None:
        tmp_root = ROOT / "tests_tmp"
        tmp_plugins = tmp_root / f"plugins_api_compat_{time.time_ns()}"
        tmp_plugins.mkdir(parents=True, exist_ok=True)
        bad = tmp_plugins / "api_bad"
        bad.mkdir(parents=True, exist_ok=True)
        (bad / "plugin.json").write_text(
            (
                '{\n'
                '  "id": "api_bad",\n'
                '  "name": "API Bad",\n'
                '  "version": "1.0.0",\n'
                '  "plugin_api_version": "9.0",\n'
                '  "permissions": ["menu"]\n'
                '}\n'
            ),
            encoding="utf-8",
        )
        (bad / "plugin.py").write_text(
            "class Plugin:\n"
            "    def __init__(self, api) -> None:\n"
            "        self.api = api\n",
            encoding="utf-8",
        )
        window = _PluginTestWindow()
        try:
            with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=tmp_plugins):
                host = PluginHost(window)
                rec = next((x for x in host.discover() if x.plugin_id == "api_bad"), None)
                self.assertIsNotNone(rec)
                assert rec is not None
                self.assertTrue(any("plugin API version" in msg for msg in rec.compatibility_issues))
        finally:
            shutil.rmtree(tmp_plugins, ignore_errors=True)


class PluginSchemaAndMetricsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_settings_schema_defaults_and_coercion(self) -> None:
        tmp_root = ROOT / "tests_tmp"
        tmp_plugins = tmp_root / f"plugins_schema_{time.time_ns()}"
        tmp_plugins.mkdir(parents=True, exist_ok=True)
        pl = tmp_plugins / "schema_demo"
        pl.mkdir(parents=True, exist_ok=True)
        (pl / "plugin.json").write_text(
            (
                '{\n'
                '  "id": "schema_demo",\n'
                '  "name": "Schema Demo",\n'
                '  "version": "1.0.0",\n'
                '  "plugin_api_version": "1.0",\n'
                '  "settings_schema": {\n'
                '    "max_items": {"type":"int","default":5,"min":1,"max":10},\n'
                '    "enabled": {"type":"bool","default":true}\n'
                '  },\n'
                '  "permissions": ["menu"]\n'
                '}\n'
            ),
            encoding="utf-8",
        )
        (pl / "plugin.py").write_text(
            "class Plugin:\n"
            "    def __init__(self, api) -> None:\n"
            "        self.api = api\n",
            encoding="utf-8",
        )
        window = _PluginTestWindow()
        try:
            with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=tmp_plugins):
                host = PluginHost(window)
                rec = next((x for x in host.discover() if x.plugin_id == "schema_demo"), None)
                assert rec is not None
                host._apply_plugin_settings_schema(rec)
                cfg = window.settings.get("plugin_config", {}).get("schema_demo", {})
                self.assertEqual(cfg.get("max_items"), 5)
                self.assertEqual(cfg.get("enabled"), True)
                host.set_plugin_config("schema_demo", "max_items", 99)
                cfg = window.settings.get("plugin_config", {}).get("schema_demo", {})
                self.assertEqual(cfg.get("max_items"), 10)
        finally:
            shutil.rmtree(tmp_plugins, ignore_errors=True)

    def test_runtime_event_bus_records_entries(self) -> None:
        window = _PluginTestWindow()
        with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=(ROOT / "plugins")):
            host = PluginHost(window)
            host.record_runtime_event("demo", "metric", {"n": 1})
            self.assertGreaterEqual(len(host.runtime_event_log), 1)
            self.assertEqual(host.runtime_event_log[-1].get("plugin_id"), "demo")

    def test_dependency_ordering_prefers_dependencies_first(self) -> None:
        window = _PluginTestWindow()
        with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=(ROOT / "plugins")):
            host = PluginHost(window)
            a = PluginRecord("a", "a", "", {"menu"}, ROOT, True, "x")
            b = PluginRecord("b", "b", "", {"menu"}, ROOT, True, "x", dependencies=["a"])
            c = PluginRecord("c", "c", "", {"menu"}, ROOT, True, "x", dependencies=["b"])
            ordered = host._build_load_order([c, b, a])
            self.assertEqual([r.plugin_id for r in ordered], ["a", "b", "c"])

    def test_service_contract_requires_declared_reference(self) -> None:
        window = _PluginTestWindow()
        with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=(ROOT / "plugins")):
            host = PluginHost(window)
            provider = PluginRecord("provider", "provider", "", {"menu"}, ROOT, True, "x", provided_services={"svc"})
            consumer = PluginRecord("consumer", "consumer", "", {"menu"}, ROOT, True, "x", required_services={"provider:svc"})
            host.records = [provider, consumer]
            host.register_plugin_service("provider", "svc", {"ok": True})
            self.assertEqual(host.resolve_plugin_service(consumer, "provider:svc"), {"ok": True})
            with self.assertRaises(RuntimeError):
                host.resolve_plugin_service(consumer, "provider:other")

    def test_command_registry_run_and_list(self) -> None:
        window = _PluginTestWindow()
        with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=(ROOT / "plugins")):
            host = PluginHost(window)
            host.register_plugin_command(
                "alpha",
                "ping",
                lambda args: f"pong:{args.get('x', '')}",
                description="Ping command",
                args_schema={"x": {"type": "str"}},
            )
            cmds = host.list_plugin_commands("alpha")
            self.assertEqual(len(cmds), 1)
            self.assertEqual(cmds[0]["name"], "ping")
            out = host.run_plugin_command("alpha", "ping", {"x": "42"})
            self.assertEqual(out, "pong:42")

    def test_register_command_creates_plugin_action_for_palette_discovery(self) -> None:
        window = _PluginTestWindow()
        with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=(ROOT / "plugins")):
            host = PluginHost(window)
            rec = PluginRecord("alpha", "Alpha", "", {"menu"}, ROOT, True, "x")
            host.records = [rec]
            host.register_plugin_command("alpha", "ping", lambda _args: "ok", description="Ping")
            self.assertTrue(any(a.objectName() == "plugincmd:alpha:ping" for a in rec.actions))

    def test_job_lifecycle_status_and_cancel(self) -> None:
        window = _PluginTestWindow()
        with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=(ROOT / "plugins")):
            host = PluginHost(window)
            stop_event = threading.Event()

            def _job(ctx):
                ctx["report_progress"](0.25)
                # Wait briefly to allow cancel request in test.
                stop_event.wait(0.2)
                if ctx["should_stop"]():
                    return
                ctx["report_progress"](1.0)

            job_id = host.start_plugin_job("alpha", "demo", _job)
            status = host.plugin_job_status("alpha", job_id)
            self.assertIn(status.get("status"), {"running", "cancelling", "completed", "cancelled"})
            self.assertTrue(host.cancel_plugin_job("alpha", job_id))
            stop_event.set()
            time.sleep(0.1)
            final_status = host.plugin_job_status("alpha", job_id)
            self.assertIn(final_status.get("status"), {"cancelled", "completed", "cancelling"})

    def test_plugin_logs_record_and_retrieve(self) -> None:
        window = _PluginTestWindow()
        with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=(ROOT / "plugins")):
            host = PluginHost(window)
            host.record_plugin_log("alpha", "info", "hello")
            logs = host.plugin_logs("alpha")
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0]["level"], "INFO")
            self.assertEqual(logs[0]["message"], "hello")

    def test_failure_counter_record_and_reset(self) -> None:
        window = _PluginTestWindow()
        with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=(ROOT / "plugins")):
            host = PluginHost(window)
            count = host._record_plugin_failure("alpha", "boom")
            self.assertEqual(count, 1)
            self.assertEqual(host._failure_counts().get("alpha"), 1)
            host.reset_plugin_failure_count("alpha")
            self.assertNotIn("alpha", host._failure_counts())

    def test_health_score_reflects_failures(self) -> None:
        window = _PluginTestWindow()
        with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=(ROOT / "plugins")):
            host = PluginHost(window)
            rec = PluginRecord("alpha", "Alpha", "", {"menu"}, ROOT, True, "x")
            baseline = host.plugin_health_score(rec)
            rec.failure_count = 3
            degraded = host.plugin_health_score(rec)
            self.assertGreater(baseline, degraded)

    def test_check_plugin_update_from_file_url(self) -> None:
        tmp_root = ROOT / "tests_tmp"
        tmp_meta = tmp_root / f"plugin_update_{time.time_ns()}.json"
        tmp_meta.write_text(json.dumps({"version": "9.9.9"}), encoding="utf-8")
        window = _PluginTestWindow()
        with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=(ROOT / "plugins")):
            host = PluginHost(window)
            rec = PluginRecord("alpha", "Alpha", "", {"menu"}, ROOT, True, "x")
            rec.metadata = {"version": "1.0.0", "update_url": tmp_meta.as_uri()}
            info = host.check_plugin_update(rec)
            self.assertEqual(info.get("latest_version"), "9.9.9")
            self.assertTrue(bool(info.get("update_available")))
        try:
            tmp_meta.unlink(missing_ok=True)
        except Exception:
            pass

    def test_check_all_plugin_updates_returns_rows(self) -> None:
        window = _PluginTestWindow()
        with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=(ROOT / "plugins")):
            host = PluginHost(window)
            rows = host.check_all_plugin_updates()
            self.assertGreaterEqual(len(rows), 1)
            self.assertIn("plugin_id", rows[0])
            self.assertIn("update_available", rows[0])

    def test_plugin_diagnostics_snapshot_contains_core_fields(self) -> None:
        window = _PluginTestWindow()
        with patch("pypad.ui.features.advanced_features.get_plugins_dir_path", return_value=(ROOT / "plugins")):
            host = PluginHost(window)
            rec = PluginRecord("alpha", "Alpha", "", {"menu"}, ROOT, True, "x")
            snap = host.plugin_diagnostics_snapshot(rec)
            self.assertEqual(snap["plugin_id"], "alpha")
            self.assertIn("health_score", snap)
            self.assertIn("logs", snap)


if __name__ == "__main__":
    unittest.main()
