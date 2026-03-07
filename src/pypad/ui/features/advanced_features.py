from __future__ import annotations

import ast
import hashlib
import hmac
import json
import keyword
import queue
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse, unquote
from urllib.request import urlopen

from PySide6.QtCore import QSize, QTimer, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QSplitter,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from pypad.app_settings.paths import get_plugins_dir_path
from pypad.ui.features.extensibility_ops import assess_plugin_security, discover_window_actions
from pypad.ui.editor.editor_tab import EditorTab
from pypad.ui.workspace.project_workflow import (
    apply_unified_patch_to_text,
    build_unified_diff_text,
    diff_stats_from_patch,
)
from pypad.ui.theme.theme_tokens import build_tokens_from_settings

PLUGIN_API_VERSION = "1.0"


def _root() -> Path:
    # src/pypad/ui/features/advanced_features.py -> repo root at parents[4]
    return Path(__file__).resolve().parents[4]


def _read_app_version() -> str:
    version_file = _root() / "assets" / "version.txt"
    try:
        return str(version_file.read_text(encoding="utf-8").strip() or "0.0.0")
    except Exception:
        return "0.0.0"


def _parse_version_tuple(value: str) -> tuple[int, int, int]:
    text = str(value or "").strip().lower().lstrip("v")
    nums = [int(x) for x in re.findall(r"\d+", text)]
    while len(nums) < 3:
        nums.append(0)
    return nums[0], nums[1], nums[2]


def _is_version_compatible(app_version: str, min_version: str, max_version: str) -> bool:
    app_v = _parse_version_tuple(app_version)
    if str(min_version or "").strip():
        if app_v < _parse_version_tuple(min_version):
            return False
    if str(max_version or "").strip():
        if app_v > _parse_version_tuple(max_version):
            return False
    return True


def _parse_api_version(value: str) -> tuple[int, int]:
    text = str(value or "").strip().lower().lstrip("v")
    nums = [int(x) for x in re.findall(r"\d+", text)]
    while len(nums) < 2:
        nums.append(0)
    return nums[0], nums[1]


def _is_plugin_api_compatible(plugin_api_version: str, supported_api_version: str) -> bool:
    plugin_major, plugin_minor = _parse_api_version(plugin_api_version)
    supported_major, supported_minor = _parse_api_version(supported_api_version)
    if plugin_major != supported_major:
        return False
    return plugin_minor <= supported_minor


@dataclass
class PluginRecord:
    plugin_id: str
    name: str
    description: str
    permissions: set[str]
    path: Path
    enabled: bool
    digest: str
    requested_permissions: set[str] = field(default_factory=set)
    quarantined: bool = False
    security_issues: list[str] = field(default_factory=list)
    compatibility_issues: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    settings_schema: dict[str, dict[str, Any]] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    provided_services: set[str] = field(default_factory=set)
    required_services: set[str] = field(default_factory=set)
    command_specs: dict[str, dict[str, Any]] = field(default_factory=dict)
    instance: Any = None
    actions: list[QAction] = field(default_factory=list)
    toolbars: list[QToolBar] = field(default_factory=list)
    panels: list[QDockWidget] = field(default_factory=list)
    timers: list[QTimer] = field(default_factory=list)
    hook_counts: dict[str, int] = field(default_factory=dict)
    load_count: int = 0
    last_run_at: str = ""
    last_event_at: str = ""
    last_error_at: str = ""
    last_error: str = ""
    runtime_events: list[dict[str, Any]] = field(default_factory=list)
    failure_count: int = 0


def compute_plugin_digest(plugin_dir: Path) -> str:
    hasher = hashlib.sha256()
    for rel in ("plugin.json", "plugin.py"):
        path = plugin_dir / rel
        if not path.exists():
            continue
        hasher.update(rel.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def apply_text_operations(text: str, operations: list[dict[str, Any]]) -> str:
    out = text
    for op in operations:
        kind = str(op.get("op", "")).strip().lower()
        if kind == "insert":
            index = int(op.get("index", -1))
            payload = str(op.get("text", ""))
            if index < 0 or index > len(out):
                raise ValueError("insert index out of bounds")
            out = out[:index] + payload + out[index:]
            continue
        if kind in {"delete", "replace"}:
            start = int(op.get("start", -1))
            end = int(op.get("end", -1))
            if start < 0 or end < start or end > len(out):
                raise ValueError(f"{kind} range out of bounds")
            replacement = str(op.get("text", "")) if kind == "replace" else ""
            out = out[:start] + replacement + out[end:]
            continue
        raise ValueError(f"unsupported operation: {kind}")
    return out


class PluginAPI:
    def __init__(self, window, record: PluginRecord) -> None:
        self.window = window
        self.record = record

    def _allow(self, perm: str) -> None:
        if perm not in self.record.permissions:
            raise RuntimeError(f"Plugin '{self.record.plugin_id}' missing permission: {perm}")

    def _allow_any(self, perms: set[str]) -> None:
        if not (self.record.permissions & perms):
            raise RuntimeError(f"Plugin '{self.record.plugin_id}' missing permission: {', '.join(sorted(perms))}")

    def notify(self, text: str) -> None:
        self.window.show_status_message(f"[Plugin:{self.record.name}] {text}", 3000)

    def _host(self):
        controller = getattr(self.window, "advanced_features", None)
        return getattr(controller, "plugin_host", None)

    def _record_runtime(self, event: str, payload: dict[str, Any] | None = None) -> None:
        host = self._host()
        if host is not None and hasattr(host, "record_runtime_event"):
            host.record_runtime_event(self.record.plugin_id, event, payload or {})

    def _allow_unsafe_ui_bridge(self) -> None:
        enabled = bool(self.window.settings.get("plugin_allow_unsafe_ui_bridge", False))
        if not enabled:
            raise RuntimeError(
                "Unsafe UI bridge is disabled. Use controller API methods instead "
                "(enable 'plugin_allow_unsafe_ui_bridge' only if you fully trust the plugin)."
            )

    def app_window(self):
        self._allow("ui")
        self._allow_unsafe_ui_bridge()
        return self.window

    def active_tab(self):
        self._allow("ui")
        self._allow_unsafe_ui_bridge()
        return self.window.active_tab()

    def app_info(self) -> dict[str, Any]:
        return {
            "app_name": "Pypad",
            "plugin_id": self.record.plugin_id,
            "plugin_name": self.record.name,
            "permissions": sorted(self.record.permissions),
        }

    def show_status(self, text: str, timeout_ms: int = 3000) -> None:
        self.window.show_status_message(f"[Plugin:{self.record.name}] {text}", max(500, int(timeout_ms)))

    def plugin_state_get(self, key: str, default: Any = None) -> Any:
        state = self.window.settings.get("plugin_state", {})
        if not isinstance(state, dict):
            return default
        plugin_state = state.get(self.record.plugin_id, {})
        if not isinstance(plugin_state, dict):
            return default
        return plugin_state.get(str(key), default)

    def plugin_state_set(self, key: str, value: Any) -> None:
        text_key = str(key).strip()
        if not text_key:
            raise ValueError("state key cannot be empty")
        state = self.window.settings.get("plugin_state")
        if not isinstance(state, dict):
            state = {}
            self.window.settings["plugin_state"] = state
        plugin_state = state.get(self.record.plugin_id)
        if not isinstance(plugin_state, dict):
            plugin_state = {}
            state[self.record.plugin_id] = plugin_state
        plugin_state[text_key] = value
        self.window.save_settings_to_disk()

    def plugin_config_schema(self) -> dict[str, dict[str, Any]]:
        return dict(getattr(self.record, "settings_schema", {}) or {})

    def plugin_config_get(self, key: str, default: Any = None) -> Any:
        cfg = self.window.settings.get("plugin_config", {})
        if not isinstance(cfg, dict):
            return default
        p = cfg.get(self.record.plugin_id, {})
        if not isinstance(p, dict):
            return default
        return p.get(str(key), default)

    def plugin_config_set(self, key: str, value: Any) -> None:
        host = self._host()
        if host is not None and hasattr(host, "set_plugin_config"):
            host.set_plugin_config(self.record.plugin_id, str(key), value)
            return
        cfg = self.window.settings.get("plugin_config")
        if not isinstance(cfg, dict):
            cfg = {}
            self.window.settings["plugin_config"] = cfg
        p = cfg.get(self.record.plugin_id)
        if not isinstance(p, dict):
            p = {}
            cfg[self.record.plugin_id] = p
        p[str(key)] = value
        self.window.save_settings_to_disk()

    def register_service(self, service_name: str, obj: Any) -> None:
        host = self._host()
        if host is None or not hasattr(host, "register_plugin_service"):
            raise RuntimeError("Plugin host service registry unavailable.")
        host.register_plugin_service(self.record.plugin_id, str(service_name), obj)
        self._record_runtime("service_register", {"service": str(service_name)})

    def get_service(self, service_ref: str) -> Any:
        host = self._host()
        if host is None or not hasattr(host, "resolve_plugin_service"):
            raise RuntimeError("Plugin host service registry unavailable.")
        value = host.resolve_plugin_service(self.record, str(service_ref))
        self._record_runtime("service_get", {"service_ref": str(service_ref)})
        return value

    def register_command(
        self,
        command_name: str,
        callback,
        *,
        description: str = "",
        args_schema: dict[str, Any] | None = None,
    ) -> None:
        host = self._host()
        if host is None or not hasattr(host, "register_plugin_command"):
            raise RuntimeError("Plugin host command registry unavailable.")
        host.register_plugin_command(
            self.record.plugin_id,
            str(command_name),
            callback,
            description=str(description or ""),
            args_schema=dict(args_schema or {}),
        )
        self._record_runtime("command_register", {"command": str(command_name)})

    def run_command(self, command_ref: str, args: dict[str, Any] | None = None) -> Any:
        host = self._host()
        if host is None or not hasattr(host, "run_plugin_command"):
            raise RuntimeError("Plugin host command registry unavailable.")
        self._record_runtime("command_run", {"command_ref": str(command_ref)})
        return host.run_plugin_command(self.record.plugin_id, str(command_ref), dict(args or {}))

    def log(self, level: str, message: str) -> None:
        host = self._host()
        lvl = str(level or "INFO").strip().upper() or "INFO"
        msg = str(message or "")
        if host is not None and hasattr(host, "record_plugin_log"):
            host.record_plugin_log(self.record.plugin_id, lvl, msg)
        self.window.log_event(lvl, f"[Plugin:{self.record.plugin_id}] {msg}")

    def start_job(self, job_name: str, fn) -> str:
        self._allow("background")
        host = self._host()
        if host is None or not hasattr(host, "start_plugin_job"):
            raise RuntimeError("Plugin host job runner unavailable.")
        job_id = host.start_plugin_job(self.record.plugin_id, str(job_name), fn)
        self._record_runtime("job_start", {"job_id": job_id, "job_name": str(job_name)})
        return job_id

    def cancel_job(self, job_id: str) -> bool:
        self._allow("background")
        host = self._host()
        if host is None or not hasattr(host, "cancel_plugin_job"):
            raise RuntimeError("Plugin host job runner unavailable.")
        ok = bool(host.cancel_plugin_job(self.record.plugin_id, str(job_id)))
        self._record_runtime("job_cancel", {"job_id": str(job_id), "ok": ok})
        return ok

    def job_status(self, job_id: str) -> dict[str, Any]:
        self._allow("background")
        host = self._host()
        if host is None or not hasattr(host, "plugin_job_status"):
            raise RuntimeError("Plugin host job runner unavailable.")
        return dict(host.plugin_job_status(self.record.plugin_id, str(job_id)))

    def log_metric(self, event: str, detail: str = "") -> None:
        host = self._host()
        if host is None or not hasattr(host, "record_runtime_event"):
            return
        host.record_runtime_event(self.record.plugin_id, str(event or "metric"), {"detail": str(detail or "")})

    def emit_runtime_event(self, event: str, payload: dict[str, Any] | None = None) -> None:
        host = self._host()
        if host is None or not hasattr(host, "publish_runtime_event"):
            return
        host.publish_runtime_event(self.record.plugin_id, str(event or "event"), dict(payload or {}))

    def tab_count(self) -> int:
        return int(self.window.tab_widget.count())

    def active_tab_index(self) -> int:
        return int(self.window.tab_widget.currentIndex())

    def active_tab_info(self) -> dict[str, Any]:
        tab = self.window.active_tab()
        if tab is None:
            return {
                "index": -1,
                "title": "",
                "path": "",
                "read_only": False,
                "modified": False,
            }
        index = int(self.window.tab_widget.currentIndex())
        title = str(self.window._tab_display_name(tab))
        path = str(getattr(tab, "current_file", "") or "")
        editor = getattr(tab, "text_edit", None)
        read_only = bool(editor.is_read_only()) if editor is not None and hasattr(editor, "is_read_only") else False
        modified = bool(tab.text_edit.is_modified()) if editor is not None and hasattr(editor, "is_modified") else False
        return {
            "index": index,
            "title": title,
            "path": path,
            "read_only": read_only,
            "modified": modified,
        }

    def switch_to_tab(self, index: int) -> bool:
        idx = int(index)
        if idx < 0 or idx >= self.window.tab_widget.count():
            return False
        self.window.tab_widget.setCurrentIndex(idx)
        return True

    def file_new(self, text: str = "") -> bool:
        self._allow("file")
        if not hasattr(self.window, "file_new"):
            return False
        self.window.file_new()
        if text:
            self.replace_text(str(text))
        return True

    def close_tab(self, index: int | None = None) -> bool:
        self._allow("file")
        idx = self.window.tab_widget.currentIndex() if index is None else int(index)
        if idx < 0 or idx >= self.window.tab_widget.count():
            return False
        if hasattr(self.window, "close_tab"):
            self.window.close_tab(idx)
            return True
        return False

    def workspace_root(self) -> str:
        ctrl = getattr(self.window, "workspace_controller", None)
        if ctrl is None:
            return ""
        root = ctrl.workspace_root()
        return str(root or "")

    def workspace_files(self) -> list[str]:
        self._allow("file")
        ctrl = getattr(self.window, "workspace_controller", None)
        if ctrl is None:
            return []
        return list(ctrl.workspace_files())

    def refresh_workspace_index(self) -> None:
        self._allow("file")
        ctrl = getattr(self.window, "workspace_controller", None)
        if ctrl is None:
            return
        if hasattr(ctrl, "_start_background_scan"):
            ctrl._start_background_scan(force=True)

    def workspace_index_status(self) -> dict[str, Any]:
        self._allow("file")
        ctrl = getattr(self.window, "workspace_controller", None)
        if ctrl is None:
            return {"ready": False, "scanning": False, "count": 0, "root": ""}
        return {
            "ready": bool(getattr(ctrl, "_index_ready", False)),
            "scanning": bool(getattr(ctrl, "_index_scanning", False)),
            "count": len(getattr(ctrl, "_index_files", []) or []),
            "root": self.workspace_root(),
        }

    def current_text(self) -> str:
        tab = self.window.active_tab()
        return tab.text_edit.get_text() if tab is not None else ""

    def selection_text(self) -> str:
        tab = self.window.active_tab()
        return tab.text_edit.selected_text() if tab is not None else ""

    def selection_range(self):
        tab = self.window.active_tab()
        return tab.text_edit.selection_range() if tab is not None else None

    def open_tabs(self) -> list[dict[str, str]]:
        tabs = []
        for i in range(self.window.tab_widget.count()):
            tab = self.window.tab_widget.widget(i)
            if not isinstance(tab, EditorTab):
                continue
            tabs.append(
                {
                    "title": self.window._tab_display_name(tab),
                    "path": tab.current_file or "",
                }
            )
        return tabs

    def list_actions(self) -> list[dict[str, str]]:
        self._allow_any({"ui", "menu"})
        return [
            {
                "action_id": item.action_id,
                "label": item.label,
                "section": item.section,
                "shortcut": item.shortcut_text,
            }
            for item in discover_window_actions(self.window)
        ]

    def trigger_action(self, action_id: str) -> bool:
        self._allow_any({"ui", "menu"})
        target_id = str(action_id or "").strip()
        if not target_id:
            return False
        for item in discover_window_actions(self.window):
            if item.action_id == target_id:
                item.action.trigger()
                return True
        return False

    def open_file(self, path: str) -> bool:
        self._allow("file")
        if hasattr(self.window, "_open_file_path"):
            return bool(self.window._open_file_path(path))
        return False

    def save_active(self) -> bool:
        self._allow("file")
        if hasattr(self.window, "file_save"):
            return bool(self.window.file_save())
        return False

    def replace_text(self, text: str) -> None:
        self._allow("file")
        tab = self.window.active_tab()
        if tab is None or tab.text_edit.is_read_only():
            return
        tab.text_edit.set_text(text)
        tab.text_edit.set_modified(True)

    def insert_text(self, text: str) -> None:
        self._allow("file")
        tab = self.window.active_tab()
        if tab is None or tab.text_edit.is_read_only():
            return
        tab.text_edit.insert_text(text)

    def replace_selection(self, text: str) -> None:
        self._allow("file")
        tab = self.window.active_tab()
        if tab is None or tab.text_edit.is_read_only():
            return
        if tab.text_edit.has_selection():
            tab.text_edit.replace_selection(text)
        else:
            tab.text_edit.insert_text(text)

    def ask_ai(self, prompt: str) -> None:
        self._allow("ai")
        self.window.ai_controller._start_generation(prompt, "Plugin AI", action_name=f"plugin:{self.record.plugin_id}")

    def network_allowed(self) -> bool:
        self._allow("network")
        return True

    def run_background(self, fn, *, name: str | None = None) -> None:
        self._allow("background")
        thread = threading.Thread(target=fn, name=name or f"plugin-{self.record.plugin_id}", daemon=True)
        thread.start()

    def start_timer(self, interval_ms: int, fn) -> QTimer:
        self._allow("background")
        timer = QTimer(self.window)
        timer.setInterval(max(10, int(interval_ms)))
        timer.timeout.connect(fn)
        timer.start()
        self.record.timers.append(timer)
        return timer

    def add_menu_action(self, menu_path: str, label: str, callback, shortcut: str | None = None) -> QAction:
        self._allow_any({"menu", "ui"})
        menu = self._resolve_menu_path(menu_path)
        action = QAction(label, self.window)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(callback)
        menu.addAction(action)
        self.record.actions.append(action)
        return action

    def add_toolbar_action(self, toolbar_name: str, label: str, callback, shortcut: str | None = None) -> QAction:
        self._allow_any({"toolbar", "ui"})
        toolbar = self._resolve_toolbar(toolbar_name)
        action = QAction(label, self.window)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(callback)
        toolbar.addAction(action)
        self.record.actions.append(action)
        if toolbar not in self.record.toolbars:
            self.record.toolbars.append(toolbar)
        return action

    def add_panel(self, title: str, widget: QWidget, area: Qt.DockWidgetArea = Qt.RightDockWidgetArea) -> QDockWidget:
        self._allow_any({"panel", "ui"})
        dock = QDockWidget(title, self.window)
        dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        dock.setWidget(widget)
        dock.setObjectName(f"plugin:{self.record.plugin_id}:{title}")
        self.window.addDockWidget(area, dock)
        self.record.panels.append(dock)
        dock.show()
        return dock

    def _resolve_toolbar(self, toolbar_name: str) -> QToolBar:
        name = (toolbar_name or "main").strip().lower()
        if name in {"main", "main_toolbar"} and hasattr(self.window, "main_toolbar"):
            return self.window.main_toolbar
        if name in {"markdown", "markdown_toolbar"} and hasattr(self.window, "markdown_toolbar"):
            return self.window.markdown_toolbar
        if name in {"search", "search_toolbar"} and hasattr(self.window, "search_toolbar"):
            return self.window.search_toolbar
        tb = QToolBar(toolbar_name or "Plugin", self.window)
        tb.setObjectName(f"pluginToolbar:{self.record.plugin_id}:{toolbar_name or 'Plugin'}")
        tb.setMovable(True)
        tb.setFloatable(True)
        self.window.addToolBar(tb)
        return tb

    def _resolve_menu_path(self, menu_path: str):
        parts = [p for p in (menu_path or "Plugins").split("/") if p.strip()]
        root_name = parts[0] if parts else "Plugins"
        menu = getattr(self.window, "plugins_menu", None)
        if menu is None:
            menu = self.window.menuBar().addMenu("&Plugins")
            self.window.plugins_menu = menu
        if root_name.lower() != "plugins":
            menu = menu.addMenu(root_name)
        for part in parts[1:]:
            menu = menu.addMenu(part)
        return menu


class PluginHost:
    def __init__(self, window) -> None:
        self.window = window
        self.app_version = _read_app_version()
        self.plugins_dir = self._resolve_plugins_dir()
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self._install_example_plugins_if_missing()
        self.records: list[PluginRecord] = []
        self.runtime_event_log: list[dict[str, Any]] = []
        self._service_registry: dict[str, dict[str, Any]] = {}
        self._command_registry: dict[str, dict[str, dict[str, Any]]] = {}
        self._job_registry: dict[str, dict[str, dict[str, Any]]] = {}
        self._plugin_logs: dict[str, list[dict[str, Any]]] = {}
        self._startup_plugins_loaded = False
        defer_load = bool(self.window.settings.get("defer_plugin_load_on_startup", True))
        delay_ms = int(self.window.settings.get("plugin_startup_defer_ms", 1200) or 0)
        if defer_load:
            QTimer.singleShot(max(0, delay_ms), self._load_startup_plugins)
        else:
            self._load_startup_plugins()

    def _resolve_plugins_dir(self) -> Path:
        # Dev-exclusive override: allow loading directly from repo ../plugins folder.
        if not getattr(sys, "frozen", False):
            if bool(self.window.settings.get("plugin_dev_use_repo_plugins", False)):
                return _root() / "plugins"
        return get_plugins_dir_path()

    def set_dev_plugins_source(self, use_repo_plugins: bool) -> None:
        if getattr(sys, "frozen", False):
            return
        self.window.settings["plugin_dev_use_repo_plugins"] = bool(use_repo_plugins)
        self.window.save_settings_to_disk()
        self.plugins_dir = self._resolve_plugins_dir()
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.reload()

    def _load_startup_plugins(self) -> None:
        if self._startup_plugins_loaded:
            return
        self._startup_plugins_loaded = True
        self.reload(startup=True)

    def _packaged_plugins_dir(self) -> Path:
        if getattr(sys, "frozen", False):
            meipass = Path(str(getattr(sys, "_MEIPASS", "")))
            if meipass:
                bundled = meipass / "plugins"
                if bundled.exists():
                    return bundled
        return _root() / "plugins"

    def runtime_mode_label(self) -> str:
        return "production" if getattr(sys, "frozen", False) else "development"

    def _install_example_plugins_if_missing(self) -> None:
        source_root = self._packaged_plugins_dir()
        if not source_root.exists():
            return
        for name in ("example_word_tools", "example_hello_network", "example_workspace_inspector"):
            src_dir = source_root / name
            if not src_dir.exists() or not src_dir.is_dir():
                continue
            if not (src_dir / "plugin.json").exists() or not (src_dir / "plugin.py").exists():
                continue
            dst_dir = self.plugins_dir / name
            try:
                if not dst_dir.exists():
                    shutil.copytree(src_dir, dst_dir)
                    continue
                # Repair partial/corrupted plugin dirs (e.g. only __pycache__ present).
                for rel in ("plugin.json", "plugin.py"):
                    src_file = src_dir / rel
                    dst_file = dst_dir / rel
                    if not dst_file.exists():
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dst_file)
            except Exception as exc:  # noqa: BLE001
                self.window.log_event("Error", f"Could not install bundled example plugin {name}: {exc}")

    def _enabled(self) -> set[str]:
        return {str(x) for x in self.window.settings.get("enabled_plugins", []) if isinstance(x, str)}

    def _save_enabled(self, ids: set[str]) -> None:
        self.window.settings["enabled_plugins"] = sorted(ids)
        self.window.save_settings_to_disk()

    def _trusted_hashes(self) -> dict[str, str]:
        raw = self.window.settings.get("trusted_plugin_hashes", {})
        if not isinstance(raw, dict):
            return {}
        out: dict[str, str] = {}
        for key, value in raw.items():
            k = str(key).strip()
            v = str(value).strip().lower()
            if k and v:
                out[k] = v
        return out

    def _save_trusted_hashes(self, mapping: dict[str, str]) -> None:
        self.window.settings["trusted_plugin_hashes"] = dict(sorted(mapping.items()))
        self.window.save_settings_to_disk()

    def _quarantined(self) -> set[str]:
        raw = self.window.settings.get("quarantined_plugins", [])
        return {str(x).strip() for x in raw if str(x).strip()}

    def _save_quarantined(self, ids: set[str]) -> None:
        self.window.settings["quarantined_plugins"] = sorted(ids)
        self.window.save_settings_to_disk()

    def _is_startup_safe_mode(self) -> bool:
        return bool(self.window.settings.get("plugin_startup_safe_mode", False))

    def _failure_counts(self) -> dict[str, int]:
        raw = self.window.settings.get("plugin_failure_counts", {})
        if not isinstance(raw, dict):
            return {}
        out: dict[str, int] = {}
        for key, value in raw.items():
            pid = str(key).strip()
            if not pid:
                continue
            try:
                out[pid] = max(0, int(value))
            except Exception:
                continue
        return out

    def _save_failure_counts(self, mapping: dict[str, int]) -> None:
        serial = {k: int(v) for k, v in sorted(mapping.items()) if int(v) > 0}
        self.window.settings["plugin_failure_counts"] = serial
        self.window.save_settings_to_disk()

    def _max_failures_before_disable(self) -> int:
        try:
            value = int(self.window.settings.get("plugin_max_failures_before_disable", 3) or 3)
        except Exception:
            value = 3
        return max(1, min(20, value))

    def plugin_health_score(self, rec: PluginRecord) -> int:
        score = 100
        score -= min(60, int(rec.failure_count) * 15)
        if rec.last_error:
            score -= 15
        if rec.security_issues:
            score -= 30
        if rec.compatibility_issues:
            score -= 20
        if rec.instance is None and rec.enabled:
            score -= 10
        return max(0, min(100, score))

    def _record_plugin_failure(self, plugin_id: str, reason: str) -> int:
        counts = self._failure_counts()
        counts[plugin_id] = int(counts.get(plugin_id, 0) or 0) + 1
        self._save_failure_counts(counts)
        self.record_runtime_event(plugin_id, "failure", {"count": counts[plugin_id], "reason": str(reason or "")})
        return counts[plugin_id]

    def _clear_plugin_failure(self, plugin_id: str) -> None:
        counts = self._failure_counts()
        if plugin_id in counts:
            counts.pop(plugin_id, None)
            self._save_failure_counts(counts)

    def reset_plugin_failure_count(self, plugin_id: str) -> None:
        self._clear_plugin_failure(plugin_id)

    def _trust_prompt(self, rec: PluginRecord) -> bool:
        box = QMessageBox(self.window)
        box.setWindowTitle("Trust Plugin")
        box.setIcon(QMessageBox.Warning)
        box.setText(f"Plugin '{rec.name}' is not trusted yet.")
        box.setInformativeText("Trust this plugin hash and allow it to load?")
        box.setDetailedText(f"Plugin ID: {rec.plugin_id}\nDigest (SHA256): {rec.digest}")
        trust_btn = box.addButton("Trust and Load", QMessageBox.AcceptRole)
        box.addButton("Cancel", QMessageBox.RejectRole)
        box.exec()
        return box.clickedButton() == trust_btn

    def _is_plugin_trusted(self, rec: PluginRecord) -> bool:
        trusted = self._trusted_hashes()
        return trusted.get(rec.plugin_id, "").strip().lower() == rec.digest.lower()

    def _mark_trusted(self, rec: PluginRecord) -> None:
        trusted = self._trusted_hashes()
        trusted[rec.plugin_id] = rec.digest.lower()
        self._save_trusted_hashes(trusted)

    def _quarantine_plugin(self, rec: PluginRecord, reason: str) -> None:
        quarantined = self._quarantined()
        quarantined.add(rec.plugin_id)
        self._save_quarantined(quarantined)
        enabled = self._enabled()
        if rec.plugin_id in enabled:
            enabled.discard(rec.plugin_id)
            self._save_enabled(enabled)
        self.window.log_event("Error", f"Plugin quarantined ({rec.plugin_id}): {reason}")

    def _permission_overrides(self) -> dict[str, set[str]]:
        raw = self.window.settings.get("plugin_permission_overrides", {})
        if not isinstance(raw, dict):
            return {}
        out: dict[str, set[str]] = {}
        for key, value in raw.items():
            pid = str(key).strip()
            if not pid:
                continue
            if isinstance(value, (list, tuple, set)):
                perms = {str(p).strip().lower() for p in value if str(p).strip()}
            else:
                perms = {str(value).strip().lower()} if str(value).strip() else set()
            out[pid] = perms
        return out

    def _save_permission_overrides(self, mapping: dict[str, set[str]]) -> None:
        serial: dict[str, list[str]] = {}
        for pid, perms in mapping.items():
            serial[str(pid)] = sorted({str(p).strip().lower() for p in perms if str(p).strip()})
        self.window.settings["plugin_permission_overrides"] = serial
        self.window.save_settings_to_disk()

    def set_permission_override(self, plugin_id: str, allowed: set[str] | None) -> None:
        overrides = self._permission_overrides()
        if allowed is None:
            overrides.pop(plugin_id, None)
        else:
            overrides[plugin_id] = {str(p).strip().lower() for p in allowed if str(p).strip()}
        self._save_permission_overrides(overrides)

    def reset_permission_overrides(self) -> None:
        self.window.settings["plugin_permission_overrides"] = {}
        self.window.save_settings_to_disk()

    def _plugin_config_map(self) -> dict[str, dict[str, Any]]:
        raw = self.window.settings.get("plugin_config", {})
        if isinstance(raw, dict):
            return raw
        self.window.settings["plugin_config"] = {}
        return self.window.settings["plugin_config"]

    def _coerce_schema_value(self, spec: dict[str, Any], value: Any) -> Any:
        typ = str(spec.get("type", "str")).strip().lower()
        if typ in {"int", "integer"}:
            try:
                n = int(value)
            except Exception:
                n = int(spec.get("default", 0) or 0)
            if "min" in spec:
                n = max(int(spec.get("min", n)), n)
            if "max" in spec:
                n = min(int(spec.get("max", n)), n)
            return n
        if typ in {"float", "number"}:
            try:
                n = float(value)
            except Exception:
                n = float(spec.get("default", 0.0) or 0.0)
            if "min" in spec:
                n = max(float(spec.get("min", n)), n)
            if "max" in spec:
                n = min(float(spec.get("max", n)), n)
            return n
        if typ in {"bool", "boolean"}:
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in {"1", "true", "yes", "on"}
        if typ in {"list", "array"}:
            if isinstance(value, list):
                return value
            if isinstance(value, tuple):
                return list(value)
            if isinstance(value, str):
                return [x.strip() for x in value.split(",") if x.strip()]
            return list(spec.get("default", []) or [])
        text = str(value if value is not None else spec.get("default", "") or "")
        enum_vals = spec.get("enum")
        if isinstance(enum_vals, list) and enum_vals:
            enum_text = [str(x) for x in enum_vals]
            if text not in enum_text:
                return str(spec.get("default", enum_text[0]))
        return text

    def _apply_plugin_settings_schema(self, rec: PluginRecord) -> None:
        schema = dict(rec.settings_schema or {})
        if not schema:
            return
        config_map = self._plugin_config_map()
        existing = config_map.get(rec.plugin_id)
        if not isinstance(existing, dict):
            existing = {}
        out: dict[str, Any] = dict(existing)
        changed = False
        for key, spec_raw in schema.items():
            if not isinstance(spec_raw, dict):
                continue
            spec = dict(spec_raw)
            if key not in out:
                out[key] = spec.get("default", "")
                changed = True
            coerced = self._coerce_schema_value(spec, out.get(key))
            if out.get(key) != coerced:
                out[key] = coerced
                changed = True
        config_map[rec.plugin_id] = out
        if changed:
            self.window.settings["plugin_config"] = config_map
            self.window.save_settings_to_disk()

    def set_plugin_config(self, plugin_id: str, key: str, value: Any) -> None:
        rec = next((x for x in self.discover() if x.plugin_id == plugin_id), None)
        schema = rec.settings_schema if rec is not None else {}
        if key in schema:
            value = self._coerce_schema_value(schema[key], value)
        config_map = self._plugin_config_map()
        plugin_cfg = config_map.get(plugin_id)
        if not isinstance(plugin_cfg, dict):
            plugin_cfg = {}
        plugin_cfg[str(key)] = value
        config_map[plugin_id] = plugin_cfg
        self.window.settings["plugin_config"] = config_map
        self.window.save_settings_to_disk()

    def _append_runtime_log(self, item: dict[str, Any]) -> None:
        self.runtime_event_log.append(dict(item))
        if len(self.runtime_event_log) > 500:
            self.runtime_event_log = self.runtime_event_log[-500:]

    def plugin_logs(self, plugin_id: str) -> list[dict[str, Any]]:
        return list(self._plugin_logs.get(str(plugin_id), []))

    def record_plugin_log(self, plugin_id: str, level: str, message: str) -> None:
        pid = str(plugin_id or "").strip()
        if not pid:
            return
        row = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "level": str(level or "INFO").strip().upper() or "INFO",
            "message": str(message or ""),
        }
        items = self._plugin_logs.get(pid)
        if items is None:
            items = []
            self._plugin_logs[pid] = items
        items.append(row)
        if len(items) > 300:
            self._plugin_logs[pid] = items[-300:]

    def register_plugin_service(self, plugin_id: str, service_name: str, obj: Any) -> None:
        pid = str(plugin_id or "").strip()
        name = str(service_name or "").strip()
        if not pid or not name:
            raise ValueError("plugin_id and service_name are required")
        registry = self._service_registry.get(pid)
        if registry is None:
            registry = {}
            self._service_registry[pid] = registry
        registry[name] = obj

    def resolve_plugin_service(self, requester: PluginRecord, service_ref: str) -> Any:
        ref = str(service_ref or "").strip()
        if not ref:
            raise RuntimeError("service reference is required")
        allowed_refs = set(requester.required_services or set())
        if ref not in allowed_refs:
            raise RuntimeError(
                f"Plugin '{requester.plugin_id}' attempted undeclared service access: {ref}"
            )
        if ":" in ref:
            pid, service_name = ref.split(":", 1)
            obj = self._service_registry.get(pid, {}).get(service_name)
            if obj is None:
                raise RuntimeError(f"Service unavailable: {ref}")
            return obj
        # Unqualified lookup: unique service by name across all plugins.
        matches: list[Any] = []
        for provider_pid, services in self._service_registry.items():
            if ref in services:
                matches.append(services[ref])
        if not matches:
            raise RuntimeError(f"Service unavailable: {ref}")
        if len(matches) > 1:
            raise RuntimeError(f"Service reference is ambiguous: {ref}")
        return matches[0]

    @staticmethod
    def _normalize_dep_id(dep: str) -> str:
        text = str(dep or "").strip()
        if not text:
            return ""
        for sep in (">=", "<=", "==", "!=", ">", "<", " "):
            if sep in text:
                text = text.split(sep, 1)[0].strip()
                break
        return text

    def _build_load_order(self, records: list[PluginRecord]) -> list[PluginRecord]:
        rec_by_id = {r.plugin_id: r for r in records}
        deps: dict[str, set[str]] = {}
        for rec in records:
            dep_ids = {self._normalize_dep_id(x) for x in rec.dependencies}
            dep_ids = {x for x in dep_ids if x}
            deps[rec.plugin_id] = {x for x in dep_ids if x in rec_by_id}
        out: list[PluginRecord] = []
        ready = sorted([pid for pid, d in deps.items() if not d])
        while ready:
            pid = ready.pop(0)
            out.append(rec_by_id[pid])
            for other in sorted(deps.keys()):
                if pid in deps[other]:
                    deps[other].discard(pid)
                    if not deps[other] and other not in [r.plugin_id for r in out] and other not in ready:
                        ready.append(other)
                        ready.sort()
        if len(out) != len(records):
            unresolved = [pid for pid, d in deps.items() if d]
            raise RuntimeError(f"Dependency cycle detected: {', '.join(sorted(unresolved))}")
        return out

    def record_runtime_event(self, plugin_id: str, event: str, payload: dict[str, Any] | None = None) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        rec = next((x for x in self.records if x.plugin_id == plugin_id), None)
        item = {
            "ts": now,
            "plugin_id": plugin_id,
            "event": str(event or "event"),
            "payload": dict(payload or {}),
        }
        self._append_runtime_log(item)
        if rec is not None:
            rec.last_run_at = now
            rec.last_event_at = now
            rec.runtime_events.append(item)
            if len(rec.runtime_events) > 100:
                rec.runtime_events = rec.runtime_events[-100:]

    def publish_runtime_event(self, source_plugin_id: str, event: str, payload: dict[str, Any]) -> None:
        self.record_runtime_event(source_plugin_id, f"bus:{event}", payload)
        envelope = {
            "source_plugin_id": source_plugin_id,
            "event": event,
            "payload": dict(payload or {}),
        }
        for rec in list(self.records):
            if rec.instance is None or "hooks" not in rec.permissions:
                continue
            try:
                on_event = getattr(rec.instance, "on_event", None)
                if callable(on_event):
                    on_event("plugin_bus", dict(envelope))
            except Exception as exc:  # noqa: BLE001
                rec.last_error = str(exc)
                rec.last_error_at = datetime.now().isoformat(timespec="seconds")
                self.window.log_event("Error", f"Plugin bus error ({rec.plugin_id}): {exc}")

    def register_plugin_command(
        self,
        plugin_id: str,
        command_name: str,
        callback,
        *,
        description: str = "",
        args_schema: dict[str, Any] | None = None,
    ) -> None:
        pid = str(plugin_id or "").strip()
        name = str(command_name or "").strip()
        if not pid or not name:
            raise ValueError("plugin_id and command_name are required")
        per = self._command_registry.get(pid)
        if per is None:
            per = {}
            self._command_registry[pid] = per
        per[name] = {
            "callback": callback,
            "description": str(description or ""),
            "args_schema": dict(args_schema or {}),
        }
        rec = next((x for x in self.records if x.plugin_id == pid), None)
        if rec is not None:
            rec.command_specs[name] = {
                "description": str(description or ""),
                "args_schema": dict(args_schema or {}),
            }
            # Command-palette integration path: expose plugin commands as real QActions in Plugins menu.
            try:
                root = getattr(self.window, "plugins_menu", None)
                if root is None and hasattr(self.window, "menuBar"):
                    root = self.window.menuBar().addMenu("&Plugins")
                    self.window.plugins_menu = root
                if root is not None:
                    commands_menu = None
                    for act in root.actions():
                        sub = act.menu()
                        if sub is not None and str(sub.title()).replace("&", "").strip().lower() == "commands":
                            commands_menu = sub
                            break
                    if commands_menu is None:
                        commands_menu = root.addMenu("Commands")
                    plugin_menu = None
                    plugin_title = rec.name or rec.plugin_id
                    for act in commands_menu.actions():
                        sub = act.menu()
                        if sub is not None and str(sub.title()).replace("&", "").strip() == plugin_title:
                            plugin_menu = sub
                            break
                    if plugin_menu is None:
                        plugin_menu = commands_menu.addMenu(plugin_title)
                    existing = next((a for a in rec.actions if a.objectName() == f"plugincmd:{pid}:{name}"), None)
                    if existing is not None:
                        try:
                            plugin_menu.removeAction(existing)
                        except Exception:
                            pass
                        try:
                            rec.actions.remove(existing)
                        except Exception:
                            pass
                    action = QAction(name, self.window)
                    action.setObjectName(f"plugincmd:{pid}:{name}")
                    action.triggered.connect(lambda _checked=False, _pid=pid, _name=name: self.run_plugin_command(_pid, _name, {}))
                    plugin_menu.addAction(action)
                    rec.actions.append(action)
            except Exception:
                pass

    def list_plugin_commands(self, plugin_id: str) -> list[dict[str, Any]]:
        pid = str(plugin_id or "").strip()
        per = self._command_registry.get(pid, {})
        out: list[dict[str, Any]] = []
        for name in sorted(per.keys()):
            entry = per[name]
            out.append(
                {
                    "name": name,
                    "description": str(entry.get("description", "") or ""),
                    "args_schema": dict(entry.get("args_schema", {}) or {}),
                }
            )
        return out

    def run_plugin_command(self, requester_plugin_id: str, command_ref: str, args: dict[str, Any] | None = None) -> Any:
        ref = str(command_ref or "").strip()
        if not ref:
            raise RuntimeError("command reference is required")
        if ":" in ref:
            pid, name = ref.split(":", 1)
        else:
            pid = str(requester_plugin_id or "").strip()
            name = ref
        entry = self._command_registry.get(pid, {}).get(name)
        if entry is None:
            raise RuntimeError(f"Command not found: {ref}")
        cb = entry.get("callback")
        payload = dict(args or {})
        self.record_runtime_event(pid, "command_execute", {"command": name, "requester": requester_plugin_id})
        if callable(cb):
            return cb(payload)
        raise RuntimeError(f"Command callback is not callable: {ref}")

    def install_plugin_archive(self, archive_path: Path) -> Path:
        path = Path(archive_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Archive not found: {path}")
        if path.suffix.lower() != ".zip":
            raise ValueError("Plugin archive must be a .zip file.")
        allowed_permissions = {
            "file",
            "network",
            "ai",
            "ui",
            "menu",
            "toolbar",
            "panel",
            "background",
            "hooks",
        }
        with tempfile.TemporaryDirectory(prefix="pypad_plugin_install_") as temp_dir:
            temp_root = Path(temp_dir)
            with zipfile.ZipFile(path, "r") as zf:
                for info in zf.infolist():
                    member = Path(info.filename.replace("\\", "/"))
                    if member.is_absolute() or ".." in member.parts:
                        raise RuntimeError(f"Unsafe archive path: {info.filename}")
                zf.extractall(temp_root)
            candidates: list[Path] = []
            if (temp_root / "plugin.json").exists() and (temp_root / "plugin.py").exists():
                candidates.append(temp_root)
            for child in temp_root.rglob("*"):
                if child.is_dir() and (child / "plugin.json").exists() and (child / "plugin.py").exists():
                    candidates.append(child)
            if not candidates:
                raise RuntimeError("Archive does not contain plugin.json + plugin.py.")
            candidates = sorted({c.resolve() for c in candidates}, key=lambda p: len(p.parts))
            source_dir = candidates[0]
            try:
                meta = json.loads((source_dir / "plugin.json").read_text(encoding="utf-8-sig"))
            except Exception as exc:
                raise RuntimeError(f"Invalid plugin.json: {exc}") from exc
            if not isinstance(meta, dict):
                raise RuntimeError("Invalid plugin.json format.")
            pid = self._normalize_plugin_id(str(meta.get("id", source_dir.name)))
            if not self._valid_plugin_id(pid):
                raise RuntimeError("Invalid plugin id in archive.")
            requested = {
                str(p).lower().strip()
                for p in meta.get("permissions", [])
                if str(p).lower().strip() in allowed_permissions
            }
            dest_dir = self.plugins_dir / pid
            if dest_dir.exists():
                raise FileExistsError(f"Plugin already exists: {pid}")
            staging_dir = self.plugins_dir / f"__incoming_{pid}_{uuid.uuid4().hex[:8]}"
            shutil.copytree(source_dir, staging_dir, ignore=shutil.ignore_patterns("__pycache__"))
            try:
                issues = assess_plugin_security(
                    plugin_root=self.plugins_dir,
                    plugin_dir=staging_dir,
                    plugin_id=pid,
                    permissions=requested,
                )
                if issues:
                    raise RuntimeError("Plugin rejected by policy: " + "; ".join(issues[:3]))
                staging_dir.rename(dest_dir)
                return dest_dir
            finally:
                if staging_dir.exists():
                    shutil.rmtree(staging_dir, ignore_errors=True)

    def _repo_online_plugins_dir(self) -> Path:
        if getattr(sys, "frozen", False):
            meipass = Path(str(getattr(sys, "_MEIPASS", "")))
            if meipass:
                candidate = meipass / "online_plugins"
                if candidate.exists():
                    return candidate
        return _root() / "online_plugins"

    def load_online_plugin_catalog(self) -> list[dict[str, str]]:
        catalog_url = str(
            self.window.settings.get(
                "plugin_online_catalog_url",
                "https://raw.githubusercontent.com/ne0gl1tch20/pypad/main/online_plugins/catalog.json",
            )
            or ""
        ).strip()
        payload: Any = None
        errors: list[str] = []
        local_catalog = self._repo_online_plugins_dir() / "catalog.json"
        if local_catalog.exists():
            try:
                payload = json.loads(local_catalog.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"Local catalog read failed: {exc}")
        if payload is None and catalog_url:
            try:
                with urlopen(catalog_url, timeout=6.0) as resp:
                    raw_bytes = resp.read()
                try:
                    payload = json.loads(raw_bytes.decode("utf-8", errors="strict"))
                except Exception:
                    payload = json.loads(raw_bytes.decode("utf-8-sig", errors="replace"))
            except Exception as exc:
                errors.append(f"Remote catalog fetch failed: {exc}")
        if payload is None:
            if errors:
                self.window.show_status_message(errors[-1], 3500)
            return []
        rows = payload if isinstance(payload, list) else payload.get("plugins", [])
        if not isinstance(rows, list):
            return []
        out: list[dict[str, str]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            plugin_id = self._normalize_plugin_id(str(row.get("id", "")).strip())
            source = str(row.get("source", "") or "").strip()
            source = source.strip("/\\")
            if not plugin_id or not source:
                continue
            out.append(
                {
                    "id": plugin_id,
                    "name": str(row.get("name", plugin_id) or plugin_id),
                    "description": str(row.get("description", "") or ""),
                    "author": str(row.get("author", "") or ""),
                    "version": str(row.get("version", "") or ""),
                    "repo": str(row.get("repo", "") or "").strip(),
                    "source": source,
                    "homepage": str(row.get("homepage", "") or "").strip(),
                }
            )
        return out

    @staticmethod
    def _decode_text_bytes_with_fallback(payload: bytes) -> str:
        try:
            return payload.decode("utf-8", errors="strict")
        except Exception:
            return payload.decode("utf-8-sig", errors="replace")

    def install_online_plugin(self, entry: dict[str, str]) -> Path:
        plugin_id = self._normalize_plugin_id(str(entry.get("id", "")).strip())
        source = str(entry.get("source", "") or "").strip().strip("/\\")
        repo = str(entry.get("repo", "") or "").strip()
        if not self._valid_plugin_id(plugin_id):
            raise RuntimeError("Invalid online plugin id.")
        if not source:
            raise RuntimeError("Online plugin source is missing.")
        dest_dir = self.plugins_dir / plugin_id
        if dest_dir.exists():
            raise FileExistsError(f"Plugin already exists: {plugin_id}")
        with tempfile.TemporaryDirectory(prefix="pypad_online_plugin_") as temp_dir:
            staging = Path(temp_dir) / plugin_id
            staging.mkdir(parents=True, exist_ok=True)
            raw_base = repo.replace("https://github.com/", "https://raw.githubusercontent.com/").rstrip("/")
            if raw_base.endswith(".git"):
                raw_base = raw_base[:-4]
            if raw_base:
                raw_base = f"{raw_base}/main/{source}"
            else:
                raw_base = f"https://raw.githubusercontent.com/ne0gl1tch20/pypad/main/{source}"
            for rel in ("plugin.json", "plugin.py"):
                file_url = f"{raw_base}/{rel}"
                with urlopen(file_url, timeout=8.0) as resp:
                    payload = resp.read()
                (staging / rel).write_text(self._decode_text_bytes_with_fallback(payload), encoding="utf-8")
            try:
                meta = json.loads((staging / "plugin.json").read_text(encoding="utf-8-sig"))
            except Exception as exc:
                raise RuntimeError(f"Invalid plugin.json from online source: {exc}") from exc
            if not isinstance(meta, dict):
                raise RuntimeError("Invalid online plugin manifest format.")
            manifest_id = self._normalize_plugin_id(str(meta.get("id", plugin_id)))
            if manifest_id != plugin_id:
                raise RuntimeError(
                    f"Plugin id mismatch: catalog '{plugin_id}' vs manifest '{manifest_id}'."
                )
            requested = {
                str(p).lower().strip()
                for p in meta.get("permissions", [])
                if str(p).lower().strip() in {
                    "file",
                    "network",
                    "ai",
                    "ui",
                    "menu",
                    "toolbar",
                    "panel",
                    "background",
                    "hooks",
                }
            }
            issues = assess_plugin_security(
                plugin_root=self.plugins_dir,
                plugin_dir=staging,
                plugin_id=plugin_id,
                permissions=requested,
            )
            if issues:
                raise RuntimeError("Plugin rejected by policy: " + "; ".join(issues[:3]))
            shutil.copytree(staging, dest_dir)
        return dest_dir

    def inspect_plugin_archive(self, archive_path: Path) -> dict[str, Any]:
        path = Path(archive_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Archive not found: {path}")
        if path.suffix.lower() != ".zip":
            raise ValueError("Plugin archive must be a .zip file.")
        allowed_permissions = {
            "file",
            "network",
            "ai",
            "ui",
            "menu",
            "toolbar",
            "panel",
            "background",
            "hooks",
        }
        with tempfile.TemporaryDirectory(prefix="pypad_plugin_") as temp_dir:
            temp_root = Path(temp_dir)
            with zipfile.ZipFile(path, "r") as zf:
                for info in zf.infolist():
                    member = Path(info.filename.replace("\\", "/"))
                    if member.is_absolute() or ".." in member.parts:
                        raise RuntimeError(f"Unsafe archive path: {info.filename}")
                zf.extractall(temp_root)
            candidates: list[Path] = []
            if (temp_root / "plugin.json").exists() and (temp_root / "plugin.py").exists():
                candidates.append(temp_root)
            for child in temp_root.rglob("*"):
                if child.is_dir() and (child / "plugin.json").exists() and (child / "plugin.py").exists():
                    candidates.append(child)
            if not candidates:
                raise RuntimeError("Archive does not contain plugin.json + plugin.py.")
            candidates = sorted({c.resolve() for c in candidates}, key=lambda p: len(p.parts))
            source_dir = candidates[0]
            try:
                meta = json.loads((source_dir / "plugin.json").read_text(encoding="utf-8-sig"))
            except Exception as exc:
                raise RuntimeError(f"Invalid plugin.json: {exc}") from exc
            if not isinstance(meta, dict):
                raise RuntimeError("Invalid plugin.json format.")
            pid = self._normalize_plugin_id(str(meta.get("id", source_dir.name)))
            if not self._valid_plugin_id(pid):
                raise RuntimeError("Invalid plugin id in archive.")
            requested = {
                str(p).lower().strip()
                for p in meta.get("permissions", [])
                if str(p).lower().strip() in allowed_permissions
            }
            inspect_dir = temp_root / "__inspect_target"
            shutil.copytree(source_dir, inspect_dir, ignore=shutil.ignore_patterns("__pycache__"))
            issues = assess_plugin_security(
                plugin_root=self.plugins_dir,
                plugin_dir=inspect_dir,
                plugin_id=pid,
                permissions=requested,
            )
            return {
                "plugin_id": pid,
                "name": str(meta.get("name", pid)),
                "author": str(meta.get("author", "") or ""),
                "version": str(meta.get("version", "") or ""),
                "requested_permissions": sorted(requested),
                "issues": list(issues),
            }

    def check_plugin_update(self, rec: PluginRecord) -> dict[str, Any]:
        update_url = str(rec.metadata.get("update_url", "") or "").strip()
        current = str(rec.metadata.get("version", "") or "").strip() or "0.0.0"
        result = {
            "plugin_id": rec.plugin_id,
            "current_version": current,
            "update_url": update_url,
            "latest_version": "",
            "update_available": False,
            "error": "",
        }
        if not update_url:
            result["error"] = "No update_url configured."
            return result
        try:
            with urlopen(update_url, timeout=5.0) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise RuntimeError("Update payload must be a JSON object.")
            latest = str(payload.get("version", "") or "").strip()
            if not latest:
                raise RuntimeError("Missing 'version' in update payload.")
            result["latest_version"] = latest
            result["update_available"] = _parse_version_tuple(latest) > _parse_version_tuple(current)
            return result
        except Exception as exc:
            result["error"] = str(exc)
            return result

    def check_all_plugin_updates(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for rec in self.discover():
            out.append(self.check_plugin_update(rec))
        return out

    def plugin_diagnostics_snapshot(self, rec: PluginRecord) -> dict[str, Any]:
        return {
            "plugin_id": rec.plugin_id,
            "name": rec.name,
            "description": rec.description,
            "enabled": bool(rec.enabled),
            "loaded": rec.instance is not None,
            "failure_count": int(rec.failure_count),
            "health_score": int(self.plugin_health_score(rec)),
            "permissions": sorted(rec.permissions),
            "requested_permissions": sorted(rec.requested_permissions),
            "dependencies": sorted(rec.dependencies),
            "provided_services": sorted(rec.provided_services),
            "required_services": sorted(rec.required_services),
            "metadata": dict(rec.metadata),
            "security_issues": list(rec.security_issues),
            "compatibility_issues": list(rec.compatibility_issues),
            "hook_counts": dict(rec.hook_counts),
            "load_count": int(rec.load_count),
            "last_run_at": rec.last_run_at,
            "last_event_at": rec.last_event_at,
            "last_error_at": rec.last_error_at,
            "last_error": rec.last_error,
            "runtime_events": list(rec.runtime_events),
            "jobs": list(self._job_registry.get(rec.plugin_id, {}).values()),
            "logs": self.plugin_logs(rec.plugin_id),
        }

    def start_plugin_job(self, plugin_id: str, job_name: str, fn) -> str:
        pid = str(plugin_id or "").strip()
        if not pid:
            raise ValueError("plugin_id is required")
        jid = f"{pid}:{uuid.uuid4().hex[:12]}"
        per = self._job_registry.get(pid)
        if per is None:
            per = {}
            self._job_registry[pid] = per
        state: dict[str, Any] = {
            "job_id": jid,
            "job_name": str(job_name or "job"),
            "status": "running",
            "progress": 0.0,
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "ended_at": "",
            "cancel_requested": False,
            "error": "",
        }
        per[jid] = state

        def _run() -> None:
            def report_progress(value: float) -> None:
                try:
                    state["progress"] = max(0.0, min(1.0, float(value)))
                except Exception:
                    pass

            def should_stop() -> bool:
                return bool(state.get("cancel_requested", False))

            try:
                if callable(fn):
                    fn({"report_progress": report_progress, "should_stop": should_stop, "job_id": jid})
                if bool(state.get("cancel_requested", False)):
                    state["status"] = "cancelled"
                else:
                    state["status"] = "completed"
            except Exception as exc:  # noqa: BLE001
                state["status"] = "failed"
                state["error"] = str(exc)
                self.record_runtime_event(pid, "job_error", {"job_id": jid, "message": str(exc)})
            finally:
                state["ended_at"] = datetime.now().isoformat(timespec="seconds")
                self.record_runtime_event(pid, "job_done", {"job_id": jid, "status": state.get("status", "")})

        thread = threading.Thread(target=_run, name=f"plugin-job-{pid}", daemon=True)
        state["thread"] = thread
        thread.start()
        self.record_runtime_event(pid, "job_created", {"job_id": jid, "job_name": state["job_name"]})
        return jid

    def cancel_plugin_job(self, plugin_id: str, job_id: str) -> bool:
        pid = str(plugin_id or "").strip()
        jid = str(job_id or "").strip()
        state = self._job_registry.get(pid, {}).get(jid)
        if state is None:
            return False
        state["cancel_requested"] = True
        if state.get("status") == "running":
            state["status"] = "cancelling"
        self.record_runtime_event(pid, "job_cancel_requested", {"job_id": jid})
        return True

    def plugin_job_status(self, plugin_id: str, job_id: str) -> dict[str, Any]:
        pid = str(plugin_id or "").strip()
        jid = str(job_id or "").strip()
        state = self._job_registry.get(pid, {}).get(jid)
        if state is None:
            raise RuntimeError(f"Job not found: {jid}")
        out = dict(state)
        out.pop("thread", None)
        return out

    def discover(self) -> list[PluginRecord]:
        enabled = self._enabled()
        quarantined = self._quarantined()
        overrides = self._permission_overrides()
        failure_counts = self._failure_counts()
        allowed_permissions = {
            "file",
            "network",
            "ai",
            "ui",
            "menu",
            "toolbar",
            "panel",
            "background",
            "hooks",
        }
        out: list[PluginRecord] = []
        for folder in sorted(self.plugins_dir.iterdir()):
            if not folder.is_dir():
                continue
            manifest = folder / "plugin.json"
            code = folder / "plugin.py"
            if not manifest.exists() or not code.exists():
                continue
            try:
                # Accept BOM-prefixed UTF-8 manifests generated by common editors/tools.
                meta = json.loads(manifest.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
            if not isinstance(meta, dict):
                continue
            pid = str(meta.get("id", folder.name))
            plugin_api_version = str(meta.get("plugin_api_version", "1.0") or "1.0").strip()
            min_app_version = str(meta.get("min_app_version", "") or "").strip()
            max_app_version = str(meta.get("max_app_version", "") or "").strip()
            update_url = str(meta.get("update_url", "") or "").strip()
            homepage = str(meta.get("homepage", "") or "").strip()
            settings_schema = meta.get("settings_schema", {})
            depends_on_raw = meta.get("depends_on", [])
            provides_raw = meta.get("provides_services", [])
            requires_raw = meta.get("requires_services", [])
            compatibility_issues: list[str] = []
            if not _is_version_compatible(self.app_version, min_app_version, max_app_version):
                compatibility_issues.append(
                    f"Incompatible with app version {self.app_version} "
                    f"(requires min={min_app_version or '-'} max={max_app_version or '-'})"
                )
            if not _is_plugin_api_compatible(plugin_api_version, PLUGIN_API_VERSION):
                compatibility_issues.append(
                    f"Incompatible plugin API version {plugin_api_version} (supported {PLUGIN_API_VERSION})"
                )
            requested = {
                str(p).lower().strip()
                for p in meta.get("permissions", [])
                if str(p).lower().strip() in allowed_permissions
            }
            override = overrides.get(pid)
            perms = requested if override is None else (requested & override)
            dependencies = [
                self._normalize_dep_id(str(x))
                for x in (depends_on_raw if isinstance(depends_on_raw, list) else [])
                if str(x).strip()
            ]
            dependencies = [x for x in dependencies if x]
            provided_services = {
                str(x).strip()
                for x in (provides_raw if isinstance(provides_raw, list) else [])
                if str(x).strip()
            }
            required_services = {
                str(x).strip()
                for x in (requires_raw if isinstance(requires_raw, list) else [])
                if str(x).strip()
            }
            issues = assess_plugin_security(
                plugin_root=self.plugins_dir,
                plugin_dir=folder,
                plugin_id=pid,
                permissions=perms,
            )
            out.append(
                PluginRecord(
                    plugin_id=pid,
                    name=str(meta.get("name", pid)),
                    description=str(meta.get("description", "")),
                    permissions=perms,
                    requested_permissions=requested,
                    path=folder,
                    enabled=pid in enabled,
                    digest=compute_plugin_digest(folder),
                    quarantined=(pid in quarantined) or bool(issues),
                    security_issues=issues,
                    compatibility_issues=compatibility_issues,
                    metadata={
                        "version": str(meta.get("version", "") or "").strip(),
                        "author": str(meta.get("author", "") or "").strip(),
                        "plugin_api_version": plugin_api_version,
                        "min_app_version": min_app_version,
                        "max_app_version": max_app_version,
                        "update_url": update_url,
                        "homepage": homepage,
                    },
                    settings_schema=settings_schema if isinstance(settings_schema, dict) else {},
                    dependencies=dependencies,
                    provided_services=provided_services,
                    required_services=required_services,
                    failure_count=int(failure_counts.get(pid, 0) or 0),
                )
            )
        ids = {r.plugin_id for r in out}
        for rec in out:
            missing = [d for d in rec.dependencies if d and d not in ids]
            for dep in missing:
                rec.compatibility_issues.append(f"Missing dependency plugin: {dep}")
        return out

    def emit_event(self, event_name: str, **payload) -> None:
        for rec in list(self.records):
            if rec.instance is None:
                continue
            if "hooks" not in rec.permissions:
                continue
            try:
                now_iso = datetime.now().isoformat(timespec="seconds")
                rec.last_run_at = now_iso
                rec.last_event_at = now_iso
                rec.hook_counts[event_name] = int(rec.hook_counts.get(event_name, 0) or 0) + 1
                self.record_runtime_event(rec.plugin_id, f"hook:{event_name}", {"source": "app"})
                event_payload = dict(payload)
                if "ui" not in rec.permissions and "tab" in event_payload:
                    event_payload.pop("tab", None)
                on_event = getattr(rec.instance, "on_event", None)
                if callable(on_event):
                    on_event(event_name, dict(event_payload))
                handler = getattr(rec.instance, f"on_{event_name}", None)
                if callable(handler):
                    handler(dict(event_payload))
            except Exception as exc:  # noqa: BLE001
                rec.failure_count = self._record_plugin_failure(rec.plugin_id, f"hook:{event_name}:{exc}")
                rec.last_error = str(exc)
                rec.last_error_at = datetime.now().isoformat(timespec="seconds")
                self.window.log_event("Error", f"Plugin hook error ({rec.plugin_id}:{event_name}): {exc}")

    def _unload_record(self, rec: PluginRecord) -> None:
        try:
            on_unload = getattr(rec.instance, "on_unload", None)
            if callable(on_unload):
                on_unload()
        except Exception as exc:  # noqa: BLE001
            self.window.log_event("Error", f"Plugin unload error ({rec.plugin_id}): {exc}")
        for timer in rec.timers:
            try:
                timer.stop()
            except Exception:
                pass
        for action in rec.actions:
            try:
                for widget in action.associatedWidgets():
                    widget.removeAction(action)
            except Exception:
                pass
            try:
                action.setParent(None)
            except Exception:
                pass
        for panel in rec.panels:
            try:
                self.window.removeDockWidget(panel)
                panel.hide()
                panel.deleteLater()
            except Exception:
                pass
        for toolbar in rec.toolbars:
            try:
                name = toolbar.objectName()
                if name.startswith("pluginToolbar:"):
                    self.window.removeToolBar(toolbar)
                    toolbar.hide()
                    toolbar.deleteLater()
            except Exception:
                pass
        rec.timers.clear()
        rec.actions.clear()
        rec.panels.clear()
        rec.toolbars.clear()
        rec.instance = None

    def _unload_all(self) -> None:
        self._service_registry = {}
        self._command_registry = {}
        self._job_registry = {}
        self._plugin_logs = {}
        for rec in list(self.records):
            if rec.instance is not None:
                self._unload_record(rec)

    def reload(self, *, startup: bool = False) -> None:
        import importlib.util

        self._unload_all()
        self.records = self.discover()
        if startup and self._is_startup_safe_mode():
            self.window.show_status_message("Plugin startup safe mode is enabled.", 3000)
            return
        enabled_recs = [r for r in self.records if r.enabled and not r.security_issues and not r.compatibility_issues and not r.quarantined]
        enabled_ids = {r.plugin_id for r in enabled_recs}
        provided_by_plugin = {r.plugin_id: set(r.provided_services) for r in enabled_recs}
        global_services = set()
        for values in provided_by_plugin.values():
            global_services.update(values)
        for rec in enabled_recs:
            unresolved_deps = [dep for dep in rec.dependencies if dep and dep not in enabled_ids]
            if unresolved_deps:
                rec.compatibility_issues.append(f"Disabled/missing dependency at runtime: {', '.join(sorted(unresolved_deps))}")
            missing_services: list[str] = []
            for req in sorted(rec.required_services):
                if ":" in req:
                    pid, name = req.split(":", 1)
                    if name not in provided_by_plugin.get(pid, set()):
                        missing_services.append(req)
                else:
                    if req not in global_services:
                        missing_services.append(req)
            if missing_services:
                rec.compatibility_issues.append("Missing required service(s): " + ", ".join(missing_services))
        try:
            load_order = self._build_load_order([r for r in self.records if r.enabled])
        except Exception as exc:
            self.window.log_event("Error", f"Plugin dependency resolution failed: {exc}")
            load_order = [r for r in self.records if r.enabled]
            for rec in load_order:
                rec.compatibility_issues.append(f"Dependency resolution warning: {exc}")
        for rec in load_order:
            if not rec.enabled:
                continue
            if rec.security_issues:
                reason = "; ".join(rec.security_issues[:3])
                self._quarantine_plugin(rec, reason)
                self.window.show_status_message(f"Plugin blocked by policy: {rec.plugin_id}", 4200)
                continue
            if rec.compatibility_issues:
                self.window.show_status_message(f"Plugin incompatible: {rec.plugin_id}", 4200)
                continue
            if rec.quarantined:
                self.window.log_event("Info", f"Skipping quarantined plugin: {rec.plugin_id}")
                continue
            if not self._is_plugin_trusted(rec):
                if not self._trust_prompt(rec):
                    self.window.log_event("Info", f"Plugin trust denied: {rec.plugin_id}")
                    continue
                self._mark_trusted(rec)
            try:
                self._apply_plugin_settings_schema(rec)
                spec = importlib.util.spec_from_file_location(f"np_plugin_{rec.plugin_id}", rec.path / "plugin.py")
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                cls = getattr(module, "Plugin", None)
                if cls is None:
                    continue
                rec.instance = cls(PluginAPI(self.window, rec))
                rec.load_count = int(rec.load_count) + 1
                rec.last_run_at = datetime.now().isoformat(timespec="seconds")
                self._clear_plugin_failure(rec.plugin_id)
                rec.failure_count = 0
                self.record_runtime_event(rec.plugin_id, "load", {"count": rec.load_count})
                on_load = getattr(rec.instance, "on_load", None)
                if callable(on_load):
                    on_load()
            except Exception as exc:  # noqa: BLE001
                rec.failure_count = self._record_plugin_failure(rec.plugin_id, str(exc))
                rec.last_error = str(exc)
                rec.last_error_at = datetime.now().isoformat(timespec="seconds")
                self.record_runtime_event(rec.plugin_id, "error", {"message": str(exc)})
                if rec.failure_count >= self._max_failures_before_disable():
                    self._quarantine_plugin(rec, f"{exc} (failure threshold reached: {rec.failure_count})")
                    self.window.show_status_message(
                        f"Plugin auto-disabled after repeated failures: {rec.plugin_id}",
                        4200,
                    )
                else:
                    self.window.show_status_message(
                        f"Plugin load failed ({rec.plugin_id}) [{rec.failure_count}/{self._max_failures_before_disable()}]",
                        3500,
                    )

    def set_enabled(self, plugin_id: str, enabled: bool) -> None:
        ids = self._enabled()
        rec = next((x for x in self.discover() if x.plugin_id == plugin_id), None)
        if enabled and rec is not None:
            if rec.security_issues:
                QMessageBox.warning(
                    self.window,
                    "Plugin Blocked by Policy",
                    f"Plugin '{plugin_id}' violates security policy:\n- " + "\n- ".join(rec.security_issues[:6]),
                )
                return
            if rec.compatibility_issues:
                QMessageBox.warning(
                    self.window,
                    "Plugin Incompatible",
                    f"Plugin '{plugin_id}' is incompatible:\n- " + "\n- ".join(rec.compatibility_issues[:6]),
                )
                return
            if rec.quarantined:
                QMessageBox.warning(
                    self.window,
                    "Plugin Quarantined",
                    f"Plugin '{plugin_id}' is quarantined due to a previous failure.\nRemove it from quarantine first.",
                )
                return
            if not self._is_plugin_trusted(rec):
                if not self._trust_prompt(rec):
                    return
                self._mark_trusted(rec)
        if enabled:
            ids.add(plugin_id)
        else:
            ids.discard(plugin_id)
        self._save_enabled(ids)

    def export_plugin(self, plugin_id: str, output_zip: Path) -> Path:
        rec = next((x for x in self.discover() if x.plugin_id == plugin_id), None)
        if rec is None:
            raise FileNotFoundError(f"Plugin not found: {plugin_id}")
        output_zip.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for child in rec.path.rglob("*"):
                if not child.is_file():
                    continue
                if "__pycache__" in child.parts:
                    continue
                rel = child.relative_to(rec.path)
                zf.write(child, arcname=f"{rec.plugin_id}/{rel.as_posix()}")
        return output_zip

    @staticmethod
    def _normalize_plugin_id(value: str) -> str:
        return re.sub(r"[^a-z0-9_.-]+", "_", str(value or "").strip().lower())

    @staticmethod
    def _valid_plugin_id(value: str) -> bool:
        text = str(value or "").strip().lower()
        if not text:
            return False
        if keyword.iskeyword(text):
            return False
        return bool(re.fullmatch(r"[a-z0-9][a-z0-9_.-]{1,63}", text))

    def scaffold_plugin(
        self,
        *,
        plugin_id: str,
        name: str,
        description: str = "",
        permissions: set[str] | None = None,
    ) -> Path:
        allowed_permissions = {
            "file",
            "network",
            "ai",
            "ui",
            "menu",
            "toolbar",
            "panel",
            "background",
            "hooks",
        }
        pid = self._normalize_plugin_id(plugin_id)
        if not self._valid_plugin_id(pid):
            raise ValueError("Invalid plugin id. Use [a-z0-9][a-z0-9_.-]{1,63}.")
        perms = sorted({str(p).strip().lower() for p in (permissions or {"menu"}) if str(p).strip().lower() in allowed_permissions})
        if not perms:
            perms = ["menu"]
        title = str(name or pid).strip() or pid
        desc = str(description or "").strip()
        plugin_dir = self.plugins_dir / pid
        if plugin_dir.exists():
            raise FileExistsError(f"Plugin folder already exists: {plugin_dir}")
        plugin_dir.mkdir(parents=True, exist_ok=False)
        manifest = {
            "id": pid,
            "name": title,
            "author": "",
            "version": "1.0.0",
            "plugin_api_version": PLUGIN_API_VERSION,
            "description": desc or "Plugin scaffold generated from Plugin Manager.",
            "min_app_version": self.app_version,
            "max_app_version": "",
            "update_url": "",
            "homepage": "",
            "depends_on": [],
            "provides_services": [],
            "requires_services": [],
            "settings_schema": {
                "enabled": {"type": "bool", "default": True, "description": "Enable plugin behavior."}
            },
            "permissions": perms,
        }
        (plugin_dir / "plugin.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        sample_code = (
            "class Plugin:\n"
            "    def __init__(self, api) -> None:\n"
            "        self.api = api\n\n"
            "    def on_load(self) -> None:\n"
            f"        self.api.notify(\"{title} loaded.\")\n"
            "        self.api.add_menu_action(\n"
            f"            \"Plugins/{title}\",\n"
            "            \"Hello\",\n"
            "            self.say_hello,\n"
            "        )\n\n"
            "    def say_hello(self) -> None:\n"
            "        self.api.show_status(\"Hello from scaffold plugin.\", 1800)\n"
        )
        (plugin_dir / "plugin.py").write_text(sample_code, encoding="utf-8")
        return plugin_dir


class PluginManagerDialog(QDialog):
    def __init__(self, parent, host: PluginHost) -> None:
        super().__init__(parent)
        self.host = host
        self.setWindowTitle("Plugin Manager")
        self.resize(620, 460)
        v = QVBoxLayout(self)
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Filter plugins by id, name, or permission...")
        self.search_input.textChanged.connect(self._populate)
        v.addWidget(self.search_input)
        self._visible_plugin_ids: list[str] = []
        self.unsafe_ui_bridge_check = QCheckBox(
            "Allow unsafe plugin UI bridge (exposes raw app window/tab objects)",
            self,
        )
        self.unsafe_ui_bridge_check.setChecked(bool(self.host.window.settings.get("plugin_allow_unsafe_ui_bridge", False)))
        self.unsafe_ui_bridge_check.setToolTip(
            "Disabled by default. Enable only for fully trusted internal plugins."
        )
        self.unsafe_ui_bridge_check.toggled.connect(self._toggle_unsafe_ui_bridge)
        v.addWidget(self.unsafe_ui_bridge_check)
        self.dev_repo_plugins_check: QCheckBox | None = None
        if self.host.runtime_mode_label() == "development":
            self.dev_repo_plugins_check = QCheckBox(
                "Dev Mode: load plugins from ../plugins (repo folder)",
                self,
            )
            self.dev_repo_plugins_check.setChecked(bool(self.host.window.settings.get("plugin_dev_use_repo_plugins", False)))
            self.dev_repo_plugins_check.toggled.connect(self._toggle_dev_repo_plugins_source)
            v.addWidget(self.dev_repo_plugins_check)
        content_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        left_pane = QWidget(content_splitter)
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.list_widget = QListWidget(left_pane)
        self.list_widget.currentRowChanged.connect(lambda _idx: self._refresh_diagnostics())
        left_layout.addWidget(self.list_widget, 1)
        hint = QLabel("Permission changes apply after Reload.", left_pane)
        left_layout.addWidget(hint)
        right_pane = QWidget(content_splitter)
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)
        diag_label = QLabel("Runtime Diagnostics", right_pane)
        right_layout.addWidget(diag_label)
        self.diagnostics_view = QTextEdit(right_pane)
        self.diagnostics_view.setReadOnly(True)
        right_layout.addWidget(self.diagnostics_view, 1)
        content_splitter.addWidget(left_pane)
        content_splitter.addWidget(right_pane)
        content_splitter.setStretchFactor(0, 3)
        content_splitter.setStretchFactor(1, 2)
        v.addWidget(content_splitter, 1)
        self._action_bar_layout = QVBoxLayout()
        self._action_row_top = QHBoxLayout()
        self._action_row_bottom = QHBoxLayout()
        self._action_bar_layout.addLayout(self._action_row_top)
        self._action_bar_layout.addLayout(self._action_row_bottom)
        scaffold_btn = self._icon_button("document-new", "Scaffold Plugin")
        inspect_btn = self._icon_button("edit-find", "Inspect Plugin Zip")
        install_btn = self._icon_button("document-open", "Install Plugin Zip")
        export_btn = self._icon_button("document-save", "Export Plugin")
        export_diag_btn = self._icon_button("ai-citations", "Export Diagnostics")
        export_logs_btn = self._icon_button("ai-changelog", "Export Logs")
        reset_failures_btn = self._icon_button("collab-resolve", "Reset Failures")
        retry_plugin_btn = self._icon_button("sync-horizontal", "Retry Plugin")
        plugin_settings_btn = self._icon_button("language-define", "Plugin Settings")
        update_btn = self._icon_button("sync-vertical", "Check Update")
        update_all_btn = self._icon_button("sync-horizontal", "Check All Updates")
        run_command_btn = self._icon_button("macro-run-multi", "Run Command")
        diagnostics_btn = self._icon_button("document-list", "Refresh Diagnostics")
        reload_btn = self._icon_button("sync-vertical", "Reload")
        clear_quarantine_btn = self._icon_button("ai-clear", "Clear Quarantine")
        reset_perms_btn = self._icon_button("collab-resolve", "Reset to requested defaults")
        close_btn = self._icon_button("tab-close", "Close")
        self._action_buttons: list[QToolButton] = [
            scaffold_btn,
            inspect_btn,
            install_btn,
            export_btn,
            export_diag_btn,
            export_logs_btn,
            reset_failures_btn,
            retry_plugin_btn,
            plugin_settings_btn,
            update_btn,
            update_all_btn,
            run_command_btn,
            diagnostics_btn,
            reload_btn,
            clear_quarantine_btn,
            reset_perms_btn,
        ]
        self._close_button = close_btn
        v.addLayout(self._action_bar_layout)
        self._relayout_action_buttons()
        scaffold_btn.clicked.connect(self._scaffold_plugin)
        inspect_btn.clicked.connect(self._inspect_plugin_zip)
        install_btn.clicked.connect(self._install_plugin_zip)
        export_btn.clicked.connect(self._export_plugin)
        export_diag_btn.clicked.connect(self._export_plugin_diagnostics)
        export_logs_btn.clicked.connect(self._export_plugin_logs)
        reset_failures_btn.clicked.connect(self._reset_selected_plugin_failures)
        retry_plugin_btn.clicked.connect(self._retry_selected_plugin)
        plugin_settings_btn.clicked.connect(self._open_plugin_settings)
        update_btn.clicked.connect(self._check_selected_plugin_update)
        update_all_btn.clicked.connect(self._check_all_plugin_updates)
        run_command_btn.clicked.connect(self._run_selected_command)
        diagnostics_btn.clicked.connect(self._refresh_diagnostics)
        reload_btn.clicked.connect(self._reload)
        clear_quarantine_btn.clicked.connect(self._clear_quarantine)
        reset_perms_btn.clicked.connect(self._reset_permission_overrides)
        close_btn.clicked.connect(self.accept)
        self._populate()

    def _icon_button(self, icon_name: str, tooltip: str) -> QToolButton:
        btn = QToolButton(self)
        btn.setAutoRaise(False)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(28, 28)
        btn.setIconSize(btn.size() - QSize(10, 10))
        window = self.host.window
        icon = None
        if hasattr(window, "_svg_icon"):
            try:
                icon = window._svg_icon(icon_name)
            except Exception:
                icon = None
        if icon is not None:
            btn.setIcon(icon)
        return btn

    def _clear_layout(self, layout: QHBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(self)

    def _relayout_action_buttons(self) -> None:
        self._clear_layout(self._action_row_top)
        self._clear_layout(self._action_row_bottom)
        available = max(220, self.width() - 80)
        per_button = 32
        max_top = max(6, min(len(self._action_buttons), available // per_button))
        if len(self._action_buttons) <= max_top:
            top_items = list(self._action_buttons)
            bottom_items: list[QToolButton] = []
        else:
            split = (len(self._action_buttons) + 1) // 2
            top_items = self._action_buttons[:split]
            bottom_items = self._action_buttons[split:]
        for btn in top_items:
            self._action_row_top.addWidget(btn)
        self._action_row_top.addStretch(1)
        self._action_row_top.addWidget(self._close_button)
        if bottom_items:
            for btn in bottom_items:
                self._action_row_bottom.addWidget(btn)
            self._action_row_bottom.addStretch(1)

    def resizeEvent(self, event):  # type: ignore[override]
        super().resizeEvent(event)
        self._relayout_action_buttons()

    def _populate(self) -> None:
        self.list_widget.clear()
        self._visible_plugin_ids = []
        query = self.search_input.text().strip().lower()
        records = self.host.discover()
        for rec in records:
            hay = " ".join(
                [
                    rec.plugin_id,
                    rec.name,
                    rec.description,
                    " ".join(sorted(rec.permissions)),
                    " ".join(sorted(rec.requested_permissions)),
                ]
            ).lower()
            if query and query not in hay:
                continue
            self._visible_plugin_ids.append(rec.plugin_id)
            holder = QListWidgetItem(self.list_widget)
            item_widget = QWidget(self.list_widget)
            outer = QVBoxLayout(item_widget)
            outer.setContentsMargins(6, 4, 6, 4)
            top = QHBoxLayout()
            check = QCheckBox(f"{rec.name} ({rec.plugin_id})", item_widget)
            check.setChecked(rec.enabled)
            if rec.security_issues:
                state = "BLOCKED"
            elif rec.compatibility_issues:
                state = "INCOMPATIBLE"
            else:
                if rec.instance is not None:
                    state = "LOADED"
                else:
                    state = "QUARANTINED" if rec.quarantined else "ok"
            requested = ", ".join(sorted(rec.requested_permissions)) or "none"
            effective = ", ".join(sorted(rec.permissions)) or "none"
            meta_parts = []
            if rec.metadata.get("version"):
                meta_parts.append(f"ver: {rec.metadata.get('version')}")
            if rec.metadata.get("author"):
                meta_parts.append(f"author: {rec.metadata.get('author')}")
            if rec.metadata.get("plugin_api_version"):
                meta_parts.append(f"api: {rec.metadata.get('plugin_api_version')}")
            if rec.metadata.get("min_app_version") or rec.metadata.get("max_app_version"):
                meta_parts.append(
                    f"compat: {rec.metadata.get('min_app_version') or '-'}..{rec.metadata.get('max_app_version') or '-'}"
                )
            details = (
                (
                    f"{rec.description} | perms: {effective} | requested: {requested} | "
                    f"state: {state} | sha256: {rec.digest[:12]}... | policy: {rec.security_issues[0]}"
                )
                if rec.security_issues
                else (
                    f"{rec.description} | perms: {effective} | requested: {requested} | "
                    f"state: {state} | sha256: {rec.digest[:12]}..."
                    + (f" | {' | '.join(meta_parts)}" if meta_parts else "")
                    + (f" | compat_issue: {rec.compatibility_issues[0]}" if rec.compatibility_issues else "")
                )
            )
            info = QLabel(
                details,
                item_widget,
            )
            top.addWidget(check)
            top.addWidget(info, 1)
            outer.addLayout(top)
            if rec.requested_permissions:
                perms_row = QHBoxLayout()
                perms_label = QLabel("Permissions:", item_widget)
                perms_row.addWidget(perms_label)
                perm_checks: dict[str, QCheckBox] = {}
                for perm in sorted(rec.requested_permissions):
                    cb = QCheckBox(perm, item_widget)
                    cb.setChecked(perm in rec.permissions)
                    cb.setEnabled(not rec.security_issues)
                    perm_checks[perm] = cb
                    perms_row.addWidget(cb)

                def _persist_permissions(pid=rec.plugin_id, requested_perms=set(rec.requested_permissions), checks=perm_checks):
                    allowed = {p for p, box in checks.items() if box.isChecked()}
                    if allowed == set(requested_perms):
                        self.host.set_permission_override(pid, None)
                    else:
                        self.host.set_permission_override(pid, allowed)

                for perm, cb in perm_checks.items():
                    cb.toggled.connect(lambda _val, _pid=rec.plugin_id: _persist_permissions(_pid))
                perms_row.addStretch(1)
                outer.addLayout(perms_row)
            holder.setSizeHint(item_widget.sizeHint())
            self.list_widget.addItem(holder)
            self.list_widget.setItemWidget(holder, item_widget)
            if rec.security_issues:
                check.setEnabled(False)
            if rec.compatibility_issues:
                check.setEnabled(False)
            check.toggled.connect(lambda val, pid=rec.plugin_id: self.host.set_enabled(pid, val))
        self._refresh_diagnostics()

    def _reload(self) -> None:
        self.host.reload()
        self._populate()

    def _clear_quarantine(self) -> None:
        self.host.window.settings["quarantined_plugins"] = []
        self.host.window.save_settings_to_disk()
        self._populate()

    def _reset_permission_overrides(self) -> None:
        self.host.reset_permission_overrides()
        self._populate()

    def _toggle_unsafe_ui_bridge(self, enabled: bool) -> None:
        self.host.window.settings["plugin_allow_unsafe_ui_bridge"] = bool(enabled)
        self.host.window.save_settings_to_disk()

    def _toggle_dev_repo_plugins_source(self, enabled: bool) -> None:
        if self.host.runtime_mode_label() != "development":
            return
        self.host.set_dev_plugins_source(bool(enabled))
        source = "..\\plugins" if enabled else "AppData plugins folder"
        self.host.window.show_status_message(f"Plugin source switched to: {source}", 3000)
        self._populate()

    def _scaffold_plugin(self) -> None:
        pid, ok = QInputDialog.getText(self, "Scaffold Plugin", "Plugin id (lowercase, 2-64 chars):")
        if not ok:
            return
        pid = str(pid or "").strip()
        if not pid:
            return
        name, ok = QInputDialog.getText(self, "Scaffold Plugin", "Display name:")
        if not ok:
            return
        if not str(name or "").strip():
            name = pid
        desc, ok = QInputDialog.getText(self, "Scaffold Plugin", "Description:")
        if not ok:
            return
        perms_text, ok = QInputDialog.getText(
            self,
            "Scaffold Plugin",
            "Permissions (comma-separated, default: menu):",
            text="menu",
        )
        if not ok:
            return
        perms = {part.strip().lower() for part in str(perms_text or "").split(",") if part.strip()}
        try:
            path = self.host.scaffold_plugin(
                plugin_id=pid,
                name=str(name or pid),
                description=str(desc or ""),
                permissions=perms,
            )
        except Exception as exc:
            QMessageBox.warning(self, "Scaffold Plugin", f"Could not create plugin:\n{exc}")
            return
        self.host.window.show_status_message(f"Plugin scaffold created: {path}", 3000)
        self._populate()

    def _selected_plugin_record(self) -> PluginRecord | None:
        row = int(self.list_widget.currentRow())
        if row < 0 or row >= len(self._visible_plugin_ids):
            return None
        pid = self._visible_plugin_ids[row]
        rec = next((x for x in self.host.discover() if x.plugin_id == pid), None)
        if rec is None:
            return None
        runtime = next((x for x in self.host.records if x.plugin_id == rec.plugin_id), None)
        return runtime or rec

    def _refresh_diagnostics(self) -> None:
        rec = self._selected_plugin_record()
        if rec is None:
            self.diagnostics_view.setPlainText("Select a plugin to view runtime diagnostics.")
            return
        hooks = ", ".join(f"{k}={v}" for k, v in sorted(rec.hook_counts.items())) or "(none)"
        lines = [
            f"Plugin: {rec.name} ({rec.plugin_id})",
            f"Description: {rec.description}",
            f"Version: {rec.metadata.get('version', '') or '(unknown)'}",
            f"Author: {rec.metadata.get('author', '') or '(unknown)'}",
            f"Plugin API Version: {rec.metadata.get('plugin_api_version', '') or '(unknown)'}",
            f"Supported Plugin API: {PLUGIN_API_VERSION}",
            f"App Version: {self.host.app_version}",
            f"Compatibility Range: min={rec.metadata.get('min_app_version', '') or '-'} max={rec.metadata.get('max_app_version', '') or '-'}",
            f"Permissions: {', '.join(sorted(rec.permissions)) or 'none'}",
            f"Requested Permissions: {', '.join(sorted(rec.requested_permissions)) or 'none'}",
            f"Settings Schema Keys: {', '.join(sorted(rec.settings_schema.keys())) or '(none)'}",
            f"Dependencies: {', '.join(sorted(rec.dependencies)) or '(none)'}",
            f"Provides Services: {', '.join(sorted(rec.provided_services)) or '(none)'}",
            f"Requires Services: {', '.join(sorted(rec.required_services)) or '(none)'}",
            f"Enabled: {rec.enabled}",
            f"Loaded: {rec.instance is not None}",
            f"Failure Count: {rec.failure_count}",
            f"Health Score: {self.host.plugin_health_score(rec)}/100",
            f"Load Count: {rec.load_count}",
            f"Last Run: {rec.last_run_at or '-'}",
            f"Last Event: {rec.last_event_at or '-'}",
            f"Last Error At: {rec.last_error_at or '-'}",
            f"Last Error: {rec.last_error or '-'}",
            f"Hook Counters: {hooks}",
            f"Security Issues: {'; '.join(rec.security_issues) if rec.security_issues else '(none)'}",
            f"Compatibility Issues: {'; '.join(rec.compatibility_issues) if rec.compatibility_issues else '(none)'}",
            f"Update URL: {rec.metadata.get('update_url', '') or '-'}",
            f"Homepage: {rec.metadata.get('homepage', '') or '-'}",
            f"Runtime Event Entries: {len(rec.runtime_events)}",
        ]
        jobs = list(self.host._job_registry.get(rec.plugin_id, {}).values())[:20]
        lines.append(f"Jobs Tracked: {len(jobs)}")
        for j in jobs:
            lines.append(
                f"- {j.get('job_name', 'job')} ({j.get('job_id', '?')}) status={j.get('status', '?')} progress={j.get('progress', 0.0)}"
            )
        cmd_specs = self.host.list_plugin_commands(rec.plugin_id)
        lines.append(f"Registered Commands: {len(cmd_specs)}")
        if cmd_specs:
            for cmd in cmd_specs[:20]:
                lines.append(f"- {cmd.get('name')} :: {cmd.get('description', '')}")
        if rec.runtime_events:
            lines.append("Recent Runtime Events:")
            for row in rec.runtime_events[-5:]:
                lines.append(
                    f"- {row.get('ts', '?')} | {row.get('event', '?')} | {json.dumps(row.get('payload', {}), ensure_ascii=True)}"
                )
        logs = self.host.plugin_logs(rec.plugin_id)
        lines.append(f"Plugin Logs: {len(logs)}")
        if logs:
            lines.append("Recent Plugin Logs:")
            for row in logs[-8:]:
                lines.append(f"- {row.get('ts', '?')} [{row.get('level', 'INFO')}] {row.get('message', '')}")
        self.diagnostics_view.setPlainText("\n".join(lines))

    def _export_plugin(self) -> None:
        rec = self._selected_plugin_record()
        if rec is None:
            QMessageBox.information(self, "Export Plugin", "Select a plugin first.")
            return
        default_name = f"{rec.plugin_id}-{rec.metadata.get('version', '') or '1.0.0'}.zip"
        path, _ = QFileDialog.getSaveFileName(self, "Export Plugin", str(self.host.plugins_dir / default_name), "Zip Files (*.zip)")
        if not path:
            return
        out = Path(path)
        if out.suffix.lower() != ".zip":
            out = out.with_suffix(".zip")
        try:
            self.host.export_plugin(rec.plugin_id, out)
        except Exception as exc:
            QMessageBox.warning(self, "Export Plugin", f"Failed to export plugin:\n{exc}")
            return
        self.host.window.show_status_message(f"Plugin exported: {out}", 3500)

    def _run_selected_command(self) -> None:
        rec = self._selected_plugin_record()
        if rec is None:
            QMessageBox.information(self, "Run Command", "Select a plugin first.")
            return
        commands = self.host.list_plugin_commands(rec.plugin_id)
        if not commands:
            QMessageBox.information(self, "Run Command", "Selected plugin has no registered commands.")
            return
        labels = [f"{c['name']} - {c.get('description', '')}".strip() for c in commands]
        choice, ok = QInputDialog.getItem(self, "Run Command", "Command:", labels, 0, False)
        if not ok or not choice:
            return
        selected_name = commands[labels.index(choice)]["name"]
        args_text, ok = QInputDialog.getText(
            self,
            "Run Command",
            "Args JSON object (optional):",
            text="{}",
        )
        if not ok:
            return
        try:
            args = json.loads(str(args_text or "{}").strip() or "{}")
            if not isinstance(args, dict):
                raise ValueError("Args must be a JSON object.")
        except Exception as exc:
            QMessageBox.warning(self, "Run Command", f"Invalid args JSON:\n{exc}")
            return
        try:
            result = self.host.run_plugin_command(rec.plugin_id, selected_name, args)
        except Exception as exc:
            QMessageBox.warning(self, "Run Command", f"Command failed:\n{exc}")
            return
        if result is not None:
            self.host.window.show_status_message(f"Command '{selected_name}' returned: {result}", 3000)
        else:
            self.host.window.show_status_message(f"Command '{selected_name}' executed.", 2500)
        self._refresh_diagnostics()

    def _inspect_plugin_zip(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Inspect Plugin Zip", str(self.host.plugins_dir), "Zip Files (*.zip)")
        if not path:
            return
        try:
            info = self.host.inspect_plugin_archive(Path(path))
        except Exception as exc:
            QMessageBox.warning(self, "Inspect Plugin Zip", f"Could not inspect archive:\n{exc}")
            return
        lines = [
            f"Plugin ID: {info.get('plugin_id', '')}",
            f"Name: {info.get('name', '')}",
            f"Author: {info.get('author', '') or '-'}",
            f"Version: {info.get('version', '')}",
            f"Requested permissions: {', '.join(info.get('requested_permissions', [])) or 'none'}",
        ]
        issues = list(info.get("issues", []) or [])
        if issues:
            lines.append("")
            lines.append("Policy issues:")
            lines.extend([f"- {x}" for x in issues[:12]])
        else:
            lines.append("")
            lines.append("Policy issues: none")
        QMessageBox.information(self, "Inspect Plugin Zip", "\n".join(lines))

    def _install_plugin_zip(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Install Plugin from Zip", str(self.host.plugins_dir), "Zip Files (*.zip)")
        if not path:
            return
        try:
            installed = self.host.install_plugin_archive(Path(path))
        except Exception as exc:
            QMessageBox.warning(self, "Install Plugin", f"Failed to install plugin:\n{exc}")
            return
        self.host.window.show_status_message(f"Plugin installed: {installed.name}", 3200)
        self._populate()

    def _check_selected_plugin_update(self) -> None:
        rec = self._selected_plugin_record()
        if rec is None:
            QMessageBox.information(self, "Check Update", "Select a plugin first.")
            return
        info = self.host.check_plugin_update(rec)
        if info.get("error"):
            QMessageBox.information(self, "Check Update", f"Update check failed:\n{info.get('error')}")
            return
        latest = str(info.get("latest_version", "") or "")
        current = str(info.get("current_version", "") or "")
        if bool(info.get("update_available", False)):
            QMessageBox.information(
                self,
                "Check Update",
                f"Update available for {rec.plugin_id}:\nCurrent: {current}\nLatest: {latest}\nURL: {info.get('update_url', '')}",
            )
        else:
            QMessageBox.information(
                self,
                "Check Update",
                f"No update available for {rec.plugin_id}.\nCurrent: {current}\nLatest: {latest or current}",
            )

    def _check_all_plugin_updates(self) -> None:
        results = self.host.check_all_plugin_updates()
        if not results:
            QMessageBox.information(self, "Check All Updates", "No plugins found.")
            return
        lines = []
        updates = 0
        errors = 0
        for row in results:
            pid = str(row.get("plugin_id", "") or "")
            cur = str(row.get("current_version", "") or "")
            latest = str(row.get("latest_version", "") or "")
            if row.get("error"):
                errors += 1
                lines.append(f"- {pid}: error -> {row.get('error')}")
                continue
            if bool(row.get("update_available", False)):
                updates += 1
                lines.append(f"- {pid}: UPDATE {cur} -> {latest}")
            else:
                lines.append(f"- {pid}: up-to-date ({cur})")
        summary = f"Updates: {updates} | Errors: {errors} | Total: {len(results)}"
        QMessageBox.information(self, "Check All Updates", summary + "\n\n" + "\n".join(lines[:40]))

    def _export_plugin_diagnostics(self) -> None:
        rec = self._selected_plugin_record()
        if rec is None:
            QMessageBox.information(self, "Export Diagnostics", "Select a plugin first.")
            return
        default_name = f"{rec.plugin_id}_diagnostics.json"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Plugin Diagnostics",
            str(self.host.plugins_dir / default_name),
            "JSON Files (*.json)",
        )
        if not path:
            return
        out = Path(path)
        if out.suffix.lower() != ".json":
            out = out.with_suffix(".json")
        snapshot = self.host.plugin_diagnostics_snapshot(rec)
        try:
            out.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        except Exception as exc:
            QMessageBox.warning(self, "Export Diagnostics", f"Could not write diagnostics:\n{exc}")
            return
        self.host.window.show_status_message(f"Plugin diagnostics exported: {out}", 3200)

    def _retry_selected_plugin(self) -> None:
        rec = self._selected_plugin_record()
        if rec is None:
            QMessageBox.information(self, "Retry Plugin", "Select a plugin first.")
            return
        quarantined = self.host.window.settings.get("quarantined_plugins", [])
        if isinstance(quarantined, list):
            self.host.window.settings["quarantined_plugins"] = [x for x in quarantined if str(x) != rec.plugin_id]
        self.host.reset_plugin_failure_count(rec.plugin_id)
        enabled = self.host._enabled()
        enabled.add(rec.plugin_id)
        self.host._save_enabled(enabled)
        self.host.reload()
        self._populate()
        self.host.window.show_status_message(f"Retried plugin: {rec.plugin_id}", 2500)

    def _open_plugin_settings(self) -> None:
        rec = self._selected_plugin_record()
        if rec is None:
            QMessageBox.information(self, "Plugin Settings", "Select a plugin first.")
            return
        schema = dict(rec.settings_schema or {})
        if not schema:
            QMessageBox.information(self, "Plugin Settings", "Selected plugin has no settings schema.")
            return
        cfg = self.host._plugin_config_map().get(rec.plugin_id, {})
        if not isinstance(cfg, dict):
            cfg = {}
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Plugin Settings - {rec.name}")
        form = QFormLayout(dlg)
        editors: dict[str, tuple[str, QWidget]] = {}
        for key in sorted(schema.keys()):
            spec = schema.get(key, {})
            if not isinstance(spec, dict):
                continue
            typ = str(spec.get("type", "str")).strip().lower()
            label = str(spec.get("label", key) or key)
            value = cfg.get(key, spec.get("default", ""))
            if isinstance(spec.get("enum"), list) and spec.get("enum"):
                combo = QComboBox(dlg)
                enum_values = [str(x) for x in spec.get("enum", [])]
                combo.addItems(enum_values)
                current_text = str(value if value is not None else "")
                idx = combo.findText(current_text)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                editors[key] = ("enum", combo)
                form.addRow(label + ":", combo)
                continue
            if typ in {"bool", "boolean"}:
                check = QCheckBox(dlg)
                check.setChecked(bool(value) if isinstance(value, bool) else str(value).strip().lower() in {"1", "true", "yes", "on"})
                editors[key] = ("bool", check)
                form.addRow(label + ":", check)
            elif typ in {"int", "integer"}:
                spin = QSpinBox(dlg)
                spin.setRange(int(spec.get("min", -1000000)), int(spec.get("max", 1000000)))
                try:
                    spin.setValue(int(value))
                except Exception:
                    spin.setValue(int(spec.get("default", 0) or 0))
                editors[key] = ("int", spin)
                form.addRow(label + ":", spin)
            elif typ in {"float", "number"}:
                dspin = QDoubleSpinBox(dlg)
                dspin.setRange(float(spec.get("min", -1000000.0)), float(spec.get("max", 1000000.0)))
                dspin.setDecimals(6)
                try:
                    dspin.setValue(float(value))
                except Exception:
                    dspin.setValue(float(spec.get("default", 0.0) or 0.0))
                editors[key] = ("float", dspin)
                form.addRow(label + ":", dspin)
            else:
                edit = QLineEdit(dlg)
                edit.setText(str(value if value is not None else ""))
                editors[key] = ("str", edit)
                form.addRow(label + ":", edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, Qt.Orientation.Horizontal, dlg)
        form.addRow(buttons)
        buttons.rejected.connect(dlg.reject)

        def _save() -> None:
            try:
                for key, (kind, widget) in editors.items():
                    if kind == "bool":
                        value = bool(widget.isChecked()) if hasattr(widget, "isChecked") else False
                    elif kind == "int":
                        value = int(widget.value()) if hasattr(widget, "value") else 0
                    elif kind == "float":
                        value = float(widget.value()) if hasattr(widget, "value") else 0.0
                    elif kind == "enum":
                        value = str(widget.currentText()) if hasattr(widget, "currentText") else ""
                    else:
                        value = str(widget.text()) if hasattr(widget, "text") else ""
                    self.host.set_plugin_config(rec.plugin_id, key, value)
            except Exception as exc:
                QMessageBox.warning(dlg, "Plugin Settings", f"Could not save settings:\n{exc}")
                return
            dlg.accept()

        buttons.accepted.connect(_save)
        dlg.exec()
        self._refresh_diagnostics()

    def _export_plugin_logs(self) -> None:
        rec = self._selected_plugin_record()
        if rec is None:
            QMessageBox.information(self, "Export Logs", "Select a plugin first.")
            return
        logs = self.host.plugin_logs(rec.plugin_id)
        if not logs:
            QMessageBox.information(self, "Export Logs", "Selected plugin has no logs.")
            return
        default_name = f"{rec.plugin_id}_logs.txt"
        path, _ = QFileDialog.getSaveFileName(self, "Export Plugin Logs", str(self.host.plugins_dir / default_name), "Text Files (*.txt)")
        if not path:
            return
        out = Path(path)
        if out.suffix.lower() != ".txt":
            out = out.with_suffix(".txt")
        lines = [f"{row.get('ts','?')} [{row.get('level','INFO')}] {row.get('message','')}" for row in logs]
        try:
            out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception as exc:
            QMessageBox.warning(self, "Export Logs", f"Could not write logs:\n{exc}")
            return
        self.host.window.show_status_message(f"Plugin logs exported: {out}", 3000)

    def _reset_selected_plugin_failures(self) -> None:
        rec = self._selected_plugin_record()
        if rec is None:
            QMessageBox.information(self, "Reset Failures", "Select a plugin first.")
            return
        self.host.reset_plugin_failure_count(rec.plugin_id)
        self.host.window.show_status_message(f"Reset failure count: {rec.plugin_id}", 2500)
        self._populate()


class OnlinePluginsDialog(QDialog):
    def __init__(self, parent, host: PluginHost) -> None:
        super().__init__(parent)
        self.host = host
        self._entries: list[dict[str, str]] = []
        self.setWindowTitle("Online Plugins")
        self.resize(700, 420)
        v = QVBoxLayout(self)
        self.list_widget = QListWidget(self)
        self.list_widget.setToolTip("Plugins available from the online catalog.")
        v.addWidget(self.list_widget, 1)
        self.details = QTextEdit(self)
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("Select an online plugin to see details.")
        v.addWidget(self.details, 1)
        row = QHBoxLayout()
        self.refresh_btn = QToolButton(self)
        self.refresh_btn.setToolTip("Refresh catalog")
        self.refresh_btn.setIconSize(QSize(18, 18))
        self.refresh_btn.setFixedSize(30, 30)
        self.install_btn = QToolButton(self)
        self.install_btn.setToolTip("Install selected plugin")
        self.install_btn.setIconSize(QSize(18, 18))
        self.install_btn.setFixedSize(30, 30)
        self.close_btn = QToolButton(self)
        self.close_btn.setToolTip("Close")
        self.close_btn.setIconSize(QSize(18, 18))
        self.close_btn.setFixedSize(30, 30)
        for btn, icon_name in (
            (self.refresh_btn, "plugin-online"),
            (self.install_btn, "plugin-install"),
            (self.close_btn, "tab-close"),
        ):
            icon = None
            if hasattr(self.host.window, "_svg_icon"):
                try:
                    icon = self.host.window._svg_icon(icon_name)
                except Exception:
                    icon = None
            if icon is not None:
                btn.setIcon(icon)
        row.addWidget(self.refresh_btn)
        row.addWidget(self.install_btn)
        row.addStretch(1)
        row.addWidget(self.close_btn)
        v.addLayout(row)
        self.list_widget.currentRowChanged.connect(self._refresh_details)
        self.refresh_btn.clicked.connect(self._populate)
        self.install_btn.clicked.connect(self._install_selected)
        self.close_btn.clicked.connect(self.accept)
        self._populate()

    def _populate(self) -> None:
        self.list_widget.clear()
        self.details.clear()
        self._entries = self.host.load_online_plugin_catalog()
        installed_ids = {rec.plugin_id for rec in self.host.discover()}
        for row in self._entries:
            plugin_id = str(row.get("id", "") or "")
            name = str(row.get("name", plugin_id) or plugin_id)
            version = str(row.get("version", "") or "")
            author = str(row.get("author", "") or "")
            status = "installed" if plugin_id in installed_ids else "available"
            text = f"{name} ({plugin_id}) | {status}"
            if version:
                text += f" | v{version}"
            if author:
                text += f" | by {author}"
            self.list_widget.addItem(QListWidgetItem(text))
        self._refresh_details()

    def _refresh_details(self) -> None:
        idx = int(self.list_widget.currentRow())
        if idx < 0 or idx >= len(self._entries):
            self.details.setPlainText("Select an online plugin to see details.")
            return
        row = self._entries[idx]
        lines = [
            f"Name: {row.get('name', '')}",
            f"ID: {row.get('id', '')}",
            f"Version: {row.get('version', '') or '-'}",
            f"Author: {row.get('author', '') or '-'}",
            f"Description: {row.get('description', '') or '-'}",
            f"Repository: {row.get('repo', '') or '-'}",
            f"Source: {row.get('source', '') or '-'}",
            f"Homepage: {row.get('homepage', '') or '-'}",
        ]
        self.details.setPlainText("\n".join(lines))

    def _install_selected(self) -> None:
        idx = int(self.list_widget.currentRow())
        if idx < 0 or idx >= len(self._entries):
            QMessageBox.information(self, "Online Plugins", "Select an online plugin first.")
            return
        entry = self._entries[idx]
        plugin_id = str(entry.get("id", "") or "")
        try:
            out = self.host.install_online_plugin(entry)
        except Exception as exc:
            QMessageBox.warning(self, "Online Plugins", f"Failed to install '{plugin_id}':\n{exc}")
            return
        self.host.window.show_status_message(f"Online plugin installed: {out.name}", 3200)
        self.host.reload()
        self._populate()


class MinimapDock(QDockWidget):
    def __init__(self, parent) -> None:
        super().__init__("Minimap", parent)
        self.text = QTextEdit(self)
        self.text.setObjectName("minimapText")
        self.text.setReadOnly(True)
        f = self.text.font()
        f.setPointSize(max(6, f.pointSize() - 4))
        f.setFamily("Consolas")
        self.text.setFont(f)
        self.text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.setWidget(self.text)
        self._apply_theme()

    def _apply_theme(self) -> None:
        parent = self.parentWidget()
        settings = getattr(parent, "settings", {}) if parent is not None else {}
        tokens = build_tokens_from_settings(settings if isinstance(settings, dict) else {})
        self.text.setStyleSheet(
            f"""
            QTextEdit#minimapText {{
                background: {tokens.input_bg};
                color: {tokens.text_muted};
                border: 1px solid {tokens.border};
                border-radius: {tokens.radius_sm}px;
                selection-background-color: {tokens.accent};
                selection-color: {tokens.text_on_accent};
                padding: 2px;
            }}
            """
        )

    def refresh(self, src: str, *, show_line_numbers: bool = False) -> None:
        self._apply_theme()
        lines = src.splitlines()[:1800]
        if show_line_numbers:
            rendered = [f"{idx + 1:5d}  {line}" for idx, line in enumerate(lines)]
        else:
            rendered = lines
        self.text.setPlainText("\n".join(rendered))


class OutlineDock(QDockWidget):
    def __init__(self, parent, jump_cb) -> None:
        super().__init__("Symbol Outline", parent)
        self.jump_cb = jump_cb
        self.list_widget = QListWidget(self)
        self.setWidget(self.list_widget)
        self.list_widget.itemDoubleClicked.connect(self._jump)

    def _jump(self, item: QListWidgetItem) -> None:
        line = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(line, int):
            self.jump_cb(line)

    def refresh(self, language: str, text: str) -> None:
        self.list_widget.clear()
        rows: list[tuple[int, str]] = []
        if language == "python":
            try:
                tree = ast.parse(text)
                for n in ast.walk(tree):
                    if isinstance(n, ast.ClassDef):
                        rows.append((n.lineno - 1, f"class {n.name}"))
                    if isinstance(n, ast.FunctionDef):
                        rows.append((n.lineno - 1, f"def {n.name}"))
            except Exception:
                pass
        if language == "markdown":
            for i, ln in enumerate(text.splitlines()):
                if ln.strip().startswith("#"):
                    rows.append((i, ln.strip()))
        if not rows:
            for i, ln in enumerate(text.splitlines()):
                s = ln.strip()
                if re.match(r"^(class|def|function)\s+\w+", s):
                    rows.append((i, s))
        for line, title in rows[:500]:
            item = QListWidgetItem(f"{line + 1}: {title}")
            item.setData(Qt.ItemDataRole.UserRole, line)
            self.list_widget.addItem(item)


class CollaborationServer:
    def __init__(self, window) -> None:
        self.window = window
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._revision = 0
        self._events: list[dict[str, Any]] = []
        self._clients: dict[str, dict[str, Any]] = {}
        self._read_write = False
        self._session_text = ""

    def _presence_timeout_sec(self) -> int:
        try:
            return max(20, int(self.window.settings.get("collab_presence_timeout_sec", 120) or 120))
        except Exception:
            return 120

    def _prune_stale_clients_locked(self) -> None:
        now = int(time.time())
        timeout = self._presence_timeout_sec()
        stale = [cid for cid, row in self._clients.items() if (now - int(row.get("last_seen", now))) > timeout]
        for cid in stale:
            self._clients.pop(cid, None)

    def _ensure_token(self) -> str:
        token = str(self.window.settings.get("collab_token", "") or "").strip()
        if token:
            return token
        token = secrets.token_urlsafe(24)
        self.window.settings["collab_token"] = token
        self.window.save_settings_to_disk()
        return token

    def start(self, port: int, read_write: bool) -> None:
        if self.server is not None:
            return
        token = self._ensure_token()
        self._read_write = bool(read_write)
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def _send(self, code: int, payload: dict[str, Any]) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _raw_body(self) -> str:
                size = int(self.headers.get("Content-Length", "0") or 0)
                raw = (self.rfile.read(size) if size > 0 else b"") or b""
                return raw.decode("utf-8", errors="replace")

            def _read_json(self) -> tuple[dict[str, Any], str]:
                raw = self._raw_body()
                if not raw:
                    return {}, raw
                try:
                    data = json.loads(raw)
                except Exception:
                    return {}, raw
                return data if isinstance(data, dict) else {}, raw

            def _authorized(self) -> bool:
                auth = str(self.headers.get("Authorization", "") or "")
                if auth.startswith("Bearer "):
                    supplied = auth[7:].strip()
                else:
                    supplied = str(self.headers.get("X-Collab-Token", "") or "").strip()
                return bool(supplied) and hmac.compare_digest(supplied, token)

            def _verify_signature(self, method: str, path: str, raw_body: str) -> bool:
                timestamp = str(self.headers.get("X-Collab-Timestamp", "") or "").strip()
                signature = str(self.headers.get("X-Collab-Signature", "") or "").strip().lower()
                if not timestamp or not signature:
                    return False
                try:
                    ts = int(timestamp)
                except Exception:
                    return False
                now = int(time.time())
                if abs(now - ts) > 120:
                    return False
                payload = f"{method}\n{path}\n{timestamp}\n{raw_body}".encode("utf-8")
                expected = hmac.new(token.encode("utf-8"), payload, hashlib.sha256).hexdigest()
                return hmac.compare_digest(signature, expected)

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if not self._authorized():
                    self._send(403, {"error": "forbidden"})
                    return
                if parsed.path != "/state":
                    if parsed.path != "/events":
                        self._send(404, {"error": "not_found"})
                        return
                    since = parse_qs(parsed.query).get("since", ["0"])[0]
                    try:
                        since_rev = int(since)
                    except Exception:
                        since_rev = 0
                    with owner._lock:
                        events = [event for event in owner._events if int(event.get("rev", 0)) > since_rev]
                    self._send(200, {"events": events[-100:]})
                    return
                tab = owner.window.active_tab()
                with owner._lock:
                    owner._prune_stale_clients_locked()
                    revision = owner._revision
                    clients = len(owner._clients)
                    text = owner._session_text if owner._session_text else (tab.text_edit.get_text() if tab else "")
                    now = int(time.time())
                    rows = []
                    for cid, meta in sorted(owner._clients.items(), key=lambda row: str(row[1].get("name", "")).lower()):
                        name = str(meta.get("name", "client") or "client")
                        idle = max(0, now - int(meta.get("last_seen", now)))
                        rows.append(f"{name} ({cid[:8]}) idle:{idle}s")
                self._send(
                    200,
                    {
                        "text": text,
                        "rw": bool(owner._read_write),
                        "revision": revision,
                        "clients": clients,
                        "client_rows": rows,
                        "server_time": now,
                    },
                )

            def do_POST(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if not self._authorized():
                    self._send(403, {"error": "forbidden"})
                    return
                payload, raw_body = self._read_json()
                if parsed.path == "/join":
                    name = str(payload.get("name", "") or "client").strip()[:64] or "client"
                    client_id = str(payload.get("client_id", "") or "").strip()[:64] or uuid.uuid4().hex[:16]
                    with owner._lock:
                        owner._prune_stale_clients_locked()
                        owner._clients[client_id] = {"name": name, "last_seen": int(time.time())}
                        revision = owner._revision
                        text = owner._session_text
                    self._send(
                        200,
                        {"client_id": client_id, "revision": revision, "text": text},
                    )
                    return
                if parsed.path != "/edit":
                    self._send(404, {"error": "not_found"})
                    return
                if not owner._read_write:
                    self._send(403, {"error": "read_only"})
                    return
                if not self._verify_signature("POST", parsed.path, raw_body):
                    self._send(403, {"error": "bad_signature"})
                    return
                client_id = str(payload.get("client_id", "") or "").strip()
                base_revision = int(payload.get("base_revision", -1))
                operations = payload.get("operations", [])
                if not client_id or not isinstance(operations, list):
                    self._send(400, {"error": "bad_request"})
                    return
                with owner._lock:
                    owner._prune_stale_clients_locked()
                    if client_id not in owner._clients:
                        self._send(403, {"error": "unknown_client"})
                        return
                    owner._clients[client_id]["last_seen"] = int(time.time())
                    current_revision = owner._revision
                if base_revision != current_revision:
                    self._send(409, {"error": "revision_conflict", "current_revision": current_revision})
                    return
                with owner._lock:
                    current_text = owner._session_text
                try:
                    new_text = apply_text_operations(current_text, operations)
                except Exception as exc:
                    self._send(400, {"error": "invalid_operations", "detail": str(exc)})
                    return
                with owner._lock:
                    owner._session_text = new_text
                    owner._revision += 1
                    rev = owner._revision
                    owner._events.append(
                        {
                            "rev": rev,
                            "client_id": client_id,
                            "operations": operations[:50],
                            "timestamp": datetime.now().isoformat(timespec="seconds"),
                        }
                    )
                    owner._events = owner._events[-300:]
                QTimer.singleShot(0, lambda txt=new_text: owner._apply_session_text_to_active_tab(txt))
                self._send(200, {"ok": True, "revision": rev})

            def log_message(self, format: str, *args) -> None:  # noqa: A003
                return

        with self._lock:
            self._revision = 0
            self._events = []
            self._clients = {}
            tab = self.window.active_tab()
            self._session_text = tab.text_edit.get_text() if tab is not None else ""
        self.server = ThreadingHTTPServer(("127.0.0.1", int(port)), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.server is None:
            return
        self.server.shutdown()
        self.server.server_close()
        self.server = None
        self.thread = None

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            self._prune_stale_clients_locked()
            now = int(time.time())
            rows: list[str] = []
            for cid, meta in sorted(self._clients.items(), key=lambda row: str(row[1].get("name", "")).lower()):
                name = str(meta.get("name", "client") or "client")
                idle = max(0, now - int(meta.get("last_seen", now)))
                rows.append(f"{name} ({cid[:8]}) idle:{idle}s")
            return {
                "running": self.server is not None,
                "rw": bool(self._read_write),
                "revision": int(self._revision),
                "clients": len(self._clients),
                "client_rows": rows,
                "server_time": now,
            }

    def get_shared_text(self) -> str:
        with self._lock:
            return str(self._session_text)

    def set_shared_text(self, text: str, *, source: str = "host") -> int:
        with self._lock:
            self._session_text = str(text)
            self._revision += 1
            rev = self._revision
            self._events.append(
                {
                    "rev": rev,
                    "client_id": source,
                    "operations": [{"op": "replace", "start": 0, "end": 0, "text": "[full-sync]"}],
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }
            )
            self._events = self._events[-300:]
        return rev

    def _apply_session_text_to_active_tab(self, text: str) -> None:
        tab = self.window.active_tab()
        if tab is None or tab.text_edit.is_read_only():
            return
        tab.text_edit.set_text(text)
        tab.text_edit.set_modified(True)


class AdvancedFeaturesController:
    def __init__(self, window) -> None:
        self.window = window
        self.plugin_host = PluginHost(window)
        try:
            self.window.show_status_message(
                f"Plugins loaded from: {self.plugin_host.plugins_dir} ({self.plugin_host.runtime_mode_label()})",
                4500,
            )
        except Exception:
            pass
        self.minimap_dock = MinimapDock(window)
        self.minimap_dock.setObjectName("minimapDock")
        self.minimap_dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        if hasattr(window, "_install_custom_dock_title_bar"):
            window._install_custom_dock_title_bar(self.minimap_dock, "Minimap", "minimap_dock_title_bar")
        self.minimap_dock.hide()
        window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.minimap_dock)
        try:
            window.log_event("Info", "[Startup] Dock created: Minimap")
        except Exception:
            pass
        self.outline_dock = OutlineDock(window, self._jump_line)
        self.outline_dock.setObjectName("outlineDock")
        self.outline_dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        if hasattr(window, "_install_custom_dock_title_bar"):
            window._install_custom_dock_title_bar(self.outline_dock, "Symbol Outline", "outline_dock_title_bar")
        self.outline_dock.hide()
        window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.outline_dock)
        try:
            window.log_event("Info", "[Startup] Dock created: Outline")
        except Exception:
            pass
        self.collab = CollaborationServer(window)
        self.backup_timer = QTimer(window)
        self.backup_timer.timeout.connect(self.backup_now)
        self.apply_backup_schedule()

    def collaboration_snapshot(self) -> dict[str, Any]:
        return self.collab.snapshot()

    def collaboration_shared_text(self) -> str:
        return self.collab.get_shared_text()

    def collaboration_set_shared_text(self, text: str, *, source: str = "host") -> int:
        return self.collab.set_shared_text(text, source=source)

    def _jump_line(self, line: int) -> None:
        tab = self.window.active_tab()
        if tab is not None:
            tab.text_edit.set_cursor_position(max(0, line), 0)

    def refresh_views(self) -> None:
        tab = self.window.active_tab()
        if tab is None:
            self.minimap_dock.refresh("")
            self.outline_dock.refresh("plain", "")
            self.window._set_breadcrumb_text("-")
            return
        txt = tab.text_edit.get_text()
        self.minimap_dock.refresh(txt, show_line_numbers=not bool(tab.text_edit.is_scintilla))
        lang = self.window._detect_language_for_tab(tab)
        self.outline_dock.refresh(lang, txt)
        line, _ = tab.text_edit.cursor_position()
        self.window._set_breadcrumb_text(f"{tab.current_file or 'Untitled'} > line {line + 1}")

    def toggle_minimap(self, checked: bool) -> None:
        self.minimap_dock.setVisible(bool(checked))
        tab = self.window.active_tab()
        if checked and tab is not None and not bool(tab.text_edit.is_scintilla):
            self.window.show_status_message(
                "Minimap fallback mode: line-numbered text preview (QScintilla not available).",
                3000,
            )
        self.refresh_views()

    def toggle_outline(self, checked: bool) -> None:
        self.outline_dock.setVisible(bool(checked))
        self.refresh_views()

    def open_plugin_manager(self) -> None:
        PluginManagerDialog(self.window, self.plugin_host).exec()
        self.plugin_host.reload()

    def open_online_plugins(self) -> None:
        OnlinePluginsDialog(self.window, self.plugin_host).exec()
        self.plugin_host.reload()

    def go_to_definition(self) -> None:
        tab = self.window.active_tab()
        if tab is None:
            return
        symbol = tab.text_edit.selected_text().strip()
        line, col = tab.text_edit.cursor_position()
        source = tab.text_edit.get_text()
        if not symbol:
            try:
                current_line = source.splitlines()[line]
            except Exception:
                current_line = ""
            matches = list(re.finditer(r"[A-Za-z_][A-Za-z0-9_]*", current_line))
            for m in matches:
                if m.start() <= col <= m.end():
                    symbol = m.group(0)
                    break
        if not symbol:
            symbol, ok = QInputDialog.getText(self.window, "Go To Definition", "Symbol:")
            if not ok or not symbol.strip():
                return
            symbol = symbol.strip()

        language = str(self.window._detect_language_for_tab(tab) or "plain").lower()
        current_path = str(tab.current_file or "").strip()
        resolved = None
        if bool(self.window.settings.get("lsp_definition_enabled", True)):
            resolved = self._resolve_definition_with_lsp(
                language=language,
                file_path=current_path,
                line=line,
                col=col,
                source_text=source,
            )
        else:
            self._lsp_log("LSP definition lookup disabled by settings.")
        if resolved is None:
            resolved = self._resolve_definition_fallback(symbol=symbol, language=language, source_text=source, current_file=current_path)
        if resolved is None:
            self.window.show_status_message("Definition not found.", 2500)
            return

        target_path, target_line = resolved
        if target_path and target_path != current_path:
            if not self.window._open_file_path(target_path):
                self.window.show_status_message("Definition target could not be opened.", 2500)
                return
            tab = self.window.active_tab()
            if tab is None:
                return
        tab.text_edit.set_cursor_position(max(0, target_line), 0)
        shown_path = Path(target_path).name if target_path else "current file"
        self.window.show_status_message(f"Definition: {shown_path}:{target_line + 1}", 2800)

    def _lsp_log(self, message: str, *, level: str = "Info") -> None:
        if not bool(self.window.settings.get("lsp_definition_verbose_logging", False)):
            return
        try:
            self.window.log_event(level, f"[LSP] {message}")
        except Exception:
            pass

    def _resolve_lsp_candidates(self, *, language: str, file_path: str) -> tuple[str, list[list[str]]]:
        def _normalize_server_list(value: Any) -> list[str]:
            if isinstance(value, list):
                return [str(item).strip() for item in value if str(item).strip()]
            if isinstance(value, str) and value.strip():
                return [part.strip() for part in value.split(",") if part.strip()]
            return []

        if language == "python":
            language_id = "python"
            raw_commands = _normalize_server_list(self.window.settings.get("lsp_python_servers", []))
        elif language in {"typescript"} or file_path.lower().endswith((".ts", ".tsx")):
            language_id = "typescript"
            raw_commands = _normalize_server_list(self.window.settings.get("lsp_typescript_servers", []))
        elif language in {"javascript", "json"} or file_path.lower().endswith((".js", ".jsx", ".mjs", ".cjs")):
            language_id = "javascript"
            raw_commands = _normalize_server_list(self.window.settings.get("lsp_javascript_servers", []))
        else:
            return "", []
        candidates: list[list[str]] = []
        seen: set[tuple[str, ...]] = set()
        for raw in raw_commands:
            cmd_text = str(raw or "").strip()
            if not cmd_text:
                continue
            try:
                parts = shlex.split(cmd_text, posix=False)
            except Exception:
                parts = [cmd_text]
            cleaned = [str(p).strip().strip('"').strip("'") for p in parts if str(p).strip()]
            if not cleaned:
                continue
            key = tuple(cleaned)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(cleaned)
        return language_id, candidates

    @staticmethod
    def _lsp_wait_for_response(
        *,
        message_queue: "queue.Queue[dict[str, Any]]",
        request_id: int,
        timeout_sec: float,
    ) -> dict[str, Any] | None:
        deadline = time.monotonic() + max(0.1, float(timeout_sec))
        while time.monotonic() < deadline:
            remaining = max(0.05, deadline - time.monotonic())
            try:
                msg = message_queue.get(timeout=min(0.2, remaining))
            except queue.Empty:
                continue
            if not isinstance(msg, dict):
                continue
            if msg.get("id") == request_id:
                return msg
            if msg.get("__error__"):
                return None
            if msg.get("__eof__"):
                return None
        return None

    def _resolve_definition_with_lsp(
        self,
        *,
        language: str,
        file_path: str,
        line: int,
        col: int,
        source_text: str,
    ) -> tuple[str, int] | None:
        if not file_path:
            return None
        path_obj = Path(file_path)
        if not path_obj.exists():
            return None

        language_id, candidates = self._resolve_lsp_candidates(language=language, file_path=file_path)
        if not language_id or not candidates:
            return None

        init_timeout = float(self.window.settings.get("lsp_definition_initialize_timeout_sec", 5.0) or 5.0)
        request_timeout = float(self.window.settings.get("lsp_definition_request_timeout_sec", 3.0) or 3.0)
        retries = max(0, int(self.window.settings.get("lsp_definition_retries", 2) or 2))
        root = str(self.window._workspace_root() or path_obj.parent)
        uri = path_obj.resolve().as_uri()

        for cmd in candidates:
            if not shutil.which(cmd[0]):
                self._lsp_log(f"Server not found in PATH: {cmd[0]}")
                continue
            for attempt in range(retries + 1):
                proc: subprocess.Popen[bytes] | None = None
                try:
                    self._lsp_log(f"Trying server '{' '.join(cmd)}' (attempt {attempt + 1}/{retries + 1}).")
                    proc = subprocess.Popen(
                        cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        text=False,
                    )
                    if proc.stdin is None or proc.stdout is None:
                        raise RuntimeError("LSP subprocess missing stdio pipes.")
                    msg_queue: "queue.Queue[dict[str, Any]]" = queue.Queue()
                    stop_reader = threading.Event()

                    def _send(payload: dict[str, Any]) -> None:
                        body = json.dumps(payload).encode("utf-8")
                        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
                        proc.stdin.write(header + body)
                        proc.stdin.flush()

                    def _reader_loop() -> None:
                        try:
                            while not stop_reader.is_set():
                                header = b""
                                while b"\r\n\r\n" not in header:
                                    chunk = proc.stdout.read(1)
                                    if not chunk:
                                        msg_queue.put({"__eof__": True})
                                        return
                                    header += chunk
                                header_text = header.decode("ascii", errors="ignore")
                                content_length = 0
                                for ln in header_text.split("\r\n"):
                                    if ln.lower().startswith("content-length:"):
                                        try:
                                            content_length = int(ln.split(":", 1)[1].strip())
                                        except Exception:
                                            content_length = 0
                                        break
                                if content_length <= 0:
                                    continue
                                payload = proc.stdout.read(content_length)
                                if not payload:
                                    msg_queue.put({"__eof__": True})
                                    return
                                try:
                                    message = json.loads(payload.decode("utf-8", errors="replace"))
                                except Exception:
                                    continue
                                if isinstance(message, dict):
                                    msg_queue.put(message)
                        except Exception as exc:
                            msg_queue.put({"__error__": str(exc)})

                    reader = threading.Thread(target=_reader_loop, name="pypad-lsp-reader", daemon=True)
                    reader.start()

                    next_id = 1
                    init_id = next_id
                    next_id += 1
                    workspace_uri = Path(root).resolve().as_uri()
                    _send(
                        {
                            "jsonrpc": "2.0",
                            "id": init_id,
                            "method": "initialize",
                            "params": {
                                "processId": None,
                                "rootUri": workspace_uri,
                                "capabilities": {},
                                "workspaceFolders": [{"uri": workspace_uri, "name": Path(root).name or "workspace"}],
                            },
                        }
                    )
                    init_msg = self._lsp_wait_for_response(
                        message_queue=msg_queue,
                        request_id=init_id,
                        timeout_sec=init_timeout,
                    )
                    if init_msg is None:
                        self._lsp_log(f"Initialize timeout from '{cmd[0]}' after {init_timeout:.1f}s.", level="Warning")
                        continue
                    if init_msg.get("error"):
                        self._lsp_log(f"Initialize failed for '{cmd[0]}': {init_msg.get('error')}", level="Warning")
                        continue

                    _send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
                    _send(
                        {
                            "jsonrpc": "2.0",
                            "method": "textDocument/didOpen",
                            "params": {
                                "textDocument": {
                                    "uri": uri,
                                    "languageId": language_id,
                                    "version": 1,
                                    "text": source_text,
                                }
                            },
                        }
                    )
                    def_id = next_id
                    next_id += 1
                    _send(
                        {
                            "jsonrpc": "2.0",
                            "id": def_id,
                            "method": "textDocument/definition",
                            "params": {
                                "textDocument": {"uri": uri},
                                "position": {"line": max(0, int(line)), "character": max(0, int(col))},
                            },
                        }
                    )
                    location_msg = self._lsp_wait_for_response(
                        message_queue=msg_queue,
                        request_id=def_id,
                        timeout_sec=request_timeout,
                    )
                    if location_msg is None:
                        self._lsp_log(f"Definition timeout from '{cmd[0]}' after {request_timeout:.1f}s.", level="Warning")
                        continue
                    if location_msg.get("error"):
                        self._lsp_log(f"Definition request failed for '{cmd[0]}': {location_msg.get('error')}", level="Warning")
                        continue

                    result = location_msg.get("result")
                    target = None
                    if isinstance(result, list) and result:
                        target = result[0]
                    elif isinstance(result, dict):
                        target = result
                    if not isinstance(target, dict):
                        self._lsp_log(f"No definition target returned by '{cmd[0]}'.")
                        continue
                    target_uri = str(target.get("uri") or target.get("targetUri") or uri)
                    rng = target.get("range") or target.get("targetSelectionRange") or target.get("targetRange") or {}
                    start = rng.get("start", {}) if isinstance(rng, dict) else {}
                    target_line = int(start.get("line", 0) or 0)
                    if target_uri.startswith("file://"):
                        parsed = urlparse(target_uri)
                        target_path = unquote(parsed.path.lstrip("/")) if parsed.path else file_path
                        if re.match(r"^[A-Za-z]:", target_uri[8:10]):
                            target_path = unquote(target_uri[8:])
                    else:
                        target_path = file_path
                    self._lsp_log(f"Definition resolved via '{cmd[0]}' -> {target_path}:{target_line + 1}")
                    return str(Path(target_path)), max(0, target_line)
                except Exception as exc:
                    self._lsp_log(f"Server '{' '.join(cmd)}' attempt {attempt + 1} failed: {exc}", level="Warning")
                    continue
                finally:
                    try:
                        stop_reader.set()
                    except Exception:
                        pass
                    if proc is not None and proc.stdin is not None:
                        try:
                            shutdown_id = 1000000 + attempt
                            body = json.dumps(
                                {"jsonrpc": "2.0", "id": shutdown_id, "method": "shutdown", "params": None}
                            ).encode("utf-8")
                            proc.stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body)
                            proc.stdin.flush()
                            exit_body = json.dumps({"jsonrpc": "2.0", "method": "exit", "params": {}}).encode("utf-8")
                            proc.stdin.write(f"Content-Length: {len(exit_body)}\r\n\r\n".encode("ascii") + exit_body)
                            proc.stdin.flush()
                        except Exception:
                            pass
                    if proc is not None:
                        try:
                            proc.terminate()
                        except Exception:
                            pass
                        try:
                            proc.wait(timeout=0.5)
                        except Exception:
                            try:
                                proc.kill()
                            except Exception:
                                pass
        return None

    def _resolve_definition_fallback(
        self,
        *,
        symbol: str,
        language: str,
        source_text: str,
        current_file: str,
    ) -> tuple[str, int] | None:
        patterns: list[str] = []
        if language == "python":
            patterns = [rf"^\s*def\s+{re.escape(symbol)}\b", rf"^\s*class\s+{re.escape(symbol)}\b", rf"^\s*{re.escape(symbol)}\s*="]
        elif language in {"javascript", "typescript"}:
            patterns = [
                rf"^\s*function\s+{re.escape(symbol)}\b",
                rf"^\s*(const|let|var)\s+{re.escape(symbol)}\b",
                rf"^\s*class\s+{re.escape(symbol)}\b",
                rf"^\s*export\s+(function|class|const|let|var)\s+{re.escape(symbol)}\b",
            ]
        else:
            patterns = [rf"^\s*{re.escape(symbol)}\s*="]
        for idx, ln in enumerate(source_text.splitlines()):
            if any(re.search(p, ln) for p in patterns):
                return current_file, idx

        workspace_files = []
        try:
            workspace_files = list(self.window._workspace_files() or [])
        except Exception:
            workspace_files = []
        for path in workspace_files[:5000]:
            try:
                text = Path(path).read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for idx, ln in enumerate(text.splitlines()):
                if any(re.search(p, ln) for p in patterns):
                    return str(path), idx
        return None

    def open_diff(self) -> None:
        tab = self.window.active_tab()
        if tab is None:
            return
        other = ""
        compare_target_label = ""
        mode = "file"
        has_other_tabs = self.window.tab_widget.count() > 1
        if has_other_tabs:
            mode_choice, ok = QInputDialog.getItem(
                self.window,
                "Side-by-side Diff",
                "Compare active tab with:",
                ["File...", "Open Tab..."],
                0,
                False,
            )
            if not ok:
                return
            mode = "tab" if mode_choice.startswith("Open Tab") else "file"
        if mode == "file":
            path, _ = QFileDialog.getOpenFileName(self.window, "Compare With File", "", "All Files (*.*)")
            if not path:
                return
            try:
                other = Path(path).read_text(encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self.window, "Diff", f"Could not open file:\n{exc}")
                return
            compare_target_label = path
        else:
            candidates: list[tuple[str, Any]] = []
            for i in range(self.window.tab_widget.count()):
                candidate = self.window.tab_widget.widget(i)
                if candidate is None or candidate is tab or not hasattr(candidate, "text_edit"):
                    continue
                if hasattr(self.window, "_tab_display_name"):
                    title = self.window._tab_display_name(candidate)
                else:
                    title = f"Tab {i + 1}"
                candidates.append((f"{i + 1}: {title}", candidate))
            if not candidates:
                QMessageBox.information(self.window, "Diff", "No other open tab available for comparison.")
                return
            labels = [name for name, _candidate in candidates]
            picked, ok = QInputDialog.getItem(self.window, "Compare With Open Tab", "Tab:", labels, 0, False)
            if not ok or not picked:
                return
            selected_tab = next((candidate for name, candidate in candidates if name == picked), None)
            if selected_tab is None:
                return
            other = selected_tab.text_edit.get_text()
            compare_target_label = picked
        dlg = QDialog(self.window)
        dlg.setWindowTitle("Side-by-side Diff")
        dlg.resize(1080, 680)
        v = QVBoxLayout(dlg)
        ignore_ws = QCheckBox("Ignore whitespace differences in unified diff", dlg)
        v.addWidget(ignore_ws)
        stats_label = QLabel("", dlg)
        v.addWidget(stats_label)
        h = QHBoxLayout()
        left = QTextEdit(dlg)
        right = QTextEdit(dlg)
        left.setReadOnly(True)
        right.setReadOnly(True)
        left_text = tab.text_edit.get_text()
        left.setPlainText(left_text)
        right.setPlainText(other)
        h.addWidget(left, 1)
        h.addWidget(right, 1)
        v.addLayout(h, 1)
        btn_row = QDialogButtonBox(QDialogButtonBox.Close, Qt.Orientation.Horizontal, dlg)
        apply_left_btn = QPushButton("Apply Left to Active Tab", dlg)
        apply_right_btn = QPushButton("Apply Right to Active Tab", dlg)
        swap_btn = QPushButton("Swap Left/Right", dlg)
        unified_btn = QPushButton("Show Unified Diff", dlg)
        btn_row.addButton(apply_left_btn, QDialogButtonBox.ActionRole)
        btn_row.addButton(apply_right_btn, QDialogButtonBox.ActionRole)
        btn_row.addButton(swap_btn, QDialogButtonBox.ActionRole)
        btn_row.addButton(unified_btn, QDialogButtonBox.ActionRole)
        btn_row.rejected.connect(dlg.reject)
        v.addWidget(btn_row)

        def _apply_text_to_active(value: str) -> None:
            active = self.window.active_tab()
            if active is None:
                return
            if active.text_edit.is_read_only():
                QMessageBox.information(self.window, "Diff", "Current tab is read-only.")
                return
            active.text_edit.set_text(value)
            active.text_edit.set_modified(True)
            self.window.show_status_message("Applied diff side to active tab.", 2500)

        apply_left_btn.clicked.connect(lambda: _apply_text_to_active(left.toPlainText()))
        apply_right_btn.clicked.connect(lambda: _apply_text_to_active(right.toPlainText()))

        def _refresh_stats() -> None:
            patch = build_unified_diff_text(
                left.toPlainText(),
                right.toPlainText(),
                from_label=str(tab.current_file or "active"),
                to_label=compare_target_label or "other",
                ignore_whitespace=ignore_ws.isChecked(),
            )
            stats = diff_stats_from_patch(patch)
            stats_label.setText(
                f"Diff stats: hunks={stats.hunks}, +{stats.added}, -{stats.removed}"
            )

        def _swap_sides() -> None:
            left_text_cur = left.toPlainText()
            right_text_cur = right.toPlainText()
            left.setPlainText(right_text_cur)
            right.setPlainText(left_text_cur)
            _refresh_stats()

        swap_btn.clicked.connect(_swap_sides)
        ignore_ws.toggled.connect(lambda _checked: _refresh_stats())

        def _show_unified_diff() -> None:
            left_label = str(tab.current_file or "active")
            right_label = compare_target_label or "other"
            diff_text = build_unified_diff_text(
                left.toPlainText(),
                right.toPlainText(),
                from_label=left_label,
                to_label=right_label,
                ignore_whitespace=ignore_ws.isChecked(),
            )
            pop = QDialog(dlg)
            pop.setWindowTitle("Unified Diff")
            pop.resize(980, 620)
            pv = QVBoxLayout(pop)
            view = QTextEdit(pop)
            view.setReadOnly(True)
            view.setPlainText(diff_text or "(No differences)")
            pv.addWidget(view, 1)
            b = QDialogButtonBox(QDialogButtonBox.Close, Qt.Orientation.Horizontal, pop)
            apply_patch_btn = QPushButton("Apply Patch to Active Tab", pop)
            b.addButton(apply_patch_btn, QDialogButtonBox.ActionRole)
            b.rejected.connect(pop.reject)
            pv.addWidget(b)

            def _apply_patch_to_active() -> None:
                active = self.window.active_tab()
                if active is None:
                    return
                if active.text_edit.is_read_only():
                    QMessageBox.information(self.window, "Unified Diff", "Current tab is read-only.")
                    return
                patch = view.toPlainText().strip()
                if not patch or patch == "(No differences)":
                    QMessageBox.information(self.window, "Unified Diff", "No patch to apply.")
                    return
                try:
                    patched = apply_unified_patch_to_text(active.text_edit.get_text(), patch)
                except Exception as exc:  # noqa: BLE001
                    QMessageBox.critical(self.window, "Unified Diff", f"Patch apply failed:\n{exc}")
                    return
                active.text_edit.set_text(patched)
                active.text_edit.set_modified(True)
                self.window.show_status_message("Unified patch applied to active tab.", 3000)
                pop.accept()

            apply_patch_btn.clicked.connect(_apply_patch_to_active)
            pop.exec()

        unified_btn.clicked.connect(_show_unified_diff)
        _refresh_stats()
        dlg.exec()

    def apply_patch_file_to_active(self) -> None:
        active = self.window.active_tab()
        if active is None:
            return
        if active.text_edit.is_read_only():
            QMessageBox.information(self.window, "Apply Patch", "Current tab is read-only.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            "Apply Patch File",
            "",
            "Patch Files (*.patch *.diff *.txt);;All Files (*.*)",
        )
        if not path:
            return
        try:
            patch_text = Path(path).read_text(encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self.window, "Apply Patch", f"Could not read patch file:\n{exc}")
            return
        patch_text = patch_text.strip()
        if not patch_text:
            QMessageBox.information(self.window, "Apply Patch", "Patch file is empty.")
            return
        try:
            patched = apply_unified_patch_to_text(active.text_edit.get_text(), patch_text)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self.window, "Apply Patch", f"Patch apply failed:\n{exc}")
            return
        active.text_edit.set_text(patched)
        active.text_edit.set_modified(True)
        stats = diff_stats_from_patch(patch_text)
        self.window.show_status_message(
            f"Patch applied from file ({stats.hunks} hunks, +{stats.added}/-{stats.removed}).",
            3200,
        )

    def open_merge_helper(self) -> None:
        base, _ = QFileDialog.getOpenFileName(self.window, "Base File", "", "All Files (*.*)")
        ours, _ = QFileDialog.getOpenFileName(self.window, "Ours File", "", "All Files (*.*)")
        theirs, _ = QFileDialog.getOpenFileName(self.window, "Theirs File", "", "All Files (*.*)")
        if not base or not ours or not theirs:
            return
        b = Path(base).read_text(encoding="utf-8")
        o = Path(ours).read_text(encoding="utf-8")
        t = Path(theirs).read_text(encoding="utf-8")
        merged = o if o == t else (t if b == o else (o if b == t else f"<<<<<<< OURS\n{o}\n=======\n{t}\n>>>>>>> THEIRS\n"))
        dlg = QDialog(self.window)
        dlg.setWindowTitle("3-way Merge")
        dlg.resize(920, 620)
        v = QVBoxLayout(dlg)
        edit = QTextEdit(dlg)
        edit.setPlainText(merged)
        v.addWidget(edit, 1)
        box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close, Qt.Orientation.Horizontal, dlg)
        use_ours_btn = QPushButton("Use Ours", dlg)
        use_theirs_btn = QPushButton("Use Theirs", dlg)
        use_auto_btn = QPushButton("Use Auto", dlg)
        apply_active_btn = QPushButton("Apply to Active Tab", dlg)
        box.addButton(use_ours_btn, QDialogButtonBox.ActionRole)
        box.addButton(use_theirs_btn, QDialogButtonBox.ActionRole)
        box.addButton(use_auto_btn, QDialogButtonBox.ActionRole)
        box.addButton(apply_active_btn, QDialogButtonBox.ActionRole)
        v.addWidget(box)
        box.rejected.connect(dlg.reject)
        box.accepted.connect(lambda: self._save_text_dialog(edit.toPlainText()))
        use_ours_btn.clicked.connect(lambda: edit.setPlainText(o))
        use_theirs_btn.clicked.connect(lambda: edit.setPlainText(t))
        use_auto_btn.clicked.connect(lambda: edit.setPlainText(merged))

        def _apply_to_active() -> None:
            active = self.window.active_tab()
            if active is None:
                return
            if active.text_edit.is_read_only():
                QMessageBox.information(self.window, "3-way Merge", "Current tab is read-only.")
                return
            active.text_edit.set_text(edit.toPlainText())
            active.text_edit.set_modified(True)
            self.window.show_status_message("Merged text applied to active tab.", 2500)

        apply_active_btn.clicked.connect(_apply_to_active)
        dlg.exec()

    def _save_text_dialog(self, text: str) -> None:
        path, _ = QFileDialog.getSaveFileName(self.window, "Save File", "", "All Files (*.*)")
        if path:
            Path(path).write_text(text, encoding="utf-8")

    def open_snippets(self) -> None:
        snippets = self.window.settings.get("snippets", {})
        if not isinstance(snippets, dict):
            snippets = {}
        snippets.setdefault("python_func", "def ${1:name}(${2:args}):\n    ${3:pass}")
        snippets.setdefault("markdown_task", "- [ ] ${1:task}")
        self.window.settings["snippets"] = snippets
        self.window.save_settings_to_disk()
        names = sorted(snippets.keys())
        name, ok = QInputDialog.getItem(self.window, "Snippets", "Choose snippet:", names, 0, False)
        if not ok or not name:
            return
        text = re.sub(r"\$\{\d+:([^}]+)\}", r"\1", str(snippets[name]))
        text = re.sub(r"\$\{\d+\}", "", text)
        tab = self.window.active_tab()
        if tab is not None:
            tab.text_edit.insert_text(text)

    def ensure_template_packs(self) -> None:
        packs = self.window.settings.get("template_packs", {})
        if not isinstance(packs, dict):
            packs = {}
        packs.setdefault("notes/meeting", "## Meeting\nDate: ${1:date}\n")
        packs.setdefault("docs/changelog", "## [Unreleased]\n### Added\n- ${1:item}\n")
        packs.setdefault("code/class", "class ${1:Name}:\n    pass\n")
        self.window.settings["template_packs"] = packs
        self.window.save_settings_to_disk()
        self.window.show_status_message("Template packs are ready.", 2500)

    def show_tasks(self) -> None:
        tasks: list[str] = []
        due = re.compile(r"due[:=]\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
        for i in range(self.window.tab_widget.count()):
            tab = self.window.tab_widget.widget(i)
            if tab is None:
                continue
            name = tab.current_file or f"Tab {i + 1}"
            for ln, line in enumerate(tab.text_edit.get_text().splitlines(), start=1):
                if "TODO" in line.upper() or "FIXME" in line.upper():
                    d = due.search(line)
                    tasks.append(f"{name}:{ln} | due={d.group(1) if d else '-'} | {line.strip()}")
                    if d and hasattr(self.window, "reminders_store"):
                        try:
                            self.window.reminders_store.upsert(
                                reminder_id=f"task:{name}:{ln}",
                                title=f"Task {Path(name).name}:{ln}",
                                when_iso=f"{d.group(1)}T09:00:00",
                                note=line.strip(),
                            )
                        except Exception:
                            pass
        dlg = QDialog(self.window)
        dlg.setWindowTitle("Task Workflow")
        dlg.resize(900, 520)
        v = QVBoxLayout(dlg)
        lst = QListWidget(dlg)
        for t in tasks or ["No tasks found."]:
            lst.addItem(t)
        v.addWidget(lst)
        box = QDialogButtonBox(QDialogButtonBox.Close, Qt.Orientation.Horizontal, dlg)
        box.rejected.connect(dlg.reject)
        box.accepted.connect(dlg.accept)
        v.addWidget(box)
        dlg.exec()
        if tasks and hasattr(self.window, "reminders_store"):
            try:
                self.window.reminders_store.save()
            except Exception:
                pass

    def backup_now(self) -> None:
        configured = str(self.window.settings.get("backup_output_dir", "") or "").strip()
        dest = Path(configured) if configured else (_root() / "backups")
        dest.mkdir(parents=True, exist_ok=True)
        out = dest / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for i in range(self.window.tab_widget.count()):
                tab = self.window.tab_widget.widget(i)
                if tab is None:
                    continue
                name = Path(tab.current_file).name if tab.current_file else f"unsaved_{i + 1}.txt"
                zf.writestr(name, tab.text_edit.get_text())
        self.window.show_status_message(f"Backup created: {out}", 3500)

    def apply_backup_schedule(self) -> None:
        enabled = bool(self.window.settings.get("backup_scheduler_enabled", False))
        mins = max(1, int(self.window.settings.get("backup_interval_min", 15) or 15))
        if enabled:
            self.backup_timer.start(mins * 60 * 1000)
        else:
            self.backup_timer.stop()

    def configure_backup(self) -> None:
        dlg = QDialog(self.window)
        dlg.setWindowTitle("Backup Scheduler")
        form = QFormLayout(dlg)
        enabled = QCheckBox("Enable background scheduler", dlg)
        enabled.setChecked(bool(self.window.settings.get("backup_scheduler_enabled", False)))
        mins = QSpinBox(dlg)
        mins.setRange(1, 720)
        mins.setValue(int(self.window.settings.get("backup_interval_min", 15) or 15))
        output_dir = QLineEdit(dlg)
        output_dir.setText(str(self.window.settings.get("backup_output_dir", "") or ""))
        browse_btn = QPushButton("Browse...", dlg)
        output_row = QWidget(dlg)
        output_layout = QHBoxLayout(output_row)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.addWidget(output_dir, 1)
        output_layout.addWidget(browse_btn)

        def pick_output() -> None:
            start_dir = output_dir.text().strip() or ""
            picked = QFileDialog.getExistingDirectory(dlg, "Choose Backup Output Folder", start_dir)
            if picked:
                output_dir.setText(picked)

        browse_btn.clicked.connect(pick_output)
        form.addRow(enabled)
        form.addRow("Interval minutes:", mins)
        form.addRow("Output folder (optional):", output_row)
        box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Orientation.Horizontal, dlg)
        form.addRow(box)
        box.accepted.connect(dlg.accept)
        box.rejected.connect(dlg.reject)
        if dlg.exec() != QDialog.Accepted:
            return
        self.window.settings["backup_scheduler_enabled"] = enabled.isChecked()
        self.window.settings["backup_interval_min"] = int(mins.value())
        self.window.settings["backup_output_dir"] = output_dir.text().strip()
        self.window.save_settings_to_disk()
        self.apply_backup_schedule()

    def export_diagnostics(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self.window, "Diagnostics Bundle", str(_root() / "diagnostics_bundle.zip"), "Zip Files (*.zip)")
        if not path:
            return
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("settings.json", json.dumps(self.window.settings, indent=2))
            zf.writestr("debug_logs.txt", "\n".join(getattr(self.window, "debug_logs", [])))
            zf.writestr("meta.json", json.dumps({"timestamp": datetime.now().isoformat()}, indent=2))
        self.window.show_status_message("Diagnostics exported.", 2500)

    def toggle_keyboard_only(self, checked: bool, *, persist: bool = True) -> None:
        self.window.settings["keyboard_only_mode"] = bool(checked)
        if checked:
            self.window.main_toolbar.hide()
            if hasattr(self.window, "markdown_toolbar"):
                self.window.markdown_toolbar.hide()
            if hasattr(self.window, "search_toolbar"):
                self.window.search_toolbar.hide()
        else:
            self.window._layout_top_toolbars()
        if persist:
            self.window.save_settings_to_disk()

    def apply_accessibility_high_contrast(self) -> None:
        self.window.settings["theme"] = "High Contrast"
        self.window.settings["dark_mode"] = True
        self.window.apply_settings()

    def apply_accessibility_dyslexic(self) -> None:
        self.window.settings["font_family"] = "OpenDyslexic"
        self.window.settings["font_size"] = max(13, int(self.window.settings.get("font_size", 11)))
        self.window.apply_settings()

    def open_collaboration(self) -> None:
        port = int(self.window.settings.get("collab_port", 8765) or 8765)
        rw = bool(self.window.settings.get("collab_rw", False))
        dlg = QDialog(self.window)
        dlg.setWindowTitle("LAN Collaboration")
        form = QFormLayout(dlg)
        port_spin = QSpinBox(dlg)
        port_spin.setRange(1024, 65535)
        port_spin.setValue(port)
        rw_check = QCheckBox("Read/Write mode", dlg)
        rw_check.setChecked(rw)
        form.addRow("Port:", port_spin)
        form.addRow(rw_check)
        box = QDialogButtonBox(dlg)
        start_btn = box.addButton("Start", QDialogButtonBox.ButtonRole.AcceptRole)
        stop_btn = box.addButton("Stop", QDialogButtonBox.ButtonRole.ActionRole)
        close_btn = box.addButton(QDialogButtonBox.StandardButton.Close)
        form.addRow(box)
        close_btn.clicked.connect(dlg.reject)
        stop_btn.clicked.connect(self.collab.stop)

        def start() -> None:
            self.window.settings["collab_port"] = int(port_spin.value())
            self.window.settings["collab_rw"] = rw_check.isChecked()
            self.window.save_settings_to_disk()
            self.collab.start(int(port_spin.value()), bool(rw_check.isChecked()))
            token = str(self.window.settings.get("collab_token", ""))
            QMessageBox.information(
                self.window,
                "LAN Collaboration",
                (
                    f"Server: http://127.0.0.1:{int(port_spin.value())}\n"
                    "Use Authorization header:\n"
                    f"Bearer {token}\n\n"
                    "Endpoints: POST /join, GET /state, GET /events?since=<rev>, POST /edit"
                ),
            )

        start_btn.clicked.connect(start)
        dlg.exec()

    def open_annotations(self) -> None:
        tab = self.window.active_tab()
        if tab is None:
            return
        key = tab.current_file or "__untitled__"
        all_notes = self.window.settings.get("annotations", {})
        if not isinstance(all_notes, dict):
            all_notes = {}
        notes = all_notes.get(key, {})
        if not isinstance(notes, dict):
            notes = {}
        dlg = QDialog(self.window)
        dlg.setWindowTitle("Annotations")
        dlg.resize(760, 480)
        v = QVBoxLayout(dlg)
        lst = QListWidget(dlg)
        for ln, txt in sorted(notes.items(), key=lambda x: int(str(x[0]))):
            lst.addItem(f"Line {ln}: {txt}")
        v.addWidget(lst, 1)
        row = QHBoxLayout()
        add_btn = QPushButton("Add", dlg)
        del_btn = QPushButton("Delete", dlg)
        close_btn = QPushButton("Close", dlg)
        row.addWidget(add_btn)
        row.addWidget(del_btn)
        row.addStretch(1)
        row.addWidget(close_btn)
        v.addLayout(row)

        def persist() -> None:
            all_notes[key] = notes
            self.window.settings["annotations"] = all_notes
            self.window.save_settings_to_disk()

        def add() -> None:
            line, ok = QInputDialog.getInt(dlg, "Line", "Line number:", 1, 1, 1000000)
            if not ok:
                return
            text, ok = QInputDialog.getMultiLineText(dlg, "Annotation", "Comment:")
            if not ok or not text.strip():
                return
            notes[str(line)] = text.strip()
            lst.addItem(f"Line {line}: {text.strip()}")
            persist()

        def delete() -> None:
            item = lst.currentItem()
            if item is None:
                return
            m = re.match(r"Line\s+(\d+):", item.text())
            if m:
                notes.pop(m.group(1), None)
            lst.takeItem(lst.row(item))
            persist()

        add_btn.clicked.connect(add)
        del_btn.clicked.connect(delete)
        close_btn.clicked.connect(dlg.accept)
        dlg.exec()

