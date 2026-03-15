import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PySide6.QtWidgets import QApplication, QMainWindow

from pypad.app_settings.defaults import build_default_settings
from pypad.ui.ai.ai_chat_dock import AIChatDock
from pypad.ui.features.advanced_features import OnlinePluginsDialog, PluginManagerDialog
from pypad.ui.features.tutorial_dialog import InteractiveTutorialDialog
from pypad.ui.workspace.workspace_dialog import WorkspaceFilesDialog, WorkspaceSearchDialog, WorkspaceSearchResult


class _ParentWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = build_default_settings(default_style="Windows", font_family="Segoe UI", font_size=11)

    def _svg_icon(self, _name: str):
        from PySide6.QtGui import QIcon

        return QIcon()


class _Host:
    def __init__(self, window: _ParentWindow) -> None:
        self.window = window
        self.plugins_dir = ROOT

    def runtime_mode_label(self) -> str:
        return "production"

    def discover(self):
        return []

    def load_online_plugin_catalog(self):
        return []


class _AIController:
    def __init__(self, window: _ParentWindow) -> None:
        self.window = window


class AccessibilitySmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_workspace_dialogs_expose_accessible_names(self) -> None:
        parent = _ParentWindow()
        files_dialog = WorkspaceFilesDialog(parent, "C:/workspace", ["a.txt"])
        search_dialog = WorkspaceSearchDialog(
            parent,
            "todo",
            [WorkspaceSearchResult(path="a.txt", line_no=2, line_text="todo item")],
        )
        self.assertEqual(files_dialog.accessibleName(), "Workspace files dialog")
        self.assertEqual(files_dialog.list_widget.accessibleName(), "Workspace files list")
        self.assertEqual(search_dialog.accessibleName(), "Workspace search results dialog")
        self.assertEqual(search_dialog.preview.accessibleName(), "Workspace search preview")

    def test_ai_chat_dock_exposes_accessible_names_and_reduced_motion(self) -> None:
        parent = _ParentWindow()
        parent.settings["accessibility_reduce_motion"] = True
        dock = AIChatDock(parent, ai_controller=_AIController(parent))
        self.assertEqual(dock.accessibleName(), "AI chat dock")
        self.assertEqual(dock.input.accessibleName(), "AI chat prompt input")
        self.assertTrue(dock._reduce_motion_enabled())

    def test_plugin_dialogs_expose_accessible_names(self) -> None:
        parent = _ParentWindow()
        host = _Host(parent)
        manager = PluginManagerDialog(parent, host)
        online = OnlinePluginsDialog(parent, host)
        self.assertEqual(manager.accessibleName(), "Plugin manager dialog")
        self.assertEqual(manager.list_widget.accessibleName(), "Installed plugins list")
        self.assertEqual(online.accessibleName(), "Online plugins dialog")
        self.assertEqual(online.details.accessibleName(), "Online plugin details")

    def test_tutorial_dialog_skips_animation_when_reduce_motion_enabled(self) -> None:
        parent = _ParentWindow()
        parent.settings["accessibility_reduce_motion"] = True
        dialog = InteractiveTutorialDialog(parent)
        self.assertTrue(dialog._reduce_motion_enabled())
        dialog._next_step()
        self.assertEqual(dialog.opacity.opacity(), 1.0)


if __name__ == "__main__":
    unittest.main()
