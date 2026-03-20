# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project uses Semantic Versioning.

## [2.0.0] - 2026-03-20

### Please Note!
- This release is a major UX, accessibility, and workflow milestone focused on making PyPad feel more serious, more trustworthy, and more maintainable as a desktop editor.

### Added
- Full timeline overhaul with modular foundations for file, folder, and workspace history:
  - `src/pypad/ui/system/timeline_models.py`
  - `src/pypad/ui/system/timeline_controller.py`
  - `src/pypad/ui/system/timeline_dialog.py`
  - `src/pypad/ui/system/workspace_timeline_models.py`
  - `src/pypad/ui/system/workspace_timeline_controller.py`
  - `src/pypad/ui/system/workspace_timeline_dialog.py`
  - `src/pypad/ui/system/workspace_timeline_panel.py`
- New VS Code-inspired unified file timeline that can merge:
  - current unsaved editor text
  - saved-on-disk content
  - local history snapshots
  - autosave drafts
  - crash recovery snapshots
  - recent Git file history
- New file timeline review features:
  - source filtering
  - grouped timeline sections
  - snapshot preview
  - diff preview
  - mark-for-compare baseline flow
  - restore to current tab
  - restore to new tab
  - copy snapshot text
  - auto-refresh when the active tab changes
  - live refresh while the current tab text changes
  - autosave-aware refresh so new draft snapshots appear without reopening the panel
- New docked File Timeline panel so current-file history now lives in the same panel system as scope timelines.
- New docked Timeline panel for folder and workspace scopes with Explorer and workspace integration.
- New scope timeline entries for:
  - recent filesystem activity
  - autosave drafts inside the selected scope
  - crash recovery snapshots inside the selected scope
  - Git commit activity for the selected folder or workspace
- New scope timeline actions:
  - open selected file
  - open selected file timeline
  - copy summary
- New `Workspace > Scope Timeline...` entry and `Timeline Panel` view toggle.
- New accessibility-first compare and merge workflow with dedicated modular implementation:
  - `src/pypad/ui/document/compare_dialog.py`
  - `src/pypad/ui/document/compare_engine.py`
  - `src/pypad/ui/document/compare_models.py`
- New compare flows for:
  - current tab vs saved file
  - current tab vs clipboard
  - current tab vs another open tab
  - merge result preview with apply/open-in-new-tab paths
- New structured data tools surface with dedicated dialog and format-aware helpers:
  - JSON formatting and validation preview
  - XML formatting and validation preview
  - CSV table preview
  - YAML structure preview
- New reusable accessible banner component:
  - `src/pypad/ui/components/banner_widget.py`
- New inline Large File Mode banner with explicit actions for:
  - loading the full file
  - opening compare
  - opening structured data tools
- New named session management workflow with dedicated storage and manager dialog:
  - save named sessions
  - browse/open/delete named sessions
  - session summaries and timestamps
- New macro library manager dialog for saved macros with:
  - run
  - rename
  - shortcut update
  - delete
- Local History timeline improvements:
  - filter box
  - restore to new tab
  - clearer snapshot review flow
- New split-view presentation controller:
  - `src/pypad/ui/editor/split_view_controller.py`
  - clearer active-pane indication
  - accessible split-pane metadata
  - status-bar split-state feedback
- New explicit portable-mode detection and storage routing:
  - `src/pypad/app_settings/portable_mode.py`
  - portable marker support for local app-data storage beside the runtime
- New workspace insights feature:
  - `Workspace Insights...`
  - lightweight TODO/FIXME/NOTE collection across workspace or open files
  - accessible list-detail review dialog
- New plugin manager presentation helper:
  - `src/pypad/ui/features/plugin_manager_presenters.py`
  - plain-language plugin health summary in the manager UI
- New status-bar indicators for:
  - portable mode
  - split-view state
- Explorer right-click menu expanded into a more serious file/folder workflow surface with:
  - `Open Timeline`
  - `Restore Previous Version...`
  - `Compare With`
  - `Open Read-Only`
  - `Open in Other View`
  - `Pin File` / `Favorite File`
  - `Reveal Related`
  - scoped workspace search/replace
  - scope-filtered workspace insights / TODO review
  - structured-data entry points
  - richer copy-path options
  - terminal and Git review actions

### Changed
- Timeline review now behaves more like a serious editor feature instead of a simple local-history popup or Explorer text dump.
- File timeline review is now dock-first and live-updating instead of opening only as a one-shot modal workflow.
- Folder and workspace timeline browsing now lives in a dock-capable panel so timeline activity can stay visible alongside Explorer, Git, and other review surfaces.
- Git-backed scope timeline entries now include richer commit preview content with stats and bounded patch excerpts, not just commit titles.
- The application architecture now uses more feature-local modules for major editor workflows instead of pushing additional logic into main-window catch-all files.
- Core roadmap work was implemented with unique module docstrings and clearer responsibility boundaries so the source is easier to read and learn from.
- Large-file behavior now presents itself as an intentional editor mode instead of relying only on transient warnings or implicit degraded behavior.
- Compare/review workflows now feel more like a dedicated editor surface instead of a one-off preview utility.
- Structured-data handling is now presented as a proper editor-side tool workflow instead of staying buried in plain text-only handling.
- Session and macro management are now more discoverable through dedicated manager-style dialogs.
- Local history restore flow is safer because historical text can now be restored into a new tab without overwriting the current document immediately.
- Split editing now communicates active-pane state more clearly, improving keyboard-first multi-view use.
- Portable storage support now routes settings, themes, autosave, reminders, translation cache, logs, and plugin storage through one shared path policy.
- Workspace navigation now includes a project-summary style surface for lightweight code/document signals instead of requiring ad hoc manual scanning.
- Explorer context menus now behave more like a serious editor/workspace tool instead of only exposing basic file operations.
- Plugin management now summarizes runtime health in a more trustworthy and readable way before the user has to inspect raw diagnostics.
- Theme token styling now also covers split-pane focus emphasis so multi-view editing remains visible in dark, light, and accessibility-oriented themes.
- Main-window status reporting is more descriptive for serious editor use, especially around split state and portable-mode context.

### Fixed
- Split-view UX now avoids the unclear “which pane is active?” state by applying explicit focus and status feedback.
- Portable-mode runs no longer require ad hoc path changes because app-managed storage can now resolve locally through a dedicated detection layer.
- Plugin manager readability is improved by surfacing concise health status instead of forcing users to infer overall plugin state from raw diagnostics alone.
- Workspace TODO/FIXME review no longer depends on the older task-only flow when the user primarily needs a project insight surface.
- Explorer file/folder review no longer requires bouncing between multiple menus for timeline, compare, workspace, copy-path, and Git actions.
- Large-file workflows are clearer and safer because reduced-feature behavior is now communicated inline near the editor.
- Source organization regressions were reduced by moving new feature logic into dedicated modules rather than expanding already-large orchestration files further.

## [1.8.4] - 2026-03-19

### Please Note!
- Because the team has any other responsibilities, please expect the app to be take longer to update as we're gonna test and find for more bugs, similar from any other production apps.

### Added
- Currency Converter now supports manual live-rate refresh via `forex-python` while keeping offline cached/default conversion available.
- The Windows installer/uninstaller now prompts whether PyPad-managed user settings and local app data should be removed during uninstall.

### Changed
- App/version metadata has been aligned to the `1.8.4` release line across release files, summaries, and update feed metadata.
- `Cached Currency Tools...` has been renamed to `Currency Converter...` across the built-in tools surface, docs, and app knowledge.
- Currency status messaging now distinguishes bundled defaults, cached rates, and live rates, while preserving existing settings compatibility.
- PyInstaller packaging now explicitly bundles `zxing-cpp` runtime pieces plus the packaged `online_plugins` catalog so QR tooling and packaged plugin metadata remain available in frozen builds.
- Settings now route logging-level and related debug controls into Developer Hub more directly, including a shortcut from `Settings > Preferences > Advanced > Diagnostics`.
- Default dark mode now separates major surfaces more clearly with a darker sidebar chrome, a slightly lighter editor, and a distinct Markdown preview shade.

### Fixed
- Offline Writing Studio now bounds local LanguageTool warmup and falls back to rule-based analysis instead of hanging the app when the local grammar backend is slow or unavailable.
- QR generation now emits standards-compliant QR images when `zxing-cpp` is available, improving phone-scanner compatibility while preserving the local fallback path.
- Settings search highlighting now uses theme-safe property styling instead of per-widget stylesheet overrides that could produce ghost black text artifacts.
- Hidden developer mode in the About dialog now requires 10 clicks instead of 3.
- Frozen builds now continue to install and execute `plugin.py` files from the writable plugins directory, including plugins installed through Online Plugins mode.
- Offline Graph Viewer now shows concrete plotting errors such as `SyntaxError: invalid syntax` in its output area instead of failing silently.
- The `Window` menu now refreshes from live tab titles so open documents no longer appear incorrectly as `Untitled`.
- Opening a file from `Recent Files` no longer replaces an actively open blank `Untitled` tab.

## [1.8.3] - 2026-03-19

### Please Note!
- Because the team has any other responsibilities, please expect the app to be take longer to update as we're gonna test and find for more bugs, similar from any other production apps.

### Added
- New built-in offline tools framework under `src/pypad/ui/tools` with a shared registration layer, common tool dialog chrome, local help affordance, and shared `Insert`, `Copy`, and `Save` actions.
- New `Tools > Built-in Tools` submenu entries for:
  - `Random Number Generator...`
  - `Password Generator...`
  - `Percentage / Finance Calculator...`
  - `Scientific Calculator...`
  - `Unit Converter...`
  - `Equation Solver...`
  - `Offline Graph Viewer...`
  - `Cached Currency Tools...`
  - `Timer / Stopwatch...`
  - `Color Picker...`
  - `World Clock...`
  - `Reminders...`
  - `Taskers...`
  - `Clean Reader Mode...`
  - `Highlights + Notes...`
  - `QR Generator / Scanner...`
- New general-purpose QR decoding support via bundled `zxing-cpp`, with PyPad-generated matrix-code fallback when the decoder is unavailable.
- New right-click editor `Selection > Tools` submenu for quick access to the newer built-in utilities directly from selected text.
- New persisted settings families for tool state and release-planned utility surfaces, including `tool_state`, `tool_help_dismissed`, `world_clock_zones`, `task_lists`, `currency_rates_cache`, `currency_rates_last_sync`, and `reader_mode_defaults`.
- New tool-focused regression coverage in `tests/test_tools.py` for generator/calculator helpers, dialog accessibility, and tool-action registration.

### Changed
- App/version metadata has been aligned to the `1.8.3` release line across release files, summaries, and update feed metadata.
- README project summary, feature overview, and developer-facing app knowledge were refreshed to reflect the new built-in tools surface and the current local-first direction.
- The command palette can now discover the new built-in tool actions automatically because they are registered as normal main-window actions.
- Built-in tool launchers now auto-seed relevant dialogs from the current editor selection, including math, QR, annotation, task, finance, unit, and currency workflows.
- QR scanning help and app knowledge now describe the bundled general-purpose decoder path instead of only the PyPad-local fallback behavior.

### Fixed
- Settings coercion now includes a concrete `coerce_str(...)` helper instead of relying on an undefined symbol in migration paths.
- World Clock now falls back to fixed-offset time zone definitions for common regions when the Python `tzdata` package is unavailable, keeping the tool usable in lean Windows environments and packaged builds.
- `zxing-cpp` QR decoding integration now uses the correct shaped grayscale image buffer bridge for `QImage`, so bundled QR scanning works with the actual decoder contract.

## [1.8.2] - 2026-03-15

### Please Note!
- Because the team has any other responsibilities, please expect the app to be take longer to update as we're gonna test and find for more bugs, similar from any other production apps.

### Added
- Security profiles now support profile-scoped saved security state, so `beginner`, `balanced`, `power_user`, and `custom` can each retain their own trust store, save/privacy preferences, and custom security overrides.
- External notes now surface a persistent untrusted-note banner with explicit `Trust and Edit`, `Trust for This Session`, and `Keep Read-Only` actions.
- Security settings now expose fuller custom-profile override controls for plugin, AI, update, save, and trust-persistence behavior.
- New `Tools > Offline Writing Studio...` workflow for local grammar/style review, heuristic AI-likeness scoring, paraphrasing, and humanizing on either the current selection or the full document.
- New offline writing-tool settings under `Settings > Preferences > AI & Updates > Language Tools` for grammar backend usage, repeated-word/style detectors, paraphraser/humanizer behavior, and AI-detector sensitivity thresholds.
- New accessibility coverage across major custom UI surfaces, including accessible names/descriptions for the trust banner, AI chat dock, workspace dialogs, plugin dialogs, tutorial flow, and core dock panels.
- New accessibility presets for `Large Text` and `Low Stimulation`, alongside the existing high-contrast and dyslexic-font presets.
- New accessibility smoke coverage for keyboard-first navigation and major dialog metadata.
- A hidden splash-screen startup gesture now opens a dedicated `Startup Recovery / Safe Mode` dashboard with restart, recovery, log, and diagnostics controls.

### Changed
- Trust, safe-save, AI privacy, and update-signature enforcement now resolve through the active security profile instead of relying on one shared global set of security toggles.
- Beginner and balanced profiles now default AI redaction to emails, paths, and tokens enabled, and default AI key usage to `env_only`.
- Encrypted notes now use a versioned PyPad armored format with AES-256-GCM for new saves while remaining backward-compatible with older encrypted note payloads.
- Enabling note encryption now rewrites the selected file as armored encrypted text, and disabling note encryption rewrites decrypted plaintext back into that same file.
- Encrypted saves no longer create `.bak` files, and other editors only see the armored encrypted payload rather than readable note contents.
- Built-in-only plugin mode now isolates discovery and trust checks to the packaged plugin root.
- Soft Light, High Contrast, Solarized Light, and Ocean Blue now provide dedicated token sets in both light and dark mode instead of collapsing to one generic dark palette.
- Print View, AI chat inline code/link cards, terminal/tasks output, and settings-search highlights now derive colors from active theme tokens so palette changes carry through consistently.
- Custom dialogs, docks, and interactive widgets now use stronger global focus-ring styling for clearer keyboard focus visibility.
- Reduced-motion preferences now suppress remaining custom UI animations such as tutorial fades and AI typing animation states.
- Keyboard navigation is more consistent across trust actions, AI chat controls, workspace dialogs, plugin dialogs, terminal/tasks, and Git dock controls.
- Developer diagnostics entry points for debug logs and runtime info now live under the Developer Hub instead of as separate Help-menu dialogs.
- App/version metadata has been aligned to the `1.8.2` release line across release files, summaries, and update feed metadata.
- Startup recovery now presents as a dedicated dashboard layout, keeps the main editor hidden while recovery mode is active, and provides one-click restart paths for safe-mode and normal relaunch.
- Local spellcheck now uses `chunspell` as the multilingual backend, keeps `symspellpy` as an English-only accelerator, and resolves bundled Hunspell dictionaries directly from `assets/dictionaries` in both development runs and PyInstaller builds.
- Local writing tools now optionally use `language-tool-python` as an on-device grammar backend when installed, while still falling back to built-in offline rule-based checks.

### Fixed
- Plugin event emission and plugin write APIs no longer bypass untrusted-note protections when plugin blocking is enabled.
- Plugin automation now enforces profile-level restrictions for `macros_only`, `restricted`, and `advanced` modes.
- Settings profile switching no longer overwrites another profile's saved security/trust/privacy state in memory before apply.
- Enabling note encryption from `File > More > Security` now persists the encrypted form of the current file instead of only toggling in-memory state.
- Theme preset switches no longer leave those named palettes partially unsupported when dark mode is enabled.
- AI chat assistant bubbles no longer pin code blocks and action links to a hard-coded dark appearance in light themes.
- AI prompt redaction no longer mistakes internal `pypad://...` deep links for filesystem paths during redacted-send preview.
- Entering a Gemini API key in `Settings > Preferences > AI & Updates` now automatically switches AI key storage to settings-backed mode so first-time saves work immediately.
- Hidden developer mode now exposes a deeper diagnostics hub, AI payload inspection, and developer-only debugging tools after triple-clicking the About dialog version text.
- Terminal & Tasks dock no longer forces a dark-only output surface regardless of the selected palette.
- Keyboard and screen-reader users now get clearer metadata on major custom widgets instead of relying on unnamed controls.
- `Tools > More > Run Backup Now` now prompts for a destination zip path instead of always writing to the configured backup folder.
- Closing the startup recovery dashboard during an armed splash-triggered recovery launch now exits the current app session instead of revealing the hidden main window underneath.
- Spellcheck language normalization now targets the actual bundled dictionary folder names directly, avoiding region-tag mismatches such as `es_ES` vs `es` when loading packaged dictionaries.
- Spellcheck suggestions now preserve the input word's capitalization pattern, so corrections such as `WAHT` -> `WHAT`, `tset` -> `test`, and `Tset` -> `Test` stay case-appropriate.

## [1.8.1] - 2026-03-14

### Added
- New dedicated Play action SVG assets for quiz and typing-speed flows.
- Online Plugins catalog entries can now expose changelog notes in the browser/install UI.
- Online Plugins catalog entries can now show verification/trust signals and 1-5 star ratings in the browser/install UI.
- New `Plugin Example Pack` online plugin that demonstrates top-level menus, Help-menu injection, topbar actions, dock panels, timers, hooks, and file creation.
- New plugin runtime architecture guide in `docs/plugin_runtime.md`, including the event flow from `ui_setup._emit_plugin_event()` into `PluginHost.emit_event()` and plugin hook handlers.
- More verbose debug logging across:
  - startup visibility gating
  - crash/autosave recovery decisions
  - deferred editor refresh scheduling
  - typing-speed challenge lifecycle events

### Changed
- App/version metadata has been aligned to the `1.8.1` release line across release files, summaries, and update feed metadata.
- Quiz flows now live under the `Play` menu alongside the typing-speed challenge.
- Online example catalog entries have been consolidated into `Plugin Example Pack`, while `plugin_online_example` remains as the minimal install sample.
- Plugin menu APIs can now target existing top-level menus such as `Help`, `Tools`, and `Play` instead of being forced under `Plugins`.
- Full-document status stats remain enabled, but the expensive refresh path is now deferred so typing is more responsive.

### Fixed
- Startup recovery no longer leaks a visible main window behind recovery prompts.
- Recovery dialogs no longer self-promote into a phantom top-level shell during startup.
- Typing Speed Test tabs no longer enter autosave drafts or crash recovery state.
- Per-keystroke editor lag is reduced by moving heavy status/preview/gamification refresh work off the immediate text-change path.

## [1.8.0] - 2026-03-13

- PyPad is finally being released!!

### Added
- Fuller LSP workflow actions and supporting panels:
  - hover
  - references
  - rename
  - completion request
  - document formatting
  - diagnostics refresh into a dedicated `Problems` dock
- New dock windows integrated into the main shell:
  - `Problems`
  - `Output`
  - `GitLens`
  - `Terminal & Tasks`
  - `Git`
- Snippet Manager upgraded to support:
  - variables and tab-stop prompts
  - snippet vs template entries
  - language scoping
  - editing and deletion
  - opening templates in a new tab
- Local spellcheck support powered by `pyspellchecker` with:
  - `Tools > Spell Check Document...`
  - editor context-menu spelling suggestions for the current word
  - spellcheck language/custom dictionary settings in `Settings > Preferences > AI & Updates`
- Reopen closed tab support with:
  - `Ctrl+Shift+T`
  - `File > Close > Recently Closed Tabs...`
  - persisted recently-closed tab history with text/metadata restore
- New discoverability surfaces:
  - stronger empty-tab start surface with quick actions, recent files, and templates
  - `Help > What Can I Do Here?`
- New status-bar/status-panel selection stats item showing live word/character/line counts
- Visible gamification shell across the main window:
  - compact XP/streak widget in the status area
  - momentum banner with one-click next-move routing
  - token-driven reward toast notifications
- Productivity Hub expansion:
  - daily briefing
  - seasonal event briefing
  - session review
  - long-term milestones
  - secret trails
  - productivity routines
  - routine history
- Companion guidance now acts like a coach with actionable recommendations tied to real workflows.
- Seasonal event progress and structured secret/easter-egg tracking are now visible in the app instead of staying hidden in raw state.
- Gamification Dashboard now includes richer surfaces for:
  - seasonal event progress
  - secret trails
  - productivity routines with usage stats
- Scintilla compat contract expansion:
  - command metadata registry for `SCI_*` / `SCN_*` symbols with status/category/args/notes
  - generated compat contract reference outputs:
    - `docs/scintilla_compat_reference.json`
    - `docs/scintilla_compat_reference.md`
  - public compat contract APIs for:
    - capability reporting
    - notification contract inspection
    - notification log snapshots
    - lexer contract and lexer snapshot inspection
    - full compat state export/import round-trip
  - compat-native future-feature shims for:
    - inline diagnostics
    - semantic ranges
    - minimap state
    - code actions
  - compat contract baseline capture via `scripts/capture_scintilla_compat_contract.py`
  - generated/audited compat-first baseline file:
    - `docs/scintilla_compat_contract_baseline.json`

### Changed
- Dock title-bar theming now covers the expanded panel set so newer windows follow the same PyPad chrome and SVG close/undock controls.
- The `Window` menu now mirrors major dock/panel windows in addition to document tabs, so panel visibility is managed from one place.
- Search Results dock now includes grouped views and an inline preview pane for better review before opening or replacing.
- Shared template packs now install into the Snippet Manager library instead of staying as a disconnected helper store.
- UI presets are now positioned as `Writing`, `Coding`, and `Review` layouts.
- External file-change handling now offers `Reload from Disk`, `Keep My Changes`, or `Compare` instead of a simple yes/no prompt.
- AI prompt knowledge assembly now includes token-saving controls:
  - compact vs full knowledge mode
  - optional UI/action appendix inclusion
  - user-knowledge character cap
  - selection preview cap
- AI user knowledge remains appended separately from built-in app knowledge and no longer risks replacing it.
- Document summary now includes both character counts with and without line endings.
- Startup logging now resolves the persisted `logging_level` before main-window bootstrap so launcher/app startup respects the saved level earlier.
- Startup crash logging is cleaner:
  - normal startup status lines no longer get mirrored into `crash_tracebacks.log`
  - only Qt warning/critical/fatal messages are persisted to the crash log
  - lower-value Qt info/debug messages stay out of crash traces
- Startup runtime environment now applies quieter Chromium/WebEngine flags to reduce benign stderr noise.
- Release/update consistency checks now verify that `assets/version.txt`, `update.xml`, and installer download metadata all agree on the `1.8.0` release line.
- Empty-editor start surface styling now follows PyPad theme tokens for panels, buttons, borders, hover states, recent-file rows, and scrollbars instead of relying on ad hoc palette-derived colors.
- Empty-editor recent files now use dedicated filename/subtitle rows rather than single-line path buttons for better readability.
- Empty-editor start content now lives inside a themed scroll area so quick actions, recents, and templates remain reachable in smaller window sizes.
- Markdown preview dock now opens with a more readable width and rebalances against the editor instead of staying stuck in an overly narrow stretched column.
- Gamification and productivity systems now share one continuous state model instead of separate passive UI fragments.
- Productivity routines now route into built-in actions such as focus sprint, workspace search, command palette, bug hunt, and daily briefing.
- Routine usage is now tracked so the app can show cadence and history, not just suggestions.
- New productivity/gamification UI follows existing PyPad token-based dark/light styling instead of one-off colors.
- Scintilla compatibility is now treated as a compat-first contract instead of a fallback parity layer:
  - repo audit now validates the app's Scintilla surface against `scintilla_compat`
  - native `PySide6.Qsci` is now optional reference material, not the source of truth
  - compat contract docs and baseline files are generated from code instead of inferred manually
- Startup readiness now shows the main window as soon as the UI shell is built instead of waiting for the full deferred startup sequence, reducing perceived launch latency.

### Docs
- Updated project summaries, AI app knowledge, and the welcome demo template to reflect the released Productivity Hub, Play menu, routine tracking, and onboarding flow under the `1.8.0` version line.
- Added Scintilla compat contract documentation and generated reference outputs describing supported commands, categories, statuses, args, and notes.

### Fixed
- Removed an early recursive wrapper mistake while wiring the new terminal/tasks panel entrypoint.
- New dock windows now participate in layout sync and hidden-window detection instead of behaving like unmanaged side panels.
- Startup autosave recovery no longer causes the app to quit when the top-level recovery dialog closes before the hidden main window is shown.
- `Open Selected` recovery flow is now safe during startup by temporarily disabling `quitOnLastWindowClosed` while recovery dialogs are active.
- Recently closed tab reopening now uses explicit restore handlers instead of brittle inline dialog lambdas.
- Reopening a closed tab now correctly replaces the single blank placeholder tab instead of competing with startup tab state.
- `Spell Check Document...` now always provides visible feedback when spellcheck dependencies are missing or when no misspellings are found.
- Spellcheck suggestion generation now tolerates `pyspellchecker` returning `None` from `candidates(...)` instead of crashing with `TypeError`.
- Spellcheck suggestion generation now falls back to close dictionary matches when `pyspellchecker` returns no candidates, preventing empty suggestion panes for obvious typos.
- Custom dock title bars again position window titles, close buttons, and undock buttons correctly after the empty-state UI refactor.
- Empty-editor start surface no longer renders with off-theme black blocks and now matches PyPad dock/title/button chrome more closely.
- Scintilla compat audit no longer produces false positives from compat metadata/audit source files when validating repo symbol coverage.
- Startup timing logs now stop overstating launch readiness by using UI-ready first paint instead of full deferred session restore as the show threshold.

## [1.7.10-prerelease] - 2026-03-08

### Added
- New regression suite `tests/test_productivity_hardening.py` covering:
  - release metadata consistency (`assets/version.txt` + `update.xml`)
  - stable vs prerelease version comparison behavior
  - Quick Open scoring priority checks
  - autosave index persistence round-trip

### Changed
- Startup instrumentation in `src/run.py` now logs splash image/font prep timing for better startup profiling.
- Quick Open scoring in `src/pypad/ui/editor/quick_open_dialog.py` now prioritizes basename/path-segment matches more accurately.
- Workspace find/replace in `src/pypad/ui/workspace/workspace_controller.py` now uses safer text decode fallback order (`utf-8`, `utf-8-sig`, `cp1252`, `latin-1`) to reduce skipped files.
- AI apply behavior in `src/pypad/ui/ai/ai_chat_dock.py` now forces preview for large payloads even when legacy direct-apply mode is enabled.
- AI app knowledge assembly in `src/pypad/ai_app_knowledge.py` now appends `ai_app_knowledge_override` to built-in knowledge (instead of replacing it), via `resolve_ai_app_knowledge(...)`.
- UI appendix generation for AI app knowledge is now lazy + cached (single-process memoized) instead of being regenerated at import time.
- UI action/menu appendix extraction now uses AST parsing of `ui_setup.py` assignments/calls rather than regex/string scanning for stronger label/action detection.
- AI prompt knowledge wiring in `src/pypad/ui/ai/ai_controller.py` now resolves built-in + override knowledge in one block, removing duplicate user-knowledge block assembly.
- Plugin reliability settings now include `plugin_max_failures_before_disable` in defaults/migration coercion.
- Updater version ordering in `src/pypad/services/updater_helpers.py` now treats stable releases as newer than prereleases with the same numeric base.

### Fixed
- Autosave index writes in `src/pypad/ui/system/autosave.py` are now atomic to avoid partial/corrupt writes.
- Corrupt autosave index files are now quarantined instead of repeatedly breaking load.
- Shortcut mapper apply flow now blocks unresolved duplicate bindings when conflict policy is `block`.

## [1.7.9-prerelease] - 2026-03-07

### Creator's Thoughts
- I'd probably know this update will be massive and sometimes overwhelming, but I know I'm planning for community plugins just yet but I'd still need to consider about the approval system, moderation, rules, and anything else.
- New updates, New Features, More Fun!
- Probably, I'm gonna add more features specifically for casual and newcomers here, so they'd probably not gonna be overwhelmed at the next update.

### Upgrade Notes
- Menus are cleaner: File/Search/View now prioritize common actions and group advanced options into submenus.
- Tabs are more compact to free editor space, with improved close/pin icon alignment.
- Crash recovery is smoother: restoring/discarding recovered items no longer leaves extra blank tabs.
- Unsaved temporary tabs now persist across restarts.
- Markdown preview and export are more reliable:
  - preview direction sync is corrected
  - HTML export preserves markdown structure.

### Added
- Demo Pack templates in `templates/demo_pack/` covering onboarding, markdown, export, AI workflow, security, collaboration, and stress testing scenarios.
- New Help action: `Help > Open Demo Pack (first template)` for one-click onboarding into `01_welcome_quick_tour.md`
- Onboarding and discoverability controls in Settings (`Settings > Onboarding`):
  - enable/disable onboarding
  - toggle contextual tips
  - toggle "next unlock" prompts
  - restart tutorial now
  - reset tip history
  - reset onboarding progress
- App-level empty-workspace hint overlay shown when non-editor windows are closed:
  - `I dont have any windows :( Add me again by right clicking anywhere!`
  - theme-token compatible centered rendering outside the editor surface
- Appearance settings now include `Follow system theme` for automatic light/dark mode selection from OS color scheme.
- Scintilla compatibility strict parity pass:
  - strict `SCN_MODIFIED` payload contract (modification type, reason flags, tokenized reason string, before/after ranges, mutation sequence id)
  - richer auto-completion compatibility commands: `SCI_AUTOCSETFILLUPS`, `SCI_AUTOCGETFILLUPS`, `SCI_AUTOCSELECT`
  - fold display text compatibility commands: `SCI_FOLDSETTEXT`, `SCI_FOLDGETTEXT`
  - undo/redo transaction scaffolding with grouped action handling via `SCI_BEGINUNDOACTION` / `SCI_ENDUNDOACTION`
  - lexer incremental window scaffolding (`LexerWindow`) and compat lexer protocol support (`lex_incremental`)
  - render-layer composition pipeline for deterministic style/indicator/hotspot/overlay ordering
  - main-window integration path for forwarding Scintilla notifications through `EditorWidget.scintillaNotification` and plugin event emission (`scintilla_notification`)
- Session persistence now includes unsaved temporary tabs:
  - unsaved content, markdown mode flag, modified state, and active unsaved tab index are now stored/restored.
- Open Source Licenses dialog upgraded to list + preview layout:
  - left pane library list (title/version)
  - right pane per-library metadata preview (license/summary/home page)
  - copy selected preview text action
- Plugin system advanced feature pass:
  - Plugin Manager upgrades:
    - live filter/search by id/name/description/permissions
    - `Scaffold Plugin` flow (creates `plugin.json` + `plugin.py`)
    - unsafe UI bridge toggle
    - one-click plugin export (`Export Plugin`)
    - plugin zip inspect/install flows (`Inspect Plugin Zip`, `Install Plugin Zip`)
    - plugin diagnostics/log export (`Export Diagnostics`, `Export Logs`)
    - plugin retry/failure controls (`Retry Plugin`, `Reset Failures`)
    - plugin update checks (`Check Update`, `Check All Updates`)
    - command runner (`Run Command`) with JSON args
    - per-plugin runtime diagnostics panel (status, hook counters, errors, last run/event, metadata)
  - New `Plugins > Online Plugins...` dialog:
    - separate catalog browser (no longer embedded in Plugin Manager pane)
    - themed SVG icon controls for refresh/install
    - GitHub-backed catalog support via `plugin_online_catalog_url`
    - one-click install flow for catalog plugins (policy/security checks still enforced)
  - Manifest/compatibility metadata support:
    - `author`
    - `version`, `plugin_api_version`
    - `min_app_version`, `max_app_version`
    - `update_url`, `homepage`
    - `settings_schema`
    - `depends_on`, `provides_services`, `requires_services`
  - Plugin API expansion:
    - config/schema helpers: `plugin_config_schema`, `plugin_config_get`, `plugin_config_set`
    - runtime telemetry hooks: `log_metric`, `emit_runtime_event`
    - service contracts: `register_service`, `get_service`
    - command contracts: `register_command`, `run_command`
    - background jobs: `start_job`, `cancel_job`, `job_status`
    - structured plugin logs: `log(level, message)`
  - Host/runtime capabilities:
    - dependency-aware load ordering with cycle/missing-dependency detection
    - plugin API version compatibility enforcement
    - typed plugin-config defaulting/coercion from `settings_schema`
    - service registry and required-service resolution checks
    - command registry/list/execute pipeline
    - plugin runtime event bus and capped diagnostics event history
    - background job registry (status/progress/cancel/error lifecycle tracking)
    - plugin health scoring and failure-threshold auto-disable containment
    - archive inspect + policy dry-run path prior to install
    - per-plugin diagnostics JSON snapshot export support
- New example plugin pack additions in `plugins/` to demonstrate advanced controller-first patterns:
  - action flows: `example_action_runner`, `example_action_macro`, `example_action_bookmarks`, `example_action_searcher`
  - workspace/reporting: `example_workspace_inspector`, `example_workspace_report`, `example_workspace_todo_index`, `example_workspace_file_sampler`
  - text/edit workflows: `example_word_tools`, `example_selection_tools`, `example_selection_case_cycle`, `example_quick_insert`, `example_file_rotator`
  - hooks/state/telemetry: `example_hook_logger`, `example_save_guard`, `example_save_snapshot_trail`, `example_tab_cycle`, `example_tab_health`, `example_session_metrics_panel`, `example_session_notes`
  - AI/network/helpers: `example_ai_commit_message`, `example_hello_network`, `example_auto_tagger`

### Changed
- HTML export now auto-detects markdown syntax and renders markdown as structured HTML elements during export.
- File/Edit template menus now include dynamic Demo Pack entries (`New From Demo` and `Insert Demo`).
- First-time tutorial and post-tutorial onboarding prompts now explicitly encourage trying the Demo Pack.
- Workspace panel feature removed in favor of the Explorer panel flow; compatibility toggle paths now route to Explorer behavior.
- Search Results dock and detached Search Results window styling now follow shared token-based PyPad window patterns.
- Search Results controls are now responsive in narrow docks:
  - replace action auto-switches to compact icon-only mode at very small widths
  - compact button sizing/padding tuned to match toolbar icon button proportions
- Minimap and Symbol Outline docks now use shared custom dock title bars and themed detach/close controls, aligned with other windows.
- Minimap visuals now follow theme-token guidelines and inherit window styling behavior.
- Explorer, Editor, and Markdown Preview now use custom dock title bar widgets (aligned with AI Chat) for consistent title rendering and controls.
- Toolbar overflow customization adjusted to remove the extra blank right-edge action button.
- `SCI_SETMODEVENTMASK` notification gating now enforces stricter `SCN_*` emission filtering in compat mode.
- Edit-command and generic text-change paths now both emit normalized `SCN_MODIFIED` metadata in compat mode.
- Search flag semantics expanded with `SCFIND_POSIX` handling for word-boundary matching behavior.
- File, Search, and View menus are now compacted with clearer subgrouping:
  - essential actions remain top-level
  - dense/advanced actions moved into structured submenus.
- Tab strip layout compactness improved for more editor vertical space:
  - reduced tab padding/heights
  - tighter tab accessory layout.
- Plugin discovery now accepts UTF-8 BOM manifests (`utf-8-sig`) for broader editor/tool compatibility.
- Online plugin discovery/install moved to dedicated `Online Plugins` dialog, while Plugin Manager remains focused on local plugin runtime/admin tooling.
- Online plugin catalog and UI now surface plugin `author` metadata across list/details/diagnostics/inspect flows.

### Docs
- Updated release metadata/docs for `1.7.9-prerelease`:
  - `assets/version.txt`
  - `assets/version_info.txt`
  - `update.xml`
  - `APP_SUMMARY.md`
  - `CONTEXT_SUMMARY.md`
  - `CHANGELOG.md` (strict Scintilla parity and notification contract updates)
- Plugin docs expanded and aligned with runtime:
  - `docs/plugins.md`
  - `docs/plugin_api.md`
  - added example map and advanced manifest/API sections (compatibility, contracts, commands, jobs, diagnostics, updates, failure management)

### Tests
- Plugin-system hardening tests added/expanded:
  - `tests/test_plugin_system_contracts.py`
  - `tests/test_advanced_features.py` import path fix + compatibility with feature module layout
  - coverage now includes:
    - PluginAPI contract checks
    - example plugin discovery/smoke load behavior
    - scaffold + export flows
    - manifest compatibility gating (app version + plugin API version)
    - typed settings schema coercion/defaulting
    - runtime event logging
    - service contract resolution
    - command registry/list/run behavior
    - background job lifecycle status/cancel checks
    - plugin archive inspect/install flows
    - plugin health score and failure counter behavior
    - update metadata checks (`update_url`) and diagnostics snapshot shape

### Fixed
- Startup crash in Search Results theming caused by missing token attributes (`button_text`, `button_hover_bg`) now resolved using valid UI theme tokens.
- Search Results appearance regression where styles were not fully unified with other themed windows.
- Settings navigation now shows both PyPad and N++ pages immediately on open (`All` scope), instead of requiring an N++ scope switch first.
- SVG icon recoloring now also rewrites style-based `fill`/`stroke` declarations, fixing icons that stayed dark after switching to dark mode.
- Added a one-time icon cache/signature reset right after `Save & Close` settings apply, forcing immediate same-frame icon color refresh.
- Tab file SVG icons now refresh for all open tabs when theme/icon settings are applied, fixing stale white icons after switching to light mode.
- Settings apply flow now preserves the current main-window mode (`normal`/`maximized`/`fullscreen`) instead of unintentionally restoring to normal.
- Layout snapshots now persist explicit main-window mode and restore it on startup, including fallback from settings when no active layout payload exists.
- Added startup debug logs for window-mode restore path:
  - `[Startup] Restoring window mode: <mode>`
  - `[Startup] Restoring window mode: <mode> (fallback)`
- Plugin storage path now uses `%APPDATA%\\pypad\\plugins` (instead of `%APPDATA%\\notepadclone\\plugins`) with automatic non-destructive migration of legacy plugin files/folders.
- Close-event trace logging noise reduced; full stack trace output is now debug-only instead of always-on.
- Empty-workspace hint visibility logic corrected so the message does not appear while the editor dock is visible.
- Markdown preview layout drift fixed:
  - preview direction now syncs to active editor tab direction (prevents RTL/LTR mismatch rendering).
- Crash recovery no longer leaves stray blank startup tabs when restoring or discarding recovery entries.
- Tab close/pin badge accessory sizing tuned to prevent icon/text cropping in compact tab mode.
- Online plugin catalog fetch now uses resilient mixed-source decode fallback (`utf-8` then `utf-8-sig`) to tolerate BOM/non-BOM remote JSON.
- Online plugin install now normalizes fetched `plugin.json`/`plugin.py` text to UTF-8 without BOM before policy parsing, fixing `U+FEFF` parser/policy failures.

## [1.7.8-prerelease] - 2026-03-06

### Added
- In-tab media experience for non-text files:
  - image/audio/video now open inside the editor tab instead of popup dialogs
  - media controls include play/pause/stop, seek/progress bar, elapsed/total time, and volume slider
  - `Open Raw in Editor` is available in the media header and reuses the same tab
- Gamification dashboard promoted to a full visual dialog with tabs:
  - Quests
  - Skill Tree
  - Companion
  - Crafted Tools
  - Seasonal Events

### Changed
- Explorer panel visual style aligned closer to VSCode:
  - compact header/action strip
  - custom chevron glyph delegate
  - tighter row density and cleaner branch rendering
  - theme-aware dark/light icon tint refresh
- Explorer interactions expanded:
  - richer context menu commands
  - keyboard shortcuts for file operations
  - `Open Shell Menu` now opens in-app context menu instead of launching system Explorer
- Workspace open behavior now persists selected root immediately and no longer auto-opens files/dialogs.

### Fixed
- `Open Raw in Editor` no longer leaves media tab in a blank/disconnected state or forces an extra tab.

## [1.7.7-prerelease] - 2026-03-06

### Added
- Quiz mode restored and expanded in the editor:
  - mixed-format parser for MCQ, True/False, and short-answer blocks
  - metadata formats accepted: `{answer:X}`, `[answer=X]`, `(correct: X)`, `{keywords: ...}`
  - `{user}` / `[user]` answer anchors (above or below question)
  - status-bar quiz controls: `Quit` and `Finish`
  - detailed scoring dialog (totals, type totals, per-question rows)
- Quiz format help dialog restored to a full detailed guide with examples and scoring notes.
- Dedicated quiz tests added (`tests/test_quiz_mode.py`) covering parser/scoring/placeholder behavior.
- AI panel quick-action UX restored:
  - `+` action menu with SVG icons
  - Add Files file-picker attachment flow
  - inline status row (`Status: Idle/Thinking/Streaming/Error`)

### Changed
- Quiz placeholder placement now prefers the first non-option line under each question for cleaner alignment.
- Parser now avoids non-gradable help bullets and marker-only sample lines to prevent visual ghost artifacts.
- Theme restart behavior remains explicit-only (`Reload App`) instead of automatic app-close restart.

### Fixed
- Preferences save/theme changes no longer trigger unintended app close.
- Cached settings-dialog reset flag is now cleared before each open to prevent accidental factory-reset close path.
- Added temporary close-event trace logging to capture shutdown trigger path in logs.

## [1.7.6-prerelease] - 2026-02-27

### Added
- Settings dialog: LSP server preference fields for Python/JavaScript/TypeScript.
- Settings dialog: factory reset action with explicit confirmation (resets defaults and closes app).
- PySide6-native Scintilla compatibility engine (`scintilla_compat.py`) used when `PySide6.Qsci` is unavailable.
- Margin rendering and interactions:
  - fold glyphs, marker glyphs, line numbers
  - per-margin width/type/mask/sensitivity handling
  - margin click signaling by margin index
- Marker symbol family support for compatibility backend (circle/arrow/plus/minus/rect/empty variants).
- Indicator and hotspot primitives:
  - indicator ranges with style variants and colors
  - hotspot ranges with payloads and hover/click signals
  - indicator hover/click signals with payloads
- Lightweight calltip/annotation API compatibility methods.
- Richer lexer-style token overlays for Python/JS/TS/JSON/Markdown in compat mode.

### Changed
- LSP go-to-definition client hardening:
  - configurable initialize/request timeouts
  - per-server retry attempts
  - optional verbose LSP event logging
  - server preference order respected from settings
- Tuned default LSP settings based on smoke timings:
  - initialize timeout: `2.5s`
  - request timeout: `2.0s`
  - retries: `2`
- Editor fallback behavior no longer degrades to plain QTextEdit-only mode; advanced editor actions are routed through compatibility backend.
- Column (rectangular) editing now persists block selection across compatible edits in column mode.
- Multi-caret workflows improved:
  - synchronized backspace/delete
  - synchronized navigation (`Left`/`Right`/`Home`/`End`)
  - row-aware multi-paste behavior
- Folding behavior expanded:
  - indentation + bracket-guided fold region detection
  - fold-all/fold-line/fold-level support in compat mode
- Visual symbol toggles (`space/tab`, `EOL`, `control`, `indent guides`, `wrap`) now render in compat backend.

### Fixed
- Windows server command parsing now handles quoted executable paths with spaces for LSP server settings.
- Removed hard dependency on importing `PySide6.Qsci` for bookmark marker symbol setup in fallback mode.
- Restored syntax/search/line-style overlays for compatibility backend by distinguishing native-vs-compat Scintilla handling.

## [1.7.4-prerelease] - 2026-02-26

- A BIG UPDATE! (yet!)

### Added
- Shared token-based UI theme system used across main window chrome, dialogs, Quick Open, and AI Chat surfaces.
- Quick Open / Go to Anything upgrades:
  - `@symbol`, `@@symbol`, `@w symbol`, and scoped `@@filepattern symbol`
  - background file/symbol indexing and persistent caches
  - grouped result sections and `Tab` / `Shift+Tab` mode cycling
  - live incremental refresh while indexing
- AI chat bubble one-click actions:
  - Insert / Replace Selection / Append / New Tab
  - Replace Whole File
  - Open Diff Preview
- Visual UI regression tooling:
  - offscreen screenshot smoke captures
  - HTML manifest (`tests_tmp/visual_smoke_phase2/index.html`)
  - baseline compare/update mode with perceptual hash threshold
  - committed baseline file and CI gate
- CI workflow split for UI checks:
  - fast UI theme/dialog tests
  - runtime smoke
  - visual smoke baseline compare
- `scripts/run_ui_checks.ps1` wrapper for local split UI checks (`-Fast`, `-Runtime`, `-Visual`, `-All`).

### Changed
- App UI overhauled to a soft modern rounded style across core chrome:
  - tabs, toolbars, menus, docks, status bar, scrollbars
- High-traffic dialogs and panels aligned to the new theme language:
  - Settings, Tutorial, Autosave, Workspace dialogs, AI edit preview/rewrite, Debug Logs, updater dialogs
- Additional custom/niche dialogs now use shared dialog theming (Windows Manager, macro run dialog, open-source licenses, clipboard/jump/search results/history panels, user guide, document summary, and others).
- `User Defined Language` dialog now uses token-based dialog styling instead of a local hardcoded dark/light stylesheet.
- `main_window` package export changed to lazy `Notepad` import to avoid circular import issues in UI tests/fixtures.

### Fixed
- AI chat insert-offer parsing now accepts `OFF_INSERT` alias tokens in addition to `OFFER_INSERT`.
- `apply_settings()` hover-mode tab-close theming ordering bug (`tab_close_icon_url` used before assignment).
- `apply_settings()` hover close-button QSS f-string brace escaping bug causing runtime `NameError` in hover mode.
- Quick Open incremental refresh now detects same-count updates using content signatures/hashes.

## [1.7.2-prerelease] - 2026-02-21

### Added
- Snap Dock actions (left/right/bottom) with shortcuts for fast panel placement.
- Live layout persistence for dock moves, toolbar moves/float, and visibility changes.
- Per-tab editor splitter sizes stored by file path.
- More settings features are added

### Changed
- AI chat dock can be placed on left/right/bottom.

## [1.6.12-prerelease] - 2026-02-21

### Fixed
- Fixed UI freezing when non-English language translation was triggered during app startup or when changing language from Settings.

### Changed
- Translation flow is now non-blocking: cache miss translations are queued in a background worker instead of running network translation on the UI thread.
- Language application now remains responsive even with large action/widget translation passes.

## [1.6.11-prerelease] - 2026-02-19

### Changes
- No API key message navigation 

## [1.6.10-prerelease] - 2026-02-19

### Added
- Startup arguments now support opening folders as workspace roots (shows Workspace Files).

### Changed
- Startup file opening now keeps the first file active instead of switching to the last.

### Fixed
- Fixed workspace dialog acceptance check to use `QDialog.Accepted`, preventing a crash.

### Added
- New top-level `Search` menu with Notepad++-style actions and submenus:
  - Find in Files, Select-and-Find next/previous, Volatile find next/previous
  - Incremental Search, Go To, Mark, Change History, style/copy-styled workflows
  - Extended bookmark operations (cut/copy/replace/remove/invert bookmarked lines)
- Expanded `View` menu with richer Notepad++-style structure:
  - Always on Top, Post-it mode, Distraction Free mode
  - View Current File in (Explorer/default viewer/CMD)
  - Show Symbol submenu (space/tab, EOL, non-printing/control chars, indent guides, wrap symbol)
  - Fold/Unfold actions (all/current/level-based), text direction RTL/LTR, project panel shortcuts
- True QScintilla line-hiding support:
  - `Hide Lines` now uses Scintilla line hiding for selected/current lines
  - Added `Show Hidden Lines` (`Alt+Shift+H`) to restore hidden lines
- Command palette with fuzzy action search (`Ctrl+Shift+P`).
- AI rewrite quick actions for selected text:
  - shorten
  - formal
  - fix grammar
  - summarize
- AI rewrite diff preview dialog with selectable hunks before applying edits.
- AI prompt template workflow:
  - run saved/default templates
  - save custom templates
- Context-aware AI action: "Ask About This File...".
- AI usage meter in the status bar and session usage summary dialog.
- AI action history log (timestamp, action, model, prompt/response sizes).
- AI private mode toggle that blocks outgoing AI requests for sensitive work.
- Simple mode toggle and one-click UI presets:
  - Reading
  - Coding
  - Focus
- Experimental advanced feature pack:
  - Plugin system with permission model (`file`, `network`, `ai`) and Plugin Manager UI
  - Minimap dock + symbol outline dock + breadcrumbs
  - Basic go-to-definition and diff/merge helpers
  - Snippet engine + shared template packs
  - TODO/FIXME task workflow with due-date reminder sync
  - AI extras: file citations, commit/changelog drafting, batch refactor preview
  - Backup scheduler + diagnostics bundle export
  - Keyboard-only mode + accessibility presets
  - LAN collaboration baseline + annotation layer
- Plugin documentation:
  - `docs/plugins.md`
- Example plugin:
  - `plugins/example_word_tools`
- Windows shell integration commands in `run.py`:
  - `--register-shell-menu`
  - `--unregister-shell-menu`
  - Registers/removes `Open with Pypad` for File Explorer context menu (current user).
- Inno Setup packaging support:
  - `installer/NotepadClone.iss`
  - `build_installer.bat`
  - Optional installer tasks for `.txt` association and context menu entry.
- Configurable backup output directory:
  - new setting key `backup_output_dir`
  - picker in Preferences `Backup & Restore`
  - used by Backup Scheduler and Run Backup Now.

### Changed
- Reassigned Pin Tab shortcut from `Ctrl+Shift+P` to `Ctrl+Alt+P` to avoid conflict with Command Palette.
- Toolbar overflow (`>>`) behavior reworked:
  - converted to right-edge overlay button instead of regular toolbar action
  - dynamic hidden-tools menu now uses proxy actions for reliable text entries.

### Fixed
- Prevented startup/runtime crashes from stale/deleted Qt action wrappers (`QWidgetAction` / `QAction`) by adding defensive `RuntimeError` guards in shortcut and tooltip/action wiring paths.
- Fixed overflow menu flicker while resizing/opening menus by avoiding layout-request-triggered rapid rebuilds.
- Fixed off-screen placement of overlay `>>` button by anchoring to toolbar `contentsRect()`.
- Fixed mojibake/garbled labels in Preferences navigation and buttons (emoji/category text).
- Fixed `build_installer.bat` parse error (`was was unexpected at this time`) caused by unescaped parentheses in a block `echo`.

## [1.6.9-prerelease] - 2026-02-18

### Changed
- Updated `notepad.xml` release feed metadata for `1.6.9-prerelease`.
- Refined updater UI flow with non-blocking update-available dialog behavior.
- Expanded updater debug logs with worker/thread lifecycle and feed parsing details.

### Fixed
- Fixed updater cross-thread UI interactions that could cause unresponsive behavior.
- Fixed overlapping/manual-vs-auto update check handling during startup checks.
- Fixed update check timeout behavior with watchdog cancellation for stalled network calls.

## [1.6.8-prerelease] - 2026-02-18

### Changed
- Updated release feed payload in `notepad.xml` for `1.6.8-prerelease` and new installer URL.
- Update checker now supports plain-text feed payloads as fallback when XML is malformed/non-XML.
- Update check timeout behavior tightened and watchdog timeout handling added.
- Updater debug logging expanded with detailed step-by-step traces.

### Fixed
- Fixed updater action signal wiring so manual update checks always run as manual checks.
- Fixed missing `QTimer` import in updater progress flow.
- Fixed updater cross-thread UI access that caused Qt parent/thread warnings and freeze-like behavior.
- Switched `Update Available` popup to non-blocking dialog flow to avoid nested event-loop lockups.

## [1.6.5-prerelease] - 2026-02-17

### Fixed
- Corrected asset path resolution in development mode so icons are loaded from `assets/` reliably.
- Replaced missing-toolbar placeholder/paper icons by adding SVG assets for:
  - `edit-cut`, `edit-copy`, `edit-paste`
  - `edit-undo`, `edit-redo`
  - `document-print`, `zoom-in`, `zoom-out`
  - `document-new`, `document-open`, `document-save`, `document-save-all`
- Fixed light-mode tab close icon color:
  - added explicit `tab-close-light.svg` / `tab-close-dark.svg` and theme-aware selection in QSS.
- Fixed SVG recolor pipeline regression that could make icons render blank:
  - monochrome recoloring now safely rewrites only valid `stroke`/`fill` attributes.

### Changed
- Main toolbar icon mapping now prefers project SVG icon assets consistently for clearer cross-platform appearance.

## [1.6.4-prerelease] - 2026-02-17

### Changed
- Fixed additional light/dark theming inconsistencies across main window UI:
  - Search toolbar labels, checkboxes, input, and action buttons now follow active theme colors.
  - Status bar language combo and dropdown list now follow active theme colors.
- Fixed AI panel theme mode detection to use effective icon/text brightness, preventing mixed light/dark panel states.
- Updated main-window SVG tinting to use effective icon color (`_icon_color`) first, then dark-mode fallback.
- Added dedicated Preferences dialog styling for dark/light mode so its panels, lists, inputs, and buttons are consistently themed.
- Accent color preview in Preferences now updates dialog theme immediately when picking or clearing accent color.

## [1.6.3-prerelease] - 2026-02-17

### Changed
- Enforced strict SVG icon coloring by theme:
  - Light mode: all rendered SVG icons use black (`#000000`).
  - Dark mode: all rendered SVG icons use white (`#ffffff`).
- Updated main window SVG icon renderer to use black/white semantic icon colors.
- Updated AI panel SVG icon renderer to use black/white semantic icon colors.

## [1.6.2-prerelease] - 2026-02-17

### Changed
- AI panel now enforces SVG icon usage with in-memory tinted icon rendering.
- Light mode AI icons are recolored to dark/black tones in memory.
- Dark mode AI icons are recolored to light tones in memory.
- AI panel icon cache now refreshes correctly when theme changes.
- AI panel message action icons are refreshed after theme changes.

## [1.6.1-prerelease] - 2026-02-17

### Added
- Left-dock AI Chat Panel with:
  - message bubbles
  - live streaming generation
  - cancel/stop in-flight generation
  - per-message copy and insert-to-tab actions
- AI chat history persistence in settings (`ai_chat_history`).
- Runtime translation support using Google Translate with on-disk translation cache.
- Translation cache clear action in preferences.
- New AI/chat icon assets:
  - `assets/icons/ai-send.svg`
  - `assets/icons/ai-stop.svg`
  - `assets/icons/ai-copy.svg`
  - `assets/icons/ai-insert.svg`
- New tests:
  - `tests/test_ai_controller.py`
  - `tests/test_updater_controller.py`

### Changed
- Top-level `Settings` menu introduced; moved:
  - `Preferences...` (renamed from `Settings...`)
  - `Shortcut Mapper...`
- `Ask AI...` now opens/focuses the AI Chat Panel.
- Explain-selection AI prompt now uses:
  - `Explain this text: {selection}`
- Missing API key error now provides direct setup instructions and API key URL.
- AI chat bubbles now render Markdown content, including streamed responses.
- Dark mode bubble styling updated to gray-black backgrounds with white text.

### Removed
- `Generate Text to Tab` action from AI menu/workflow.

---

And the older changelogs and versions were forgotten...
