# Plugin Runtime

This document explains how PyPad plugins actually work at runtime, beyond the higher-level setup notes in `docs/plugins.md` and the method inventory in `docs/plugin_api.md`.

## Mental Model

The plugin system is host-driven, not plugin-driven.

- The app owns discovery, security checks, trust state, dependency resolution, lifecycle, and hook delivery.
- A plugin is just a folder containing `plugin.json` and `plugin.py`.
- `plugin.py` must expose a `Plugin` class.
- The host instantiates that class with a `PluginAPI` object.
- Plugins are expected to operate through `PluginAPI`, not by directly reaching into the app internals.

The main runtime lives in [advanced_features.py](/c:/Users/user/Downloads/py/RawAPPS/test/notepadclone/src/pypad/ui/features/advanced_features.py) and the static safety checks live in [extensibility_ops.py](/c:/Users/user/Downloads/py/RawAPPS/test/notepadclone/src/pypad/ui/features/extensibility_ops.py).

## Where Plugins Come From

The host resolves a plugin directory at startup.

- In normal runtime, it uses the app's plugin data directory.
- In development mode, it can optionally load directly from the repo `plugins/` folder when `plugin_dev_use_repo_plugins` is enabled.
- On startup, a few bundled example plugins are copied in if they are missing.

Each plugin folder must contain:

- `plugin.json`
- `plugin.py`

Anything missing those files is ignored during discovery.

## Discovery

Discovery is metadata-only at first. The host scans plugin folders and builds `PluginRecord` objects before any plugin code is executed.

During discovery, the host reads:

- identity fields such as `id`, `name`, `description`, `author`, `version`
- compatibility fields such as `plugin_api_version`, `min_app_version`, `max_app_version`
- capability fields such as `permissions`
- dependency fields such as `depends_on`, `provides_services`, `requires_services`
- config metadata in `settings_schema`

The output of this step is a list of records describing what could be loaded, what is enabled, and what is currently blocked.

## Security and Policy Checks

Before a plugin is loadable, the host runs static policy checks on its folder and source.

Current checks include:

- plugin directory must stay inside the plugin root
- plugin folder and critical files cannot be symlinks
- `plugin.py` and `plugin.json` must exist
- plugin id must match the allowed id pattern
- large scripts are rejected above the size limit
- risky payloads such as `.exe`, `.dll`, `.pyd`, `.so`, `.bat`, `.cmd`, and `.ps1` are blocked
- blocked imports such as `ctypes`, `subprocess`, and `importlib` are rejected
- blocked dynamic execution calls such as `eval`, `exec`, `__import__`, and `compile` are rejected
- file-related imports and `open(...)` require the `file` permission
- network-related imports require the `network` permission

These are static AST and filesystem checks. They do not sandbox Python itself. The security model here is policy gating plus trusted-hash approval, not process isolation.

## Permissions

Plugins request permissions in `plugin.json`, but requested permissions are not automatically final permissions.

The effective permission set is:

- the permissions declared in the manifest
- intersected with any user override configured in Plugin Manager

That means Plugin Manager can narrow a plugin's permissions after install.

Permissions are enforced at the `PluginAPI` boundary. If a plugin calls an API method that requires a permission it does not currently have, the call is blocked by the host.

## Trust Model

Passing policy checks is not enough. A plugin also has a digest-based trust step.

The host computes a SHA-256 digest for the plugin folder and compares it against the trusted-hash map stored in settings.

- If the digest is already trusted, loading can continue.
- If not, the user is prompted to trust and load the plugin.
- Once trusted, that exact digest is stored.
- If the plugin files change later, the digest changes and the plugin must be trusted again.

This is why edited plugins can prompt again even if they were trusted previously.

## Compatibility Checks

A plugin can be discovered but still blocked from loading.

Common reasons:

- app version is outside `min_app_version` / `max_app_version`
- `plugin_api_version` is incompatible with the host
- a declared dependency plugin is missing
- a required service is not provided by another enabled plugin
- the plugin is quarantined
- the plugin has accumulated enough failures to be auto-disabled or quarantined

The host tracks these issues in each `PluginRecord` so Plugin Manager can show why a plugin is blocked.

## Dependency and Service Resolution

There are two separate concepts:

- `depends_on`
- `provides_services` / `requires_services`

`depends_on` controls plugin load ordering and basic presence requirements. If plugin `B` depends on plugin `A`, then `A` must be enabled and loadable first.

Services are looser contracts:

- a plugin can register a named capability
- another plugin can require that capability either globally or from a specific plugin

Examples:

- `requires_services: ["word_stats"]`
- `requires_services: ["base_utils:format_utils"]`

During reload, the host builds a load order and then checks that required services are actually available from enabled plugins.

## Startup and Reload Flow

Startup loading is optionally deferred for faster app launch.

Relevant settings:

- `defer_plugin_load_on_startup`
- `plugin_startup_defer_ms`
- `plugin_startup_safe_mode`

The high-level flow is:

1. Create `PluginHost`.
2. Resolve the plugin directory.
3. Optionally copy bundled example plugins.
4. Optionally defer startup loading with a timer.
5. Call `reload(startup=True)`.
6. Discover all plugin records.
7. Skip loading entirely if startup safe mode is enabled.
8. Build the enabled/loadable set.
9. Resolve dependency order.
10. For each candidate plugin:
11. Reject blocked or quarantined plugins.
12. Require trust if the digest is new.
13. Apply any settings schema defaults.
14. Import `plugin.py`.
15. Instantiate `Plugin(api)`.
16. Call `on_load()` if present.

Reload uses the same general flow, but starts by unloading existing plugin runtime objects.

## What Unload Actually Does

When the host unloads a plugin, it does more than drop the Python instance.

It attempts to:

- call `on_unload()` if present
- stop plugin-owned timers
- remove plugin-created actions from widgets
- remove plugin-created dock panels
- remove plugin-created toolbars
- clear host-side registries for services, commands, jobs, and logs

This matters because plugins can register real UI objects. Reload has to clean up those side effects explicitly.

## PluginAPI Injection

Plugins do not receive the main window directly. They receive a `PluginAPI` wrapper.

That wrapper is responsible for:

- permission checks
- state persistence
- config access
- action registration
- panel and toolbar creation
- background work orchestration
- service and command registration
- logging and runtime events

This is the key boundary in the system. Most extension behavior should flow through `PluginAPI`.

The optional `app_window()` and `active_tab()` bridge is intentionally treated as unsafe and is disabled unless the corresponding setting allows it.

## Persistent State

Plugins have two separate persistent stores exposed by the host:

- plugin state
- plugin config

Plugin state:

- intended for plugin-owned runtime data
- accessed with `plugin_state_get()` and `plugin_state_set()`
- stored per plugin id in app settings

Plugin config:

- intended for user-editable configuration values
- shaped by `settings_schema`
- accessed with `plugin_config_get()` and `plugin_config_set()`
- coerced by the host to schema types such as `bool`, `int`, `float`, `list`, or enum-like strings

This split keeps operational state separate from user settings.

## Commands, Services, Jobs, and Logs

The host keeps several registries for plugin-created runtime features.

Commands:

- plugins can register named commands
- commands are also surfaced into action-based workflows such as command discovery

Services:

- plugins can register service objects for other plugins
- required services are checked during reload

Jobs and timers:

- background permission allows timers, jobs, and thread-based work
- the host tracks them so they can be queried and cleaned up

Logs:

- plugin log entries are stored per plugin
- Plugin Manager can export them
- runtime event history is also recorded by the host

## Event and Hook Delivery

The editor window emits plugin events through `_emit_plugin_event(...)` in [ui_setup.py](/c:/Users/user/Downloads/py/RawAPPS/test/notepadclone/src/pypad/ui/main_window/ui_setup.py).

That method builds a payload and forwards it to `PluginHost.emit_event(...)`.

Important details:

- only plugins with the `hooks` permission receive hook events
- if a plugin does not have `ui`, the raw `tab` object is stripped from the payload
- the host first calls `on_event(name, payload)` if present
- then it calls the specific handler such as `on_change(payload)` or `on_before_save(payload)` if present
- hook counts, last-run timestamps, and failures are tracked per plugin

Examples of app-originated hook sources include:

- text changes
- selection changes
- open and close events
- tab changes
- save lifecycle events
- focus and blur events

This is how plugins react to app behavior without polling.

### Event Flow Diagram

The exact path for a normal plugin hook looks like this:

```text
User action or window event
    |
    v
UISetupMixin method
for example: _handle_text_changed(), _handle_selection_changed(), file save logic
    |
    v
_emit_plugin_event(event_name, tab=..., **extra)
    |
    | builds payload
    | adds fields like:
    | - tab
    | - path
    | - title
    | - modified
    v
advanced_features.plugin_host
    |
    v
PluginHost.emit_event(event_name, **payload)
    |
    | loops through loaded PluginRecord entries
    | skips plugins without "hooks" permission
    | removes raw tab object if plugin lacks "ui"
    | updates hook counters and timestamps
    v
Plugin instance
    |
    | first, if present:
    |   on_event(event_name, payload)
    |
    | then, if present:
    |   on_<event_name>(payload)
    v
Plugin-specific behavior runs
```

For example, a text edit follows this shape:

```text
UISetupMixin._handle_text_changed()
    -> UISetupMixin._emit_plugin_event("change", tab=tab)
    -> PluginHost.emit_event("change", tab=tab, path=..., title=..., modified=...)
    -> Plugin.on_event("change", payload)
    -> Plugin.on_change(payload)
```

That means a plugin can implement either:

- one generic dispatcher in `on_event(...)`
- one or more specific handlers like `on_change(...)`, `on_selection_changed(...)`, or `on_before_save(...)`
- or both

## Failure Handling and Quarantine

Plugin failures are counted and persisted.

If a plugin raises during load or during a hook:

- the failure count is incremented
- the last error and timestamp are recorded
- a runtime event is logged

After enough failures, the host can auto-disable or quarantine the plugin based on the configured threshold.

Quarantine is a stronger state than simple disable. Quarantined plugins are skipped until the user explicitly resets or fixes them.

## Online Plugins

The online plugin flow is deliberately simple.

Catalog loading:

- the host prefers the local `online_plugins/catalog.json` if present
- otherwise it fetches the configured catalog URL
- each catalog row is normalized into a simple display/install record

Installation:

1. Create a staging directory.
2. Download `plugin.json` and `plugin.py` from the declared GitHub-backed source path.
3. Validate the manifest.
4. Confirm the manifest id matches the catalog id.
5. Re-run the same security assessment used for local plugins.
6. Copy the staged plugin into the installed plugins directory.

Online install does not bypass the normal trust and load flow. It only automates getting the files into place.

## Minimal Lifecycle Example

At runtime, a typical plugin lifecycle looks like this:

1. User enables plugin in Plugin Manager.
2. Host discovers the plugin from disk.
3. Host validates policy, compatibility, and trust.
4. Host imports `plugin.py`.
5. Host creates `Plugin(PluginAPI(...))`.
6. Host calls `on_load()`.
7. Plugin registers actions, panels, commands, timers, or services.
8. App emits hook events as the user edits files.
9. Plugin reacts through `on_event(...)` or named hook handlers.
10. Host unloads the plugin during reload, uninstall, or shutdown.

## Recommended Extension Pattern

If you want to extend the system cleanly:

- treat `plugin.json` as the plugin's contract
- request only the permissions you actually need
- prefer `PluginAPI` over direct window access
- use `settings_schema` for user configuration
- use plugin state for counters, caches, and plugin-owned history
- use hooks for app reactions instead of polling whenever possible
- register commands and services when you want composition with other plugins

## Related Docs

- `docs/plugins.md`: setup, manifest shape, manager features, examples
- `docs/plugin_api.md`: method-by-method API and hook reference
