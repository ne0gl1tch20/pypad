"""Coordinate split-view presentation details for paired editor panes.

This module keeps split-view focus styling and user-facing state descriptions
separate from the main-window action wiring. The controller does not create the
split itself; it explains and decorates an existing split so the UI feels
intentional and accessible.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QEvent, Qt


class SplitViewController(QObject):
    """Manage split-view focus state, labels, and accessibility metadata."""

    def __init__(self, window) -> None:
        """Bind the controller to the main window that owns the editor tabs."""

        super().__init__(window)
        self.window = window

    @staticmethod
    def orientation_label(orientation: Qt.Orientation) -> str:
        """Return a user-facing label for the split orientation."""

        return "Vertical Split" if orientation == Qt.Horizontal else "Horizontal Split"

    def install_for_tab(self, tab) -> None:
        """Attach focus tracking and accessible descriptions to the split editors."""

        clone_editor = getattr(tab, "clone_editor", None)
        if clone_editor is None:
            return
        for widget, label in (
            (tab.text_edit.widget, "Primary editor pane"),
            (clone_editor.widget, "Secondary editor pane"),
        ):
            try:
                widget.installEventFilter(self)
                widget.setAccessibleName(label)
                widget.setAccessibleDescription(
                    "One pane of the active split editor. Use Focus on Another View to move between panes."
                )
            except Exception:
                continue
        self.set_active_pane(tab, tab.text_edit.widget)

    def teardown_for_tab(self, tab) -> None:
        """Remove split-view focus metadata from a tab that is returning to single view."""

        for editor in (getattr(tab, "text_edit", None), getattr(tab, "clone_editor", None)):
            widget = getattr(editor, "widget", None)
            if widget is None:
                continue
            try:
                widget.removeEventFilter(self)
            except Exception:
                pass
            widget.setProperty("splitActivePane", False)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def set_active_pane(self, tab, widget) -> None:
        """Mark one pane as active so split focus remains visually obvious."""

        clone_editor = getattr(tab, "clone_editor", None)
        widgets = [tab.text_edit.widget]
        if clone_editor is not None:
            widgets.append(clone_editor.widget)
        for candidate in widgets:
            active = candidate is widget
            try:
                candidate.setProperty("splitActivePane", active)
                candidate.style().unpolish(candidate)
                candidate.style().polish(candidate)
            except Exception:
                continue
        if hasattr(self.window, "split_status_label"):
            description = "Single view"
            if clone_editor is not None and getattr(clone_editor.widget, "isVisible", lambda: False)():
                orientation = self.orientation_label(tab.editor_splitter.orientation())
                pane_name = "Primary" if widget is tab.text_edit.widget else "Secondary"
                description = f"{orientation} | {pane_name} pane active"
            self.window.split_status_label.setText(description)
            self.window.split_status_label.setToolTip(description)

    def eventFilter(self, watched, event):  # type: ignore[override]
        """Track focus changes on split panes so the active pane remains highlighted."""

        if event.type() != QEvent.Type.FocusIn:
            return super().eventFilter(watched, event)
        tab = self.window.active_tab()
        if tab is None or getattr(tab, "clone_editor", None) is None:
            return super().eventFilter(watched, event)
        if watched in {tab.text_edit.widget, tab.clone_editor.widget}:
            self.set_active_pane(tab, watched)
        return super().eventFilter(watched, event)
