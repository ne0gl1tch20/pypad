"""Provide test-time import compatibility for older module paths.

The repository has moved several UI modules into clearer subpackages over time.
Some tests still import the older flat paths or the older ``notepadclone``
package name. This shim keeps the test suite focused on behavior instead of
failing during collection because of import-path drift.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _alias_module(alias: str, target: str) -> None:
    """Expose one module under an older import path for compatibility tests."""

    if alias in sys.modules:
        return
    sys.modules[alias] = importlib.import_module(target)


_ALIASES = {
    "pypad.ui.ai_chat_dock": "pypad.ui.ai.ai_chat_dock",
    "pypad.ui.ai_edit_preview_dialog": "pypad.ui.ai.ai_edit_preview_dialog",
    "pypad.ui.autosave": "pypad.ui.system.autosave",
    "pypad.ui.debug_logs_dialog": "pypad.ui.debug.debug_logs_dialog",
    "pypad.ui.dialog_theme": "pypad.ui.theme.dialog_theme",
    "pypad.ui.quick_open_dialog": "pypad.ui.editor.quick_open_dialog",
    "pypad.ui.shortcut_mapper": "pypad.ui.editor.shortcut_mapper",
    "pypad.ui.theme_tokens": "pypad.ui.theme.theme_tokens",
    "pypad.ui.tutorial_dialog": "pypad.ui.features.tutorial_dialog",
    "pypad.ui.updater_controller": "pypad.ui.system.updater_controller",
    "pypad.ui.updater_helpers": "pypad.services.updater_helpers",
    "pypad.ui.workspace_controller": "pypad.ui.workspace.workspace_controller",
    "notepadclone": "pypad",
    "notepadclone.app_settings": "pypad.app_settings",
    "notepadclone.app_settings.defaults": "pypad.app_settings.defaults",
    "notepadclone.i18n": "pypad.i18n",
    "notepadclone.i18n.translator": "pypad.i18n.translator",
    "notepadclone.ui": "pypad.ui",
    "notepadclone.ui.ai": "pypad.ui.ai",
    "notepadclone.ui.ai.ai_controller": "pypad.ui.ai.ai_controller",
    "notepadclone.ui.autosave": "pypad.ui.system.autosave",
    "notepadclone.ui.ai_chat_dock": "pypad.ui.ai.ai_chat_dock",
    "notepadclone.ui.ai_edit_preview_dialog": "pypad.ui.ai.ai_edit_preview_dialog",
    "notepadclone.ui.debug_logs_dialog": "pypad.ui.debug.debug_logs_dialog",
    "notepadclone.ui.main_window": "pypad.ui.main_window",
    "notepadclone.ui.main_window.misc": "pypad.ui.main_window.misc",
    "notepadclone.ui.main_window.settings_dialog": "pypad.ui.main_window.settings_dialog",
    "notepadclone.ui.quick_open_dialog": "pypad.ui.editor.quick_open_dialog",
    "notepadclone.ui.shortcut_mapper": "pypad.ui.editor.shortcut_mapper",
    "notepadclone.ui.tutorial_dialog": "pypad.ui.features.tutorial_dialog",
    "notepadclone.ui.updater_controller": "pypad.ui.system.updater_controller",
    "notepadclone.ui.updater_helpers": "pypad.services.updater_helpers",
    "notepadclone.ui.workspace_controller": "pypad.ui.workspace.workspace_controller",
}

for alias_name, target_name in _ALIASES.items():
    _alias_module(alias_name, target_name)
