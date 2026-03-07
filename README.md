# Pypad

Pypad is a PySide6 desktop text editor focused on fast note-taking and power-user workflows.
- More than a simple notepad app, PyPad includes powerful tools for productivity, quick navigation, and workspace management.

## Project Status

PyPad is currently in **pre-release** and under active development.
Some features are experimental and may change as the editor evolves.

Development happens during my free time, so updates may be irregular.

## Features

- 🚀 Fast multi-tab editing
- 🔍 Quick Open (Ctrl+Alt+P) for files, symbols, and commands
- 🤖 AI assistant dock with apply actions
- 📝 Markdown preview and tools
- 💾 Autosave and crash recovery
- 🗂 Workspace search
- 🎨 Token-based UI theming
- 🎨 Command Palette (Ctrl+Shift+P) for quick commands

## Goals

The long-term goals of PyPad include:

- Build a fast and reliable desktop editor for everyday writing and coding
- Provide powerful navigation tools for large projects
- Keep the UI customizable through token-based theming
- Expand AI-assisted workflows while keeping the editor lightweight
- Maintain a clean architecture that is easy to extend

## Preview

*The picture below does not reflect on the actual app experience as the app ui layout can be updated anytime.

### Splash
![Pypad Splash](assets/splash.png)

### Main Window
![Pypad Main Window](pictures/mainwindow.png)

### Settings Dialog
![Pypad Settings Dialog](pictures/settingsdialog.png)

## Install / Run

- Development: run `src/run.py`
- Build: `compile.bat`
- Version file: `assets/version.txt`
- Installer artifacts (when built): `dist/installer/`

## Key Paths

- Main window: `src/pypad/ui/main_window/window.py`
- Theme tokens / chrome QSS: `src/pypad/ui/theme_tokens.py`
- Dialog theming helpers: `src/pypad/ui/dialog_theme.py`
- AI chat dock: `src/pypad/ui/ai_chat_dock.py`
- Quick Open dialog: `src/pypad/ui/quick_open_dialog.py`
- Settings dialog: `src/pypad/ui/main_window/settings_dialog.py`
- Update feed metadata: `update.xml`

## UI Test / Visual Regression Commands

- Fast UI checks:
  - `powershell -File scripts/run_ui_checks.ps1 -Fast`
- Runtime smoke:
  - `powershell -File scripts/run_ui_checks.ps1 -Runtime`
- Visual smoke baseline compare:
  - `powershell -File scripts/run_ui_checks.ps1 -Visual`
- Update visual baseline (intentional refresh):
  - `powershell -File scripts/run_ui_checks.ps1 -Visual -UpdateVisualBaseline`

## Notes

- `tests/visual_smoke_phase2_baseline.json` is the committed visual baseline used by CI.
- `tests_tmp/visual_smoke_phase2/index.html` is generated during visual smoke runs for quick review.

## Credits
I use OpenAI Codex to turbo-boost my productivity. However, I still have to use my coding skills, ideas and any decisions for that.
