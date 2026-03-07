# Plugin API

This document describes the plugin runtime API, permission gates, and hook events.

## Design Direction

- Prefer `PluginAPI` controller methods.
- Avoid direct internal object access.
- Treat `app_window()` / `active_tab()` as an unsafe bridge for trusted internal plugins only.
- Use Plugin Manager `Scaffold Plugin` for quick, policy-aligned plugin bootstrapping.

## Permissions

Plugins declare permissions in `plugin.json`. Users can allow/deny requested permissions in Plugin Manager.

- `file`
- `network`
- `ai`
- `ui`
- `menu`
- `toolbar`
- `panel`
- `background`
- `hooks`

## Manifest Metadata

Optional compatibility/update fields in `plugin.json`:

- `version`: plugin version string.
- `plugin_api_version`: plugin API contract version expected by plugin.
- `min_app_version`: minimum app version required.
- `max_app_version`: maximum app version supported.
- `update_url`: plugin update metadata endpoint.
- `homepage`: plugin homepage/project URL.
- `depends_on`: plugin ids that must be enabled/loadable first.
- `provides_services`: service names this plugin offers.
- `requires_services`: required service refs (`service` or `plugin_id:service`).
- `settings_schema`: plugin config schema (typed defaults/validation metadata).

Plugins with incompatible app-version ranges are discovered but blocked from enabling/loading.
Plugins with incompatible `plugin_api_version` are also blocked.
Plugins with missing/cyclic dependencies or unresolved required services are blocked.
Repeated plugin failures are tracked and may trigger automatic disable/quarantine depending on host threshold settings.

## Hook Events

Hook handlers are only delivered if the plugin has `hooks`.

Supported hooks:

- `on_change`
- `on_selection_changed`
- `on_open`
- `on_close`
- `on_tab_changed`
- `on_before_save`
- `on_before_save_text`
- `on_before_save_export`
- `on_after_save`
- `on_after_save_text`
- `on_after_save_export`
- `on_save`
- `on_window_focus`
- `on_window_blur`

Each hook receives one `event` dict.

```python
def on_before_save(self, event) -> None:
    path = event.get("path", "")
    title = event.get("title", "")
    mode = event.get("save_mode", "text")
```

Optional generic handler:

```python
def on_event(self, name, event) -> None:
    pass
```

## PluginAPI Surface

General:

- `notify(text)`
- `show_status(text, timeout_ms=3000)`
- `app_info()`
- `plugin_state_get(key, default=None)`
- `plugin_state_set(key, value)`
- `plugin_config_schema()`
- `plugin_config_get(key, default=None)`
- `plugin_config_set(key, value)`
- `log_metric(event, detail="")`
- `emit_runtime_event(event, payload=None)`
- `register_service(service_name, obj)`
- `get_service(service_ref)`
- `register_command(command_name, callback, description="", args_schema=None)`
- `run_command(command_ref, args=None)`
- `log(level, message)`

Registered plugin commands are also surfaced as `Plugins/Commands/...` actions, so they are discoverable via action-based workflows (including Command Palette).
Plugin logs from `log(level, message)` are retained per plugin and exposed in Plugin Manager diagnostics/export.

Editor and tabs:

- `tab_count()`
- `active_tab_index()`
- `active_tab_info()`
- `switch_to_tab(index)`
- `current_text()`
- `selection_text()`
- `selection_range()`
- `open_tabs()`

File/workspace (`file`):

- `file_new(text="")`
- `close_tab(index=None)`
- `open_file(path)`
- `save_active()`
- `replace_text(text)`
- `insert_text(text)`
- `replace_selection(text)`
- `workspace_root()`
- `workspace_files()`
- `workspace_index_status()`
- `refresh_workspace_index()`

Actions/menus/UI:

- `list_actions()` (`ui` or `menu`)
- `trigger_action(action_id)` (`ui` or `menu`)
- `add_menu_action(menu_path, label, callback, shortcut=None)` (`menu` or `ui`)
- `add_toolbar_action(toolbar_name, label, callback, shortcut=None)` (`toolbar` or `ui`)
- `add_panel(title, widget, area=Qt.RightDockWidgetArea)` (`panel` or `ui`)

AI and network:

- `ask_ai(prompt)` (`ai`)
- `network_allowed()` (`network`)

Background:

- `run_background(fn, name=None)` (`background`)
- `start_timer(interval_ms, fn)` (`background`)
- `start_job(job_name, fn)` (`background`)
- `cancel_job(job_id)` (`background`)
- `job_status(job_id)` (`background`)

## Manager Capabilities

Plugin Manager can:

- inspect plugin zip archives before install
- install/export plugin zip bundles
- export per-plugin diagnostics JSON
- export per-plugin logs
- reset failure counters and retry plugin startup
- check update metadata for one plugin or all plugins

Unsafe bridge (`ui`, default disabled):

- `app_window()`
- `active_tab()`

These two methods are blocked unless `plugin_allow_unsafe_ui_bridge=true` in settings.
You can toggle this from `Settings -> Plugin Manager...`.

## Minimal Example

```python
class Plugin:
    def __init__(self, api) -> None:
        self.api = api

    def on_load(self) -> None:
        self.api.add_menu_action("Plugins/Demo", "Notify", self.say_hi)

    def say_hi(self) -> None:
        self.api.notify("Hello from plugin!")
```

## Example Map

| Example Plugin | Demonstrates |
| --- | --- |
| `example_word_tools` | `file` + `ai` flows, `add_menu_action`, `add_toolbar_action`, `add_panel`, timers, basic text transforms |
| `example_hello_network` | `network_allowed`, `show_status`, persistent counters via `plugin_state_get/set`, action discovery with `list_actions` |
| `example_workspace_inspector` | Workspace index APIs (`refresh_workspace_index`, `workspace_index_status`), panel UI, plugin state persistence |
| `example_action_runner` | Action introspection and dispatch via `list_actions` + `trigger_action` |
| `example_session_notes` | Document creation and writing (`file_new`, `replace_text`), plugin-scoped state tracking |
| `example_hook_logger` | Generic hook capture with `on_event`, per-hook counters stored in plugin state |
| `example_tab_cycle` | Tab navigation APIs (`tab_count`, `active_tab_index`, `switch_to_tab`, `active_tab_info`) and background timer heartbeat |
| `example_selection_tools` | Selection helpers with `selection_text`, `replace_selection`, `insert_text`, plus persistent operation counters |
| `example_workspace_report` | Workspace reporting using `workspace_root`, `workspace_files`, `workspace_index_status`, and `file_new` |
| `example_action_macro` | Macro-like action chaining using `list_actions` and `trigger_action` |
| `example_auto_tagger` | Content tagging heuristics with persisted tag counters via `plugin_state_get/set` |
| `example_save_guard` | Save-time guard rails using `on_before_save` hook and persisted last-check diagnostics |
| `example_quick_insert` | Snippet insertion patterns with `insert_text` and menu commands |
| `example_workspace_todo_index` | Background workspace scan and report generation using `run_background`, `workspace_files`, and `file_new` |
| `example_tab_health` | Health telemetry with tab hooks (`on_tab_changed`), timers, and `active_tab_info` |
| `example_action_bookmarks` | Persisting favorite action IDs and replaying them with `trigger_action` |
| `example_ai_commit_message` | AI prompt workflow for commit-message drafting from selection/current text |
| `example_session_metrics_panel` | Dockable live metrics panel powered by hooks and periodic refresh timers |
| `example_file_rotator` | Controlled save orchestration across tabs using `tab_count`, `switch_to_tab`, `active_tab_info`, and `save_active` |
| `example_selection_case_cycle` | Stateful text transform cycling with `selection_text`, `replace_selection`, and plugin state |
| `example_workspace_file_sampler` | Workspace sampling/report generation from `workspace_files` into `file_new` output |
| `example_save_snapshot_trail` | Persistent save event journaling with `on_after_save` hook and report rendering |
| `example_action_searcher` | Action discovery/filtering and invocation patterns with `list_actions` + `trigger_action` |
