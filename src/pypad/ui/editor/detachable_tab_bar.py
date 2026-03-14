"""Define a custom tab bar that supports detaching, reordering, and managing editor tabs.

This module belongs to the editor widget and text-manipulation UI layer. It helps explain how `pypad.ui.editor` is structured and where this file fits into the runtime workflow.
"""

from PySide6.QtCore import QPoint, Qt, QMimeData, Signal
from PySide6.QtGui import QDrag, QColor, QPainter, QIcon
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QTabBar, QToolButton, QWidget

class DetachableTabBar(QTabBar):
    """Class that implements the `DetachableTabBar` runtime behavior."""
    detach_requested = Signal(int, QPoint)
    _tab_mime_type = "application/x-pypad-tab"
    _badge_size = 10

    def __init__(self, parent=None) -> None:
        """Initialize the `detachable_tab_bar` state for this instance."""
        super().__init__(parent)
        self._drag_start_pos: QPoint | None = None
        self._drag_index = -1
        self.detach_enabled = True
        self.setAcceptDrops(True)
        self.setUsesScrollButtons(True)
        self.setElideMode(Qt.ElideRight)
        self.setExpanding(False)

    def tabInserted(self, index: int) -> None:  # type: ignore[override]
        """Execute the `tabInserted` workflow."""
        super().tabInserted(index)
        self._install_close_button(index)

    def _install_close_button(self, index: int) -> None:
        """Internal helper for `_install_close_button`."""
        if index < 0:
            return
        existing = self.tabButton(index, QTabBar.RightSide)
        pinned = self._tab_is_pinned(index)
        favorite = self._tab_is_favorite(index)
        if isinstance(existing, QWidget) and bool(existing.property("pypad_tab_right_container")):
            pin_label = existing.findChild(QLabel, "pypadTabPinBadge")
            favorite_label = existing.findChild(QLabel, "pypadTabFavoriteBadge")
            close_btn = existing.findChild(QToolButton, "pypadTabCloseButton")
            if close_btn is not None:
                self._style_close_button(close_btn)
                close_btn.setVisible(not pinned)
                close_btn.setEnabled(not pinned)
            self._set_pin_badge(pin_label, pinned)
            self._set_favorite_badge(favorite_label, favorite)
            return
        close_btn = existing if isinstance(existing, QToolButton) else None
        if close_btn is None:
            close_btn = QToolButton(self)
            close_btn.clicked.connect(self._emit_close_from_button)
        self._style_close_button(close_btn)
        container = QWidget(self)
        container.setProperty("pypad_tab_right_container", True)
        container.setFixedHeight(14)
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 1, 1, 1)
        row.setSpacing(1)
        pin_label = QLabel(container)
        pin_label.setObjectName("pypadTabPinBadge")
        pin_label.setAlignment(Qt.AlignCenter)
        pin_label.setFixedSize(self._badge_size, self._badge_size)
        row.addWidget(pin_label, 0, Qt.AlignVCenter)
        favorite_label = QLabel(container)
        favorite_label.setObjectName("pypadTabFavoriteBadge")
        favorite_label.setAlignment(Qt.AlignCenter)
        favorite_label.setFixedSize(self._badge_size, self._badge_size)
        row.addWidget(favorite_label, 0, Qt.AlignVCenter)
        close_btn.setObjectName("pypadTabCloseButton")
        row.addWidget(close_btn, 0, Qt.AlignVCenter)
        # Reserve enough width for pin + favorite + close so tab text doesn't overlap.
        container.setFixedWidth((self._badge_size * 2) + 12 + 5)
        self._set_pin_badge(pin_label, pinned)
        self._set_favorite_badge(favorite_label, favorite)
        close_btn.setVisible(not pinned)
        close_btn.setEnabled(not pinned)
        self.setTabButton(index, QTabBar.RightSide, container)

    def refresh_tab_accessory(self, index: int) -> None:
        """Execute the `refresh_tab_accessory` workflow."""
        self._install_close_button(index)

    @staticmethod
    def _style_close_button(button: QToolButton) -> None:
        """Internal helper for `_style_close_button`."""
        button.setAutoRaise(True)
        button.setCursor(Qt.ArrowCursor)
        button.setToolTip("Close tab")
        button.setText("x")
        button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        button.setStyleSheet("")
        font = button.font()
        font.setPixelSize(9)
        button.setFont(font)
        button.setFixedSize(12, 12)

    def _tab_is_pinned(self, index: int) -> bool:
        """Internal helper for `_tab_is_pinned`."""
        tab = self._tab_obj(index)
        return bool(getattr(tab, "pinned", False))

    def _tab_is_favorite(self, index: int) -> bool:
        """Internal helper for `_tab_is_favorite`."""
        tab = self._tab_obj(index)
        return bool(getattr(tab, "favorite", False))

    def _tab_obj(self, index: int):
        """Internal helper for `_tab_obj`."""
        tab_widget = self.parentWidget()
        if tab_widget is None or not hasattr(tab_widget, "widget"):
            return None
        try:
            return tab_widget.widget(index)
        except Exception:
            return None

    def _set_pin_badge(self, label: QLabel | None, pinned: bool) -> None:
        """Internal helper for `_set_pin_badge`."""
        if label is None:
            return
        if not pinned:
            label.clear()
            label.setVisible(False)
            label.setToolTip("")
            return
        icon = self._pin_badge_icon(size=self._badge_size)
        pixmap = icon.pixmap(self._badge_size, self._badge_size)
        if pixmap.isNull():
            label.clear()
            label.setVisible(False)
            label.setToolTip("")
            return
        label.setPixmap(pixmap)
        label.setVisible(True)
        label.setToolTip("Pinned tab")

    def _pin_badge_icon(self, size: int = 10):
        """Internal helper for `_pin_badge_icon`."""
        return self._named_badge_icon("tab-pin", size=size)

    def _set_favorite_badge(self, label: QLabel | None, favorite: bool) -> None:
        """Internal helper for `_set_favorite_badge`."""
        if label is None:
            return
        if not favorite:
            label.clear()
            label.setVisible(False)
            label.setToolTip("")
            return
        icon = self._favorite_badge_icon(size=self._badge_size)
        pixmap = icon.pixmap(self._badge_size, self._badge_size)
        if pixmap.isNull():
            label.clear()
            label.setVisible(False)
            label.setToolTip("")
            return
        label.setPixmap(pixmap)
        label.setVisible(True)
        label.setToolTip("Favorite tab")

    def _favorite_badge_icon(self, size: int = 10):
        """Internal helper for `_favorite_badge_icon`."""
        return self._named_badge_icon("tab-heart", size=size)

    def _named_badge_icon(self, name: str, size: int = 10) -> QIcon:
        """Internal helper for `_named_badge_icon`."""
        host_window = self.window()
        icon_fn = getattr(host_window, "_svg_icon_colored", None)
        if callable(icon_fn):
            try:
                return icon_fn(name, size=size)
            except Exception:
                pass
        return QIcon()

    def tabLayoutChange(self) -> None:  # type: ignore[override]
        """Execute the `tabLayoutChange` workflow."""
        super().tabLayoutChange()
        for index in range(self.count()):
            self._install_close_button(index)

    def _emit_close_from_button(self) -> None:
        """Internal helper for `_emit_close_from_button`."""
        button = self.sender()
        if not isinstance(button, QToolButton):
            return
        center = button.mapTo(self, button.rect().center())
        index = self.tabAt(center)
        if index >= 0 and not self._tab_is_pinned(index):
            self.tabCloseRequested.emit(index)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """Execute the `mousePressEvent` workflow."""
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            self._drag_index = self.tabAt(event.pos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        """Execute the `mouseMoveEvent` workflow."""
        if not self.detach_enabled:
            super().mouseMoveEvent(event)
            return
        if (
            self._drag_start_pos is not None
            and self._drag_index >= 0
            and (event.pos() - self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance()
            and not self.rect().contains(event.pos())
        ):
            tab_widget = self.parentWidget()
            host_window = tab_widget.window() if tab_widget is not None else None
            source_window_id = getattr(host_window, "window_id", -1)

            drag = QDrag(self)
            mime = QMimeData()
            payload = f"{source_window_id}:{self._drag_index}".encode("ascii", errors="ignore")
            mime.setData(self._tab_mime_type, payload)
            drag.setMimeData(mime)
            result = drag.exec(Qt.MoveAction)
            if result != Qt.MoveAction:
                self.detach_requested.emit(self._drag_index, event.globalPosition().toPoint())
            self._drag_start_pos = None
            self._drag_index = -1
            return
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        """Execute the `dragEnterEvent` workflow."""
        if event.mimeData().hasFormat(self._tab_mime_type):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        """Execute the `dragMoveEvent` workflow."""
        if event.mimeData().hasFormat(self._tab_mime_type):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        """Execute the `dropEvent` workflow."""
        if not event.mimeData().hasFormat(self._tab_mime_type):
            super().dropEvent(event)
            return

        payload = bytes(event.mimeData().data(self._tab_mime_type)).decode("ascii", errors="ignore")
        parts = payload.split(":")
        if len(parts) != 2:
            event.ignore()
            return
        try:
            source_window_id = int(parts[0])
            source_index = int(parts[1])
        except ValueError:
            event.ignore()
            return

        target_tab_widget = self.parentWidget()
        target_window = target_tab_widget.window() if target_tab_widget is not None else None
        receive_fn = getattr(target_window, "receive_external_tab", None)
        if callable(receive_fn):
            insert_index = self.tabAt(event.position().toPoint())
            moved = bool(receive_fn(source_window_id, source_index, insert_index))
            if moved:
                event.acceptProposedAction()
                return
        event.ignore()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        """Execute the `mouseReleaseEvent` workflow."""
        if event.button() == Qt.MiddleButton:
            index = self.tabAt(event.pos())
            if index >= 0 and not self._tab_is_pinned(index):
                host_window = self.window()
                close_fn = getattr(host_window, "close_tab", None)
                if callable(close_fn):
                    close_fn(index)
                else:
                    self.tabCloseRequested.emit(index)
                self._drag_start_pos = None
                self._drag_index = -1
                return
        self._drag_start_pos = None
        self._drag_index = -1
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        """Execute the `paintEvent` workflow."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        for index in range(self.count()):
            data = self.tabData(index)
            if not data:
                continue
            color = QColor(str(data))
            if not color.isValid():
                continue
            rect = self.tabRect(index)
            strip = rect.adjusted(3, 3, -3, -rect.height() + 6)
            painter.fillRect(strip, color)
        painter.end()

    def contextMenuEvent(self, event) -> None:  # type: ignore[override]
        """Execute the `contextMenuEvent` workflow."""
        index = self.tabAt(event.pos())
        host_window = self.window()
        show_fn = getattr(host_window, "show_tab_context_menu", None)
        if callable(show_fn):
            show_fn(index, event.globalPos())
            return
        super().contextMenuEvent(event)




