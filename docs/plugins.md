# Plugin System

Pypad plugins are now controller-first: plugins should use `PluginAPI` methods instead of touching internal app objects directly.
Dependencies are resolved before load; missing/cyclic dependencies block plugin load.
Service contracts are explicit with `provides_services` and `requires_services`.

## Plugin Location

Plugins are discovered from:

- `plugins/<plugin_folder>/plugin.json`
- `plugins/<plugin_folder>/plugin.py`

## Manifest Format

`plugin.json`:

```json
{
  "id": "my_plugin",
  "name": "My Plugin",
  "version": "1.0.0",
  "plugin_api_version": "1.0",
  "description": "What this plugin does",
  "min_app_version": "1.0.0",
  "max_app_version": "",
  "update_url": "https://example.com/my-plugin/update.json",
  "homepage": "https://example.com/my-plugin",
  "depends_on": ["base_utils"],
  "provides_services": ["word_stats"],
  "requires_services": ["base_utils:format_utils"],
  "settings_schema": {
    "enabled": { "type": "bool", "default": true }
  },
  "permissions": ["file", "menu", "hooks"]
}
```

## Permissions

- `file`: document and workspace file operations through `PluginAPI`.
- `network`: network capability checks through `PluginAPI`.
- `ai`: AI actions through `PluginAPI`.
- `ui`: UI-level controller actions.
- `menu`: add/trigger menu actions through controller API.
- `toolbar`: add toolbar actions through controller API.
- `panel`: add dock panels through controller API.
- `background`: background threads and timers.
- `hooks`: receive lifecycle hook events.

## Sandboxing Model

- Security checks run before loading (manifest/script presence, hash trust, blocked imports/calls, payload checks).
- Permissions are enforced at the API method boundary.
- Unsafe raw UI object bridge (`api.app_window()` / `api.active_tab()`) is disabled by default.
- To enable raw UI bridge for trusted internal plugins only, set `plugin_allow_unsafe_ui_bridge` to `true` in settings.
- Plugin failure containment tracks repeated load/hook failures and can auto-disable/quarantine unstable plugins after threshold.

## Plugin Entry Point

`plugin.py` should expose `Plugin`:

```python
class Plugin:
    def __init__(self, api):
        self.api = api

    def on_load(self):
        self.api.notify("Loaded")
```

## UI

Open plugin manager from:

- `Settings -> Plugin Manager...`

Use it to enable/disable plugins, adjust permission overrides, toggle unsafe UI bridge, and reload.
In development mode only, it also supports loading plugins directly from the repository `../plugins` folder.
It also supports:
- Live filtering by id/name/description/permissions.
- `Scaffold Plugin` to generate a ready-to-edit `plugin.json` + `plugin.py` template.
- `Install Plugin Zip` to import plugin bundles with policy checks.
- `Inspect Plugin Zip` for dry-run metadata/policy preview before install.
- `Export Plugin` one-click zip packaging for selected plugin.
- `Export Diagnostics` to save selected plugin runtime snapshot as JSON.
- `Export Logs` for per-plugin structured logs.
- `Reset Failures` to clear plugin failure counters after fixes.
- `Retry Plugin` to clear failure state/quarantine and attempt reload.
- `Check Update` to compare installed plugin version with `update_url` metadata.
- `Check All Updates` to batch-check all installed plugins.
- `Plugin Settings` to edit schema-driven plugin configuration values.
- `Run Command` to execute a selected plugin's registered command with optional JSON args.
- Runtime diagnostics panel per plugin (errors, hook counters, last run/event, metadata).
- Online Plugins catalog (GitHub-backed) with one-click install from `online_plugins/catalog.json`.

## Update Metadata Endpoint

If `update_url` is set, Plugin Manager update checks expect a JSON object containing at least:

```json
{
  "version": "1.2.3"
}
```

## Example Plugins

- `plugins/example_word_tools/`
- `plugins/example_hello_network/`
- `plugins/example_workspace_inspector/`
- `plugins/example_action_runner/`
- `plugins/example_session_notes/`
- `plugins/example_hook_logger/`
- `plugins/example_tab_cycle/`
- `plugins/example_selection_tools/`
- `plugins/example_workspace_report/`
- `plugins/example_action_macro/`
- `plugins/example_auto_tagger/`
- `plugins/example_save_guard/`
- `plugins/example_quick_insert/`
- `plugins/example_workspace_todo_index/`
- `plugins/example_tab_health/`
- `plugins/example_action_bookmarks/`
- `plugins/example_ai_commit_message/`
- `plugins/example_session_metrics_panel/`
- `plugins/example_file_rotator/`
- `plugins/example_selection_case_cycle/`
- `plugins/example_workspace_file_sampler/`
- `plugins/example_save_snapshot_trail/`
- `plugins/example_action_searcher/`

For full method and hook references, see `docs/plugin_api.md`.

## Online Plugins

- Catalog URL setting: `plugin_online_catalog_url` (defaults to the PyPad GitHub `online_plugins/catalog.json`).
- Catalog entries can point to plugin source folders in GitHub (raw `plugin.json` + `plugin.py`).
- Example online plugin in this repo: `online_plugins/plugin_online_example/`.
