# Pypad - App Summary

Last updated: 2026-03-14
Release target: `1.8.1`

## Product Snapshot

Pypad is a PySide6 desktop editor that combines note-taking, coding and markdown workflows, workspace tooling, AI-assisted editing, and a visible productivity/gamification layer. The app uses a token-based dark/light theme system across the main window, dialogs, docks, and newer feature surfaces.

Current release focus:
- startup and recovery hardening:
  - recovery dialogs no longer promote into phantom startup shells
  - main window remains hidden until startup is actually ready
  - typing-test play tabs are excluded from autosave/crash recovery state
- editor responsiveness without dropping full stats:
  - full-document counters remain available in the status area
  - heavy status/gamification refresh work is deferred off the keystroke path
- more explicit Play-mode polish:
  - typing speed challenge gets dedicated status controls
  - quiz/play flows now live under the `Play` menu with dedicated SVG icons
- IDE-style workflow expansion:
  - fuller LSP actions for hover, references, rename, completion, formatting, and diagnostics
  - dedicated dock windows for Problems, Output, GitLens, Terminal & Tasks, and Git
  - stronger search-results review UX and a richer snippet/template manager
- visible gamification shell in the main window:
  - compact XP and quest widget in the status area
  - momentum banner with one-click next-move routing
  - themed reward toasts
- Productivity Hub dock with:
  - daily briefing
  - seasonal event briefing
  - session review
  - long-term milestones
  - secret trails
  - productivity routines
  - routine history
- companion guidance now routes into practical flows such as focus sprint, workspace search, command palette, bug hunt, and planning loop
- Gamification Dashboard now includes richer tabs for seasonal events, secret trails, and tracked productivity routines
- local spellcheck, reopen-closed-tab support, discoverability help, and token-based empty-state UI remain part of the current release line

## Major Capabilities

- Multi-tab editing with detachable tabs, pin/favorite/read-only states, tags, and per-tab metadata
- QScintilla-like editor experience in PySide6-only environments
- Markdown formatting tools and live preview
- Workspace files/search dialogs and search result navigation
- LSP-assisted code navigation/edit workflows with dedicated output/problem surfaces
- Autosave, crash recovery, and version history with diff preview
- Per-note encryption (`.encnote`) and app privacy lock options
- AI chat dock, AI inline edits, workspace citation workflows, and diff/apply previews
- Visible productivity/gamification systems layered into the main shell and `Play` menu
- Expanded debug logging around startup, recovery, autosave, and deferred editor refresh paths
- Update checking/downloading from XML feed (`update.xml`)
- Unified Preferences (PyPad + Notepad++ compatibility pages)

## UI Status

Implemented:
- shared `UIThemeTokens` in `src/pypad/ui/theme/theme_tokens.py`
- token-driven main-window chrome QSS (tabs, toolbars, menus, docks, status bar, scrollbars)
- token-driven dialog theme system in `src/pypad/ui/theme/dialog_theme.py`
- token-aligned high-traffic dialogs and panels:
  - Settings
  - Tutorial
  - Autosave and recovery
  - Quick Open / Go to Anything
  - AI Chat dock and AI edit preview dialogs
  - Debug Logs and updater dialogs
  - Search Results, Problems, Output, GitLens, Terminal & Tasks, and Git docks
- productivity/gamification surfaces:
  - status widget
  - momentum banner
  - Productivity Hub
  - Gamification Dashboard additions

Remaining style islands should be limited to small inline utility surfaces rather than major product areas.

## Key Architecture

Main window class:
- `src/pypad/ui/main_window/window.py` (`Notepad`)

Mixins:
- `src/pypad/ui/main_window/ui_setup.py`
- `src/pypad/ui/main_window/file_ops.py`
- `src/pypad/ui/main_window/edit_ops.py`
- `src/pypad/ui/main_window/view_ops.py`
- `src/pypad/ui/main_window/misc.py`

Core UI modules:
- `src/pypad/ui/features/gamification_system.py`
- `src/pypad/ui/features/gamification_widgets.py`
- `src/pypad/ui/features/gamification_dashboard_dialog.py`
- `src/pypad/ui/editor/scintilla_compat.py`
- `src/pypad/ui/theme/theme_tokens.py`
- `src/pypad/ui/theme/dialog_theme.py`
- `src/pypad/ui/editor/quick_open_dialog.py`
- `src/pypad/ui/ai/ai_chat_dock.py`
- `src/pypad/ui/ai/ai_edit_preview_dialog.py`

Settings system:
- `src/pypad/ui/main_window/settings_dialog.py`
- `src/pypad/app_settings/defaults.py`
- `src/pypad/app_settings/coercion.py`

## QA / Regression Tooling

Focused checks for the current productivity shell:
- `tests/test_gamification_system.py`
- `tests/test_ui_theme_tokens.py`
- `tests/test_productivity_hardening.py`

Broader UI/runtime tooling still present:
- `tests/test_dialog_theme.py`
- `tests/test_main_theme_qss_builder.py`
- `tests/test_settings_apply_runtime.py`
- `tests/test_ui_visual_smoke_screenshots.py`

## Current Productivity Layer

Visible surfaces:
- compact status-area widget for level, XP, and current quest
- momentum banner for current next move
- Productivity Hub dock
- Gamification Dashboard dialog

Tracked concepts:
- quests
- streaks
- activity timeline
- seasonal event progress
- milestones
- secret progress
- productivity routines
- routine history

## Release Metadata Files

- App version: `assets/version.txt`
- Windows version info: `assets/version_info.txt`
- Update feed: `update.xml`
- Human changelog: `CHANGELOG.md`
