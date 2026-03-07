# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project uses Semantic Versioning.


## [1.7.9-prerelease] - 2026-03-07

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

### Docs
- Updated release metadata/docs for `1.7.9-prerelease`:
  - `assets/version.txt`
  - `assets/version_info.txt`
  - `update.xml`
  - `APP_SUMMARY.md`
  - `CONTEXT_SUMMARY.md`
  - `CHANGELOG.md` (strict Scintilla parity and notification contract updates)

### Fixed
- Startup crash in Search Results theming caused by missing token attributes (`button_text`, `button_hover_bg`) now resolved using valid UI theme tokens.
- Search Results appearance regression where styles were not fully unified with other themed windows.
- Settings navigation now shows both PyPad and N++ pages immediately on open (`All` scope), instead of requiring an N++ scope switch first.
- SVG icon recoloring now also rewrites style-based `fill`/`stroke` declarations, fixing icons that stayed dark after switching to dark mode.
- Added a one-time icon cache/signature reset right after `Save & Close` settings apply, forcing immediate same-frame icon color refresh.
- Close-event trace logging noise reduced; full stack trace output is now debug-only instead of always-on.
- Empty-workspace hint visibility logic corrected so the message does not appear while the editor dock is visible.
- Markdown preview layout drift fixed:
  - preview direction now syncs to active editor tab direction (prevents RTL/LTR mismatch rendering).
- Crash recovery no longer leaves stray blank startup tabs when restoring or discarding recovery entries.
- Tab close/pin badge accessory sizing tuned to prevent icon/text cropping in compact tab mode.

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
