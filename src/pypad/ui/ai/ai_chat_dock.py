"""Implement the docked AI chat surface that lets users ask questions and apply AI-generated suggestions.

This module belongs to the AI-assisted editing and collaboration UI layer. It helps explain how `pypad.ui.ai` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

import base64
import difflib
import hashlib
import json
import re
import socket
from datetime import datetime
from html import escape as html_escape
from pathlib import Path
from typing import TYPE_CHECKING, Callable
from urllib.parse import parse_qs, unquote, urlparse

from PySide6.QtCore import QByteArray, QRect, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QTextDocument
from PySide6.QtGui import QColor, QIcon, QKeyEvent, QKeySequence, QPainter, QPixmap, QResizeEvent, QShortcut
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFrame,
    QHBoxLayout,
    QLayout,
    QLayoutItem,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QMenu,
    QInputDialog,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)
from pypad.ui.theme.asset_paths import resolve_asset_path
from pypad.ui.ai.ai_collaboration import build_workspace_citation_snippets, paragraph_bounds
from pypad.ui.ai.ai_edit_preview_dialog import AIEditPreviewDialog
from pypad.ui.document.document_fidelity import render_markdown_to_mathjax_html
from pypad.services.workspace_search_helpers import collect_workspace_files, search_files_for_query
from pypad.ui.main_window.notepadpp_pref_runtime import is_clickable_scheme_allowed
from pypad.ui.theme.theme_tokens import build_ai_chat_qss, build_tokens_from_settings
from pypad.app_settings import get_ai_chats_dir_path
from pypad.logging_utils import get_logger

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except Exception:
    QWebEngineView = None

if TYPE_CHECKING:
    from pypad.ui.ai.ai_controller import AIController

_LOGGER = get_logger(__name__)


class _FlowLayout(QLayout):
    """Class that implements the `_FlowLayout` runtime behavior."""
    def __init__(self, parent: QWidget | None = None, *, h_spacing: int = 6, v_spacing: int = 6) -> None:
        """Initialize the `ai_chat_dock` state for this instance."""
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing

    def addItem(self, item: QLayoutItem) -> None:
        """Execute the `addItem` workflow."""
        self._items.append(item)

    def count(self) -> int:
        """Execute the `count` workflow."""
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:
        """Execute the `itemAt` workflow."""
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:
        """Execute the `takeAt` workflow."""
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):  # type: ignore[override]
        """Execute the `expandingDirections` workflow."""
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        """Execute the `hasHeightForWidth` workflow."""
        return True

    def heightForWidth(self, width: int) -> int:
        """Execute the `heightForWidth` workflow."""
        return self._do_layout(QRect(0, 0, max(0, width), 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        """Execute the `setGeometry` workflow."""
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        """Execute the `sizeHint` workflow."""
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        """Execute the `minimumSize` workflow."""
        size = QSize(0, 0)
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, *, test_only: bool) -> int:
        """Internal helper for `_do_layout`."""
        margins = self.contentsMargins()
        x = rect.x() + margins.left()
        y = rect.y() + margins.top()
        line_height = 0
        max_right = rect.right() - margins.right()
        if max_right < x:
            max_right = x

        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width()
            if line_height > 0 and next_x > max_right:
                x = rect.x() + margins.left()
                y += line_height + self._v_spacing
                next_x = x + hint.width()
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(x, y, hint.width(), hint.height()))
            x = next_x + self._h_spacing
            line_height = max(line_height, hint.height())

        return (y - rect.y()) + line_height + margins.bottom()


class _HoverActionRow(QWidget):
    """Class that implements the `_HoverActionRow` runtime behavior."""
    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the `ai_chat_dock` state for this instance."""
        super().__init__(parent)
        self._actions_widget: QWidget | None = None
        self._actions_enabled = True

    def set_actions_widget(self, widget: QWidget | None) -> None:
        """Update state handled by `set_actions_widget`."""
        self._actions_widget = widget
        if self._actions_widget is not None:
            self._actions_widget.setVisible(False)

    def set_actions_enabled(self, enabled: bool) -> None:
        """Update state handled by `set_actions_enabled`."""
        self._actions_enabled = bool(enabled)
        if self._actions_widget is not None:
            self._actions_widget.setVisible(False)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        """Execute the `enterEvent` workflow."""
        if self._actions_widget is not None and self._actions_enabled:
            self._actions_widget.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        """Execute the `leaveEvent` workflow."""
        if self._actions_widget is not None:
            self._actions_widget.setVisible(False)
        super().leaveEvent(event)


class _Bubble(QFrame):
    """Class that implements the `_Bubble` runtime behavior."""
    _HIDDEN_COMMAND_RE = re.compile(
        r"\[PYPAD_CMD_(?:(?:OFFER|OFF)_INSERT|SET_FILE|SET_CHAT_TITLE|OFFER_PATCH|PROPOSE_ACTION)_BEGIN\].*?\[PYPAD_CMD_(?:(?:OFFER|OFF)_INSERT|SET_FILE|SET_CHAT_TITLE|OFFER_PATCH|PROPOSE_ACTION)_END\]",
        re.DOTALL | re.IGNORECASE,
    )
    _BROKEN_BUTTON_LINK_RE = re.compile(
        r"style\s*=\s*['\"][^'\"]*display\s*:\s*inline-block[^'\"]*['\"]\s*>\s*Open\s+([a-z0-9/_-]+)`?",
        re.IGNORECASE,
    )
    _BROKEN_PYPAD_ANCHOR_RE = re.compile(
        r"<a\b[^>]*href\s*=\s*['\"](pypad://[^'\"\s>]+)['\"][^>]*>([^<\n`]*)`?",
        re.IGNORECASE,
    )
    _TRUNCATED_PYPAD_ANCHOR_RE = re.compile(
        r"<a\b[^>]*href\s*=\s*['\"](pypad://[^'\"\s>]+)",
        re.IGNORECASE,
    )
    _MARKDOWN_PYPAD_LINK_RE = re.compile(
        r"\[([^\]]*?)\]\((pypad://[^)\s]+)\)+",
        re.IGNORECASE,
    )
    _BROKEN_MARKDOWN_PYPAD_LINK_RE = re.compile(
        r"\[([^\]]*?)\]\((pypad://[^\s]+)",
        re.IGNORECASE,
    )
    _PYPAD_LINK_RE = re.compile(r"(?<![\w/\"'])(pypad://[^\s<>'\")]+)", re.IGNORECASE)
    _MATH_RE = re.compile(
        r"\$[^$]+\$|\$\$[\s\S]+\$\$|\\\([^\)]+\\\)|\\\[[\s\S]+\\\]|\\begin\{[a-zA-Z*]+\}|"
        r"[A-Za-z]\s*=\s*[^=\n]+|\d+\s*[-+*/=^]\s*\d+|\\frac|\\sqrt|\\sum|\\int|\\alpha|\\beta|\\theta|\\pi",
        re.IGNORECASE,
    )
    _PEANO_CHAIN_RE = re.compile(r"\bS\(\s*(S\(\s*)*0\s*(\)\s*)+\)")

    def __init__(
        self,
        text: str,
        role: str,
        parent: QWidget | None = None,
        copy_icon_data_uri: str = "",
        on_pypad_link: Callable[[str], bool] | None = None,
    ) -> None:
        """Initialize the `ai_chat_dock` state for this instance."""
        super().__init__(parent)
        self._role = role
        self._raw_text = text
        self._copy_icon_data_uri = copy_icon_data_uri
        self._on_pypad_link = on_pypad_link
        self._code_blocks: list[str] = []
        self._view = QTextBrowser(self)
        self._view.setFrameStyle(QFrame.NoFrame)
        self._view.setReadOnly(True)
        self._view.setOpenExternalLinks(False)
        self._view.setOpenLinks(False)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._view.document().setDocumentMargin(0)
        self._view.anchorClicked.connect(self._on_anchor_clicked)
        self._web_view = None
        if QWebEngineView is not None:
            try:
                self._web_view = QWebEngineView(self)
                self._web_view.setVisible(False)
                self._web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            except Exception:
                self._web_view = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.addWidget(self._view)
        if self._web_view is not None:
            lay.addWidget(self._web_view)
        if role == "user":
            self.setObjectName("userBubble")
        else:
            self.setObjectName("assistantBubble")
        self._render_markdown()
        self._sync_height()

    def append_text(self, text: str) -> None:
        """Execute the `append_text` workflow."""
        self._raw_text += text
        self._render_markdown()
        self._sync_height()

    def set_text(self, text: str) -> None:
        """Update state handled by `set_text`."""
        self._raw_text = text
        self._render_markdown()
        self._sync_height()

    def text(self) -> str:
        """Execute the `text` workflow."""
        return self._HIDDEN_COMMAND_RE.sub("", self._raw_text).strip()

    def _render_markdown(self) -> None:
        """Internal helper for `_render_markdown`."""
        if self._should_use_mathjax():
            self._render_markdown_mathjax()
            return
        if self._web_view is not None:
            self._web_view.setVisible(False)
        self._view.setVisible(True)
        if self._role != "assistant":
            self._view.setMarkdown(self._raw_text)
            return

        self._code_blocks = []
        pypad_links: list[str] = []
        card_idx = 0

        def _replace_fenced(match: re.Match[str]) -> str:
            """Internal helper for `_replace_fenced`."""
            nonlocal card_idx
            raw_label = (match.group(1) or "").strip()
            label = raw_label if raw_label else f"Code {card_idx + 1}"
            code = (match.group(2) or "").rstrip("\n")
            self._code_blocks.append(code)
            safe_label = html_escape(label)
            safe_code = html_escape(code)
            href = f"copy-code:{card_idx}"
            card_idx += 1
            copy_icon_html = ""
            if self._copy_icon_data_uri:
                copy_icon_html = (
                    f"<img src='{self._copy_icon_data_uri}' width='12' height='12' "
                    "style='vertical-align:middle;margin-right:4px;'/>"
                )
            return (
                "<div style='margin:8px 0;border:1px solid #5a5f66;border-radius:6px;overflow:hidden;'>"
                "<div style='display:flex;justify-content:space-between;align-items:center;"
                "padding:6px 8px;background:#2a2f36;'>"
                f"<span style='font-weight:600;'>{safe_label}</span>"
                f"<a href='{href}' style='text-decoration:none;'>{copy_icon_html}Copy Code</a>"
                "</div>"
                "<pre style='margin:0;padding:10px;overflow:auto;background:#1f2329;'>"
                f"<code>{safe_code}</code>"
                "</pre>"
                "</div>"
            )

        clean_text = self._HIDDEN_COMMAND_RE.sub("", self._raw_text)
        clean_text = self._normalize_broken_pypad_buttons(clean_text)
        clean_text = self._normalize_peano_notation(clean_text)
        processed = re.sub(r"```([^\n`]*)\n(.*?)```", _replace_fenced, clean_text, flags=re.DOTALL)

        def _replace_pypad_with_placeholder(match: re.Match[str]) -> str:
            """Internal helper for `_replace_pypad_with_placeholder`."""
            href = str(match.group(1) or "").strip()
            if not href:
                return ""
            token = f"[[PYPAD_LINK_{len(pypad_links)}]]"
            pypad_links.append(href)
            return token

        processed = self._PYPAD_LINK_RE.sub(_replace_pypad_with_placeholder, processed)
        doc = QTextDocument()
        doc.setDefaultStyleSheet(
            """
            p { margin-top: 0px; margin-bottom: 4px; }
            ul, ol { margin-top: 2px; margin-bottom: 4px; margin-left: 14px; padding-left: 0px; }
            li { margin-top: 0px; margin-bottom: 1px; }
            h1, h2, h3, h4, h5, h6 { margin-top: 4px; margin-bottom: 4px; }
            pre { margin-top: 4px; margin-bottom: 4px; }
            """
        )
        doc.setMarkdown(processed)
        html = doc.toHtml()
        for idx, href in enumerate(pypad_links):
            html = html.replace(f"[[PYPAD_LINK_{idx}]]", self._pypad_link_html(href))
        self._view.setHtml(html)

    def _should_use_mathjax(self) -> bool:
        """Internal helper for `_should_use_mathjax`."""
        if self._web_view is None:
            return False
        text = str(self._raw_text or "")
        if "```" in text or "pypad://" in text or "copy-code:" in text:
            return False
        return bool(self._MATH_RE.search(text))

    def _render_markdown_mathjax(self) -> None:
        """Internal helper for `_render_markdown_mathjax`."""
        if self._web_view is None:
            return
        window = self.window()
        settings = getattr(window, "settings", {}) if window is not None else {}
        dark_mode = bool(settings.get("dark_mode", False))
        clean_text = self._HIDDEN_COMMAND_RE.sub("", self._raw_text)
        clean_text = self._normalize_broken_pypad_buttons(clean_text)
        clean_text = self._normalize_peano_notation(clean_text)
        clean_text = self._normalize_escaped_math_delimiters(clean_text)
        html = render_markdown_to_mathjax_html(clean_text, dark_mode=dark_mode)
        self._view.setVisible(False)
        self._web_view.setVisible(True)
        # Ensure the bubble is visible immediately even before JS height probes return.
        self._web_view.setMinimumHeight(96)
        self._web_view.setFixedHeight(180)
        self._web_view.setHtml(html)
        try:
            self._web_view.page().runJavaScript(
                "Math.max(document.body.scrollHeight || 0, document.documentElement.scrollHeight || 0)",
                self._apply_web_height,
            )
        except Exception:
            self._web_view.setFixedHeight(180)

    def _apply_web_height(self, value) -> None:
        """Internal helper for `_apply_web_height`."""
        try:
            height = int(float(value))
        except Exception:
            height = 160
        height = max(80, min(1200, height + 12))
        if self._web_view is not None:
            self._web_view.setFixedHeight(height)

    @staticmethod
    def _normalize_escaped_math_delimiters(text: str) -> str:
        # Many model outputs escape math delimiters for markdown (\$...\$).
        # Normalize those back so MathJax can parse equations.
        """Internal helper for `_normalize_escaped_math_delimiters`."""
        normalized = str(text or "")
        normalized = normalized.replace("\\$", "$")
        normalized = normalized.replace("\\[", "[")
        normalized = normalized.replace("\\]", "]")
        return normalized

    @classmethod
    def _normalize_peano_notation(cls, text: str) -> str:
        # Convert obvious unary Peano chains (S(...S(0)...)) to plain integers.
        # This is a display-only cleanup for AI responses.
        """Internal helper for `_normalize_peano_notation`."""
        value = str(text or "")

        def _replace(match: re.Match[str]) -> str:
            """Internal helper for `_replace`."""
            token = match.group(0)
            n = token.count("S(")
            # Keep output bounded/safe for huge nested chains.
            if n < 0 or n > 10000:
                return token
            return str(n)

        return cls._PEANO_CHAIN_RE.sub(_replace, value)

    @classmethod
    def _normalize_broken_pypad_buttons(cls, text: str) -> str:
        """Internal helper for `_normalize_broken_pypad_buttons`."""
        def _replace_markdown_link(match: re.Match[str]) -> str:
            """Internal helper for `_replace_markdown_link`."""
            href = cls._normalize_pypad_href(str(match.group(2) or ""))
            return href or match.group(0)

        def _replace_anchor(match: re.Match[str]) -> str:
            """Internal helper for `_replace_anchor`."""
            href = cls._normalize_pypad_href(str(match.group(1) or ""))
            label = str(match.group(2) or "").strip()
            if not href:
                return match.group(0)
            # Keep surrounding sentence readable; button rendering will happen in the next pass.
            return href if not label else href

        text = cls._MARKDOWN_PYPAD_LINK_RE.sub(_replace_markdown_link, text)
        text = cls._BROKEN_MARKDOWN_PYPAD_LINK_RE.sub(_replace_markdown_link, text)
        text = cls._BROKEN_PYPAD_ANCHOR_RE.sub(_replace_anchor, text)
        text = cls._TRUNCATED_PYPAD_ANCHOR_RE.sub(
            lambda m: cls._normalize_pypad_href(str(m.group(1) or "")),
            text,
        )

        def _replace(match: re.Match[str]) -> str:
            """Internal helper for `_replace`."""
            path = str(match.group(1) or "").strip().strip("/")
            if not path:
                return match.group(0)
            return f"pypad://{path}"

        return cls._BROKEN_BUTTON_LINK_RE.sub(_replace, text)

    @staticmethod
    def _normalize_pypad_href(href: str) -> str:
        """Internal helper for `_normalize_pypad_href`."""
        value = str(href or "").strip()
        if not value:
            return ""
        # Trim markdown emphasis/code punctuation that can stick to bare links.
        value = value.rstrip("`*_)],.;:!?\"'")
        # Common malformed case from markdown/bold wrapping around links.
        value = re.sub(r"\*{1,}$", "", value)
        return value

    @staticmethod
    def _label_for_pypad_link(href: str) -> str:
        """Internal helper for `_label_for_pypad_link`."""
        normalized = _Bubble._normalize_pypad_href(href).lower()
        mapping = {
            "pypad://settings": "Open Settings",
            "pypad://settings/ai-updates": "Open AI & Updates",
            "pypad://settings/appearance": "Open Appearance Settings",
            "pypad://settings/editor": "Open Editor Settings",
            "pypad://settings/workspace": "Open Workspace Settings",
            "pypad://settings/shortcuts": "Open Shortcuts Settings",
            "pypad://ai/chat": "Open AI Chat",
            "pypad://workspace": "Open Workspace",
            "pypad://workspace/files": "Open Workspace Files",
            "pypad://workspace/search": "Open Workspace Search",
        }
        if normalized in mapping:
            return mapping[normalized]
        target = normalized.replace("pypad://", "", 1).strip("/") or "link"
        return f"Open {target}"

    def _pypad_link_html(self, href: str) -> str:
        """Internal helper for `_pypad_link_html`."""
        href = self._normalize_pypad_href(href)
        if not href:
            return ""
        safe_href = html_escape(href, quote=True)
        label = html_escape(self._label_for_pypad_link(href))
        return (
            f"<a href='{safe_href}' style='display:inline-block;margin:2px 4px 2px 0;"
            "padding:4px 8px;border-radius:6px;border:1px solid #5a5f66;"
            "background:#2a2f36;color:#ffffff;text-decoration:none;'>"
            f"{label}</a>"
        )

    def _on_anchor_clicked(self, url: QUrl) -> None:
        """Internal helper for `_on_anchor_clicked`."""
        href = self._normalize_pypad_href(url.toString())
        window = self.window()
        settings = getattr(window, "settings", {}) if window is not None else {}
        if href.startswith("pypad://"):
            if callable(self._on_pypad_link) and self._on_pypad_link(href):
                return
            QDesktopServices.openUrl(QUrl(href))
            return
        if not href.startswith("copy-code:"):
            if not is_clickable_scheme_allowed(settings, href):
                _LOGGER.debug("AI chat blocked external link due to scheme filter href=%r", href)
                QMessageBox.information(self, "Blocked Link", f"Link scheme is disabled by Clickable Link Settings.\n\n{href}")
                return
            QDesktopServices.openUrl(url)
            return
        try:
            index = int(href.split(":", 1)[1])
        except (TypeError, ValueError):
            return
        if 0 <= index < len(self._code_blocks):
            QApplication.clipboard().setText(self._code_blocks[index])

    def _sync_height(self) -> None:
        """Internal helper for `_sync_height`."""
        if self._web_view is not None and self._web_view.isVisible():
            try:
                self._web_view.page().runJavaScript(
                    "Math.max(document.body.scrollHeight || 0, document.documentElement.scrollHeight || 0)",
                    self._apply_web_height,
                )
            except Exception:
                self._web_view.setFixedHeight(max(120, self._web_view.height()))
            return
        width = max(220, self._view.viewport().width())
        self._view.document().setTextWidth(width)
        doc_height = self._view.document().size().height()
        self._view.setFixedHeight(int(doc_height + 8))

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Execute the `resizeEvent` workflow."""
        super().resizeEvent(event)
        self._sync_height()


class _DockTitleBar(QWidget):
    """Class that implements the `_DockTitleBar` runtime behavior."""
    def __init__(self, dock: "AIChatDock") -> None:
        """Initialize the `ai_chat_dock` state for this instance."""
        super().__init__(dock)
        self.setObjectName("aiChatTitleBar")
        self._dock = dock
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 4, 4)
        layout.setSpacing(4)
        self.label = QLabel("AI Chat", self)
        self.label.setObjectName("aiChatTitleLabel")
        self.mathjax_label = QLabel("", self)
        self.mathjax_label.setObjectName("aiChatMathJaxLabel")
        self.float_btn = QToolButton(self)
        self.close_btn = QToolButton(self)
        for btn in (self.float_btn, self.close_btn):
            btn.setAutoRaise(True)
            btn.setFixedSize(20, 20)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.float_btn.setToolTip("Float / Dock")
        self.close_btn.setToolTip("Close")
        self.float_btn.clicked.connect(self._toggle_floating)
        self.close_btn.clicked.connect(self._dock.close)
        layout.addWidget(self.label)
        layout.addWidget(self.mathjax_label)
        layout.addStretch(1)
        layout.addWidget(self.float_btn)
        layout.addWidget(self.close_btn)
        self.setMinimumHeight(28)

    def _toggle_floating(self) -> None:
        """Internal helper for `_toggle_floating`."""
        self._dock.setFloating(not self._dock.isFloating())


class _AIChatInputEdit(QPlainTextEdit):
    """Class that implements the `_AIChatInputEdit` runtime behavior."""
    def __init__(self, parent: QWidget, on_send: Callable[[], None]) -> None:
        """Initialize the `ai_chat_dock` state for this instance."""
        super().__init__(parent)
        self._on_send = on_send

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Execute the `keyPressEvent` workflow."""
        modifiers = event.modifiers()
        key = event.key()
        if modifiers == Qt.KeyboardModifier.ControlModifier and key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_send()
            event.accept()
            return
        super().keyPressEvent(event)


class AIChatDock(QDockWidget):
    """Class that implements the `AIChatDock` runtime behavior."""
    apply_completed = Signal(str, bool, str)
    _INSERT_CMD_RE = re.compile(
        r"\[PYPAD_CMD_(?:OFFER|OFF)_INSERT_BEGIN\](.*?)\[PYPAD_CMD_(?:OFFER|OFF)_INSERT_END\]",
        re.DOTALL | re.IGNORECASE,
    )
    _SET_FILE_CMD_RE = re.compile(
        r"\[PYPAD_CMD_SET_FILE_BEGIN\](.*?)\[PYPAD_CMD_SET_FILE_END\]",
        re.DOTALL | re.IGNORECASE,
    )
    _SET_CHAT_TITLE_CMD_RE = re.compile(
        r"\[PYPAD_CMD_SET_CHAT_TITLE_BEGIN\](.*?)\[PYPAD_CMD_SET_CHAT_TITLE_END\]",
        re.DOTALL | re.IGNORECASE,
    )
    _PATCH_CMD_RE = re.compile(
        r"\[PYPAD_CMD_OFFER_PATCH_BEGIN\](.*?)\[PYPAD_CMD_OFFER_PATCH_END\]",
        re.DOTALL | re.IGNORECASE,
    )
    _PROPOSE_ACTION_CMD_RE = re.compile(
        r"\[PYPAD_CMD_PROPOSE_ACTION_BEGIN\](.*?)\[PYPAD_CMD_PROPOSE_ACTION_END\]",
        re.DOTALL | re.IGNORECASE,
    )

    def __init__(self, parent: QWidget, ai_controller: "AIController") -> None:
        """Initialize the `ai_chat_dock` state for this instance."""
        super().__init__("AI Chat", parent)
        self.setObjectName("aiChatDock")
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        self.ai_controller = ai_controller
        self._active_reply_bubble: _Bubble | None = None
        self._active_reply_index: int | None = None
        self._external_on_done: Callable[[str], None] | None = None
        self._history: list[dict[str, str]] = []
        self._pending_prompt_edit_row: QWidget | None = None
        self._chat_sessions: list[dict[str, object]] = []
        self._active_chat_id: str = ""
        self._start_menu_filter_text: str = ""
        self._start_menu_rebuild_active = False
        self._pending_insert_offer: str | None = None
        self._pending_set_file_offer: str | None = None
        self._pending_patch_offer: dict[str, object] | None = None
        self._pending_local_action: dict[str, object] | None = None
        self._ai_response_correlation_seq = 0
        self._active_response_correlation_id: str | None = None
        self._pending_apply_correlation_id: str | None = None
        self._icon_cache: dict[tuple[str, str, int], QIcon] = {}
        self._copy_code_icon_data_uri = ""
        self._typing_timer = QTimer(self)
        self._typing_timer.setInterval(320)
        self._typing_timer.timeout.connect(self._advance_typing_animation)
        self._typing_step = 0
        self._typing_active = False
        self._received_stream_content = False
        self._title_bar = _DockTitleBar(self)
        self.setTitleBarWidget(self._title_bar)

        host = QWidget(self)
        host.setObjectName("aiChatHost")
        self.setWidget(host)
        root = QVBoxLayout(host)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        top_row = QHBoxLayout()
        self.start_menu_btn = QToolButton(host)
        self.start_menu_btn.setText("Start")
        self.start_menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.start_menu_btn.setToolTip("Saved chats and chat actions")
        self.start_menu = QMenu(self.start_menu_btn)
        self.start_menu.aboutToShow.connect(self._rebuild_start_menu)
        self.start_menu_btn.setMenu(self.start_menu)
        self.chat_title_label = QLabel("New Chat", host)
        self.chat_title_label.setObjectName("aiChatSessionTitle")
        self.chat_title_label.setWordWrap(False)
        top_row.addWidget(self.start_menu_btn, 0)
        top_row.addWidget(self.chat_title_label, 1)
        root.addLayout(top_row)

        self.scroll = QScrollArea(host)
        self.scroll.setObjectName("aiChatScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.viewport().setObjectName("aiChatViewport")
        self.scroll.viewport().setAutoFillBackground(True)
        root.addWidget(self.scroll, 1)

        self.messages_host = QWidget(self.scroll)
        self.messages_host.setObjectName("aiChatMessages")
        self.messages_host.setAutoFillBackground(True)
        self.messages_layout = QVBoxLayout(self.messages_host)
        self.messages_layout.setContentsMargins(4, 4, 4, 4)
        self.messages_layout.setSpacing(8)
        self.messages_layout.addStretch(1)
        self.scroll.setWidget(self.messages_host)
        self._chat_stick_to_bottom = True
        self.scroll.verticalScrollBar().valueChanged.connect(self._update_chat_stick_to_bottom_state)

        self.input = _AIChatInputEdit(host, self._send_prompt)
        self.input.setObjectName("aiChatInput")
        self.input.setPlaceholderText("Ask AI...")
        self.input.setFixedHeight(90)
        root.addWidget(self.input)
        self.attachments_bar = QWidget(host)
        self.attachments_bar.setObjectName("aiChatAttachmentsBar")
        self.attachments_layout = _FlowLayout(self.attachments_bar, h_spacing=6, v_spacing=6)
        self.attachments_layout.setContentsMargins(6, 4, 6, 4)
        self.attachments_bar.setLayout(self.attachments_layout)
        self.attachments_bar.setVisible(False)
        root.addWidget(self.attachments_bar)
        self.pending_insert_label = QLabel("Pending insert offer: none", host)
        self.pending_insert_label.setObjectName("aiPendingInsertLabel")
        self.pending_insert_label.setWordWrap(True)
        root.addWidget(self.pending_insert_label)

        self.quick_actions_bar = QWidget(host)
        self.quick_actions_bar.setObjectName("aiQuickActionsBar")
        self.quick_actions_layout = _FlowLayout(self.quick_actions_bar, h_spacing=6, v_spacing=6)
        self.quick_actions_layout.setContentsMargins(6, 4, 6, 4)
        self.quick_actions_bar.setLayout(self.quick_actions_layout)
        for key, label, tooltip, icon_name in (
            ("summarize", "Summarize", "Quick prompt: summarize selected text or current draft", "ai-explain"),
            ("fix", "Fix", "Quick prompt: fix grammar/style for selected text or draft", "ai-inline-edit"),
            ("refactor", "Refactor", "Quick prompt: refactor selected code or provide a refactor plan", "ai-refactor"),
            ("test", "Test", "Quick prompt: generate focused tests for selected code", "ai-citations"),
        ):
            chip = QPushButton(label, self.quick_actions_bar)
            chip.setObjectName("aiQuickActionChip")
            chip.setProperty("ai_icon_name", icon_name)
            chip.setToolTip(tooltip)
            icon = self._icon(icon_name, size=12)
            if not icon.isNull():
                chip.setIcon(icon)
                chip.setIconSize(QSize(12, 12))
            chip.clicked.connect(lambda _checked=False, action_key=key: self._run_quick_action(action_key))
            self.quick_actions_layout.addWidget(chip)
        self.quick_actions_bar.setVisible(False)
        root.addWidget(self.quick_actions_bar)

        self.context_usage_label = QLabel("Context: 0 attachments | ~0 chars", host)
        self.context_usage_label.setObjectName("aiContextUsageLabel")
        self.context_usage_label.setWordWrap(False)
        root.addWidget(self.context_usage_label)

        row = QHBoxLayout()
        self.quick_plus_btn = QToolButton(host)
        self.quick_plus_btn.setObjectName("aiQuickPlusButton")
        self.quick_plus_btn.setText("+")
        self.quick_plus_btn.setToolTip("Quick AI Actions")
        self.quick_plus_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.quick_plus_menu = QMenu(self.quick_plus_btn)
        self.quick_plus_btn.setMenu(self.quick_plus_menu)
        self._build_quick_plus_menu("idle")
        self.model_btn = QPushButton("Model", host)
        self.clear_btn = QPushButton("Clear", host)
        self.stop_btn = QPushButton("Stop", host)
        self.stop_btn.setEnabled(False)
        self.send_btn = QPushButton("Send", host)
        self._setup_button_icons()
        row.addWidget(self.quick_plus_btn)
        row.addWidget(self.model_btn)
        row.addWidget(self.clear_btn)
        row.addWidget(self.stop_btn)
        row.addStretch(1)
        row.addWidget(self.send_btn)
        root.addLayout(row)

        self.clear_btn.clicked.connect(self.clear_chat)
        self.model_btn.clicked.connect(self._choose_chat_model)
        self.stop_btn.clicked.connect(self._stop_generation)
        self.send_btn.clicked.connect(self._send_prompt)
        self._setup_shortcuts()
        self._copy_code_icon_data_uri = self._copy_code_icon_uri()
        self._apply_styles()
        self._refresh_model_button_label()
        self._refresh_pending_insert_indicator()
        self._load_history()
        self._refresh_attachment_chips()
        self._set_generation_state("idle")
        self.input.textChanged.connect(self._refresh_context_usage_indicator)
        self._refresh_context_usage_indicator()

    def _build_quick_plus_menu(self, state: str) -> None:
        """Internal helper for `_build_quick_plus_menu`."""
        menu = getattr(self, "quick_plus_menu", None)
        if menu is None:
            return
        menu.clear()
        add_files_action = menu.addAction("Add Files")
        icon = self._icon("ai-attach", size=14)
        if not icon.isNull():
            add_files_action.setIcon(icon)
        add_files_action.triggered.connect(self._attach_files_to_chat)
        menu.addSeparator()
        for key, label, icon_name in (
            ("summarize", "Summarize", "ai-explain"),
            ("fix", "Fix", "ai-inline-edit"),
            ("refactor", "Refactor", "ai-refactor"),
            ("test", "Test", "ai-citations"),
        ):
            action = menu.addAction(label)
            action_icon = self._icon(icon_name, size=14)
            if not action_icon.isNull():
                action.setIcon(action_icon)
            action.triggered.connect(lambda _checked=False, action_key=key: self._run_quick_action(action_key))
        menu.addSeparator()
        status_action = menu.addAction(f"Status: {str(state or 'idle').strip().title()}")
        sparkles = self._icon("ai-sparkles", size=14)
        if not sparkles.isNull():
            status_action.setIcon(sparkles)
        status_action.setEnabled(False)

    def _setup_shortcuts(self) -> None:
        """Internal helper for `_setup_shortcuts`."""
        def _dock_shortcut(sequence: str, callback: Callable[[], None]) -> None:
            """Internal helper for `_dock_shortcut`."""
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(callback)

        _dock_shortcut("Ctrl+Enter", self._send_prompt)
        _dock_shortcut("Ctrl+Shift+L", self.clear_chat)
        _dock_shortcut("Ctrl+.", self._stop_generation)
        _dock_shortcut("Alt+M", self._choose_chat_model)

    def _log_ai_chat(self, message: str) -> None:
        """Internal helper for `_log_ai_chat`."""
        window = getattr(self.ai_controller, "window", None)
        if window is None:
            return
        if not bool(getattr(window, "settings", {}).get("ai_verbose_logging", False)):
            return
        logger = getattr(window, "log_event", None)
        if callable(logger):
            cid = self._active_response_correlation_id or self._pending_apply_correlation_id
            if cid:
                logger("Info", f"[AI Chat][cid={cid}] {message}")
            else:
                logger("Info", f"[AI Chat] {message}")

    def _new_response_correlation_id(self) -> str:
        """Internal helper for `_new_response_correlation_id`."""
        self._ai_response_correlation_seq += 1
        return f"chatresp-{self._ai_response_correlation_seq:05d}"

    def _is_effective_dark_mode(self) -> bool:
        """Internal helper for `_is_effective_dark_mode`."""
        icon_color = getattr(self.ai_controller.window, "_icon_color", None)
        if isinstance(icon_color, QColor) and icon_color.isValid():
            # Light text color usually means dark UI chrome.
            return icon_color.lightnessF() >= 0.65
        return bool(getattr(self.ai_controller.window, "settings", {}).get("dark_mode", False))

    def _icon(self, name: str, size: int = 16) -> QIcon:
        """Internal helper for `_icon`."""
        path = resolve_asset_path("icons", f"{name}.svg")
        if path is None:
            return QIcon()
        dark_mode = self._is_effective_dark_mode()
        color = QColor("#ffffff" if dark_mode else "#000000")
        key = (name, color.name(), int(size))
        cached = self._icon_cache.get(key)
        if cached is not None:
            return cached
        try:
            svg_text = path.read_text(encoding="utf-8")
            svg_text = self._force_svg_monochrome(svg_text, color.name())
            renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
            if renderer.isValid():
                pixmap = QPixmap(size, size)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                renderer.render(painter)
                painter.end()
                icon = QIcon(pixmap)
                self._icon_cache[key] = icon
                return icon
        except Exception:
            pass
        icon = QIcon(str(path))
        self._icon_cache[key] = icon
        return icon

    @staticmethod
    def _force_svg_monochrome(svg_text: str, color_hex: str) -> str:
        """Internal helper for `_force_svg_monochrome`."""
        text = re.sub(
            r'\b(stroke|fill)\b\s*=\s*["\'](?!none\b)[^"\']*["\']',
            lambda m: f'{m.group(1)}="{color_hex}"',
            svg_text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r'(?i)\b(stroke|fill)\s*:\s*(?!none\b)[^;}"\']+',
            lambda m: f"{m.group(1)}:{color_hex}",
            text,
        )
        text = text.replace("currentColor", color_hex)
        return text

    def _setup_button_icons(self) -> None:
        """Internal helper for `_setup_button_icons`."""
        clear_icon = self._icon("ai-clear", size=16)
        send_icon = self._icon("ai-send", size=18)
        stop_icon = self._icon("ai-stop", size=18)
        self.clear_btn.setText("Clear")
        self.send_btn.setText("Send")
        self.stop_btn.setText("Stop")
        if not clear_icon.isNull():
            self.clear_btn.setIcon(clear_icon)
            self.clear_btn.setText("")
        if not send_icon.isNull():
            self.send_btn.setIcon(send_icon)
            self.send_btn.setText("")
        if not stop_icon.isNull():
            self.stop_btn.setIcon(stop_icon)
            self.stop_btn.setText("")
        self.clear_btn.setToolTip("Clear chat (Ctrl+Shift+L)")
        self.send_btn.setToolTip("Send (Ctrl+Enter)")
        self.stop_btn.setToolTip("Stop (Ctrl+.)")
        self.model_btn.setToolTip(f"AI model\nCurrent: {self._current_model_name()}\nShortcut: Alt+M")
        for btn in (self.clear_btn, self.send_btn, self.stop_btn):
            btn.setMinimumSize(34, 30)
            if not btn.text():
                btn.setMaximumWidth(38)

    def _copy_code_icon_uri(self) -> str:
        """Internal helper for `_copy_code_icon_uri`."""
        path = resolve_asset_path("icons", "ai-copy.svg")
        if path is None:
            return ""
        try:
            svg_text = path.read_text(encoding="utf-8")
            svg_text = self._force_svg_monochrome(svg_text, "#ffffff")
            encoded = base64.b64encode(svg_text.encode("utf-8")).decode("ascii")
            return f"data:image/svg+xml;base64,{encoded}"
        except Exception:
            return ""

    def _apply_styles(self) -> None:
        """Internal helper for `_apply_styles`."""
        settings = getattr(self.ai_controller.window, "settings", {})
        tokens = build_tokens_from_settings(settings if isinstance(settings, dict) else {})
        body_qss, title_qss = build_ai_chat_qss(tokens)
        self.setStyleSheet(body_qss)
        self._title_bar.label.setStyleSheet(f"color: {tokens.text};")
        self._title_bar.mathjax_label.setStyleSheet(f"color: {tokens.text_muted};")
        self._title_bar.setStyleSheet(title_qss)
        float_icon = self._icon("view-fullscreen", size=12)
        close_icon = self._icon("tab-close", size=12)
        if not float_icon.isNull():
            self._title_bar.float_btn.setIcon(float_icon)
        if not close_icon.isNull():
            self._title_bar.close_btn.setIcon(close_icon)
        self._refresh_mathjax_indicator()

    def refresh_theme(self) -> None:
        """Execute the `refresh_theme` workflow."""
        self._icon_cache.clear()
        self._copy_code_icon_data_uri = self._copy_code_icon_uri()
        self._apply_styles()
        self._setup_button_icons()
        self._refresh_message_action_icons()
        self._refresh_quick_action_icons()

    def _refresh_mathjax_indicator(self) -> None:
        """Internal helper for `_refresh_mathjax_indicator`."""
        label = getattr(self._title_bar, "mathjax_label", None)
        if label is None:
            return
        if QWebEngineView is None:
            label.setText("MathJax: Off (WebEngine missing)")
            label.setToolTip("Install/use Qt WebEngine to enable LaTeX rendering in AI chat bubbles.")
        else:
            label.setText("MathJax: On")
            label.setToolTip("LaTeX rendering is enabled for math-like AI chat messages.")

    def _refresh_message_action_icons(self) -> None:
        """Internal helper for `_refresh_message_action_icons`."""
        for button in self.messages_host.findChildren(QPushButton):
            icon_name = button.property("ai_icon_name")
            if not icon_name:
                continue
            icon = self._icon(str(icon_name), size=14)
            if icon.isNull():
                continue
            button.setIcon(icon)

    def _refresh_quick_action_icons(self) -> None:
        """Internal helper for `_refresh_quick_action_icons`."""
        bar = getattr(self, "quick_actions_bar", None)
        if bar is None:
            return
        for button in bar.findChildren(QPushButton):
            icon_name = button.property("ai_icon_name")
            if not icon_name:
                continue
            icon = self._icon(str(icon_name), size=12)
            if icon.isNull():
                continue
            button.setIcon(icon)
            button.setIconSize(QSize(12, 12))

    def _remove_attachment_by_id(self, attachment_id: str) -> bool:
        """Internal helper for `_remove_attachment_by_id`."""
        session = self._ensure_active_session(create_if_missing=False)
        if session is None:
            return False
        rows = session.get("context_attachments", [])
        if not isinstance(rows, list):
            return False
        before = len(rows)
        rows = [r for r in rows if not (isinstance(r, dict) and str(r.get("id", "")) == str(attachment_id))]
        if len(rows) == before:
            return False
        session["context_attachments"] = self._sanitize_context_attachments(rows)
        self._persist_history(save=True)
        self._refresh_attachment_chips()
        self.ai_controller.window.show_status_message("Removed chat attachment.", 2000)
        return True

    def _refresh_attachment_chips(self) -> None:
        """Internal helper for `_refresh_attachment_chips`."""
        if not hasattr(self, "attachments_layout"):
            return
        while self.attachments_layout.count() > 0:
            item = self.attachments_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        session = self._current_session()
        rows = session.get("context_attachments", []) if isinstance(session, dict) else []
        attachments = rows if isinstance(rows, list) else []
        shown = 0
        attach_icon = self._icon("ai-attach", size=12)
        for row in attachments[:12]:
            if not isinstance(row, dict):
                continue
            att_id = str(row.get("id", "") or "").strip()
            kind = str(row.get("kind", "") or "attachment")
            title = str(row.get("title", "") or kind.replace("_", " ").title())
            source_path = str(row.get("source_path", "") or "").strip()
            display_name = Path(source_path).name if source_path else title
            display_name = display_name or title or "Attachment"
            chip = QWidget(self.attachments_bar)
            chip.setObjectName("aiChatAttachmentChip")
            chip_row = QHBoxLayout(chip)
            chip_row.setContentsMargins(8, 2, 4, 2)
            chip_row.setSpacing(4)
            icon_label = QLabel(chip)
            icon_label.setObjectName("aiChatAttachmentChipIcon")
            if not attach_icon.isNull():
                icon_label.setPixmap(attach_icon.pixmap(12, 12))
            else:
                icon_label.setText("F")
            text_label = QLabel(display_name, chip)
            text_label.setObjectName("aiChatAttachmentChipText")
            text_label.setToolTip(f"{title}\n{source_path}" if source_path else title)
            text_label.setMaximumWidth(220)
            text_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            remove_btn = QPushButton("x", chip)
            remove_btn.setObjectName("aiChatAttachmentChipRemove")
            remove_btn.setToolTip("Remove attachment")
            remove_btn.clicked.connect(lambda _checked=False, aid=att_id: self._remove_attachment_by_id(aid))
            chip_row.addWidget(icon_label, 0)
            chip_row.addWidget(text_label, 0)
            chip_row.addWidget(remove_btn, 0)
            self.attachments_layout.addWidget(chip)
            shown += 1
        self.attachments_bar.setVisible(shown > 0)
        self._refresh_context_usage_indicator()

    def _set_generation_state(self, state: str) -> None:
        """Internal helper for `_set_generation_state`."""
        value = str(state or "").strip().lower()
        normalized = value if value in {"idle", "thinking", "streaming", "error"} else "idle"
        self._build_quick_plus_menu(normalized)

    def _estimate_context_chars(self, prompt: str) -> tuple[int, int, bool]:
        """Internal helper for `_estimate_context_chars`."""
        session = self._current_session()
        policy = self._sanitize_memory_policy(session.get("memory_policy", {})) if isinstance(session, dict) else self._default_memory_policy()
        attachments_count = 0
        attachments_chars = 0
        if isinstance(session, dict):
            rows = session.get("context_attachments", [])
            if isinstance(rows, list):
                for item in rows[-12:]:
                    if not isinstance(item, dict):
                        continue
                    attachments_count += 1
                    attachments_chars += len(str(item.get("content", "") or "")[:4000])
        auto_current_chars = 0
        window = getattr(self.ai_controller, "window", None)
        if bool(policy.get("include_current_file_auto", False)) and window is not None and hasattr(window, "active_tab"):
            tab = window.active_tab()
            if tab is not None:
                auto_current_chars = min(len(str(tab.text_edit.get_text() or "")), 12000)
        policy_chars = 0
        if bool(policy.get("strict_citations_only", False)):
            policy_chars += 96
        if not bool(policy.get("allow_hidden_apply_commands", True)):
            policy_chars += 80
        prompt_chars = len(str(prompt or ""))
        total = prompt_chars + attachments_chars + auto_current_chars + policy_chars
        workspace_auto = bool(policy.get("include_workspace_snippets_auto", False))
        return total, attachments_count, workspace_auto

    def _refresh_context_usage_indicator(self) -> None:
        """Internal helper for `_refresh_context_usage_indicator`."""
        label = getattr(self, "context_usage_label", None)
        if label is None:
            return
        prompt = self.input.toPlainText() if hasattr(self, "input") and self.input is not None else ""
        total, attachments_count, workspace_auto = self._estimate_context_chars(prompt)
        suffix = " + workspace:auto" if workspace_auto else ""
        label.setText(f"Context: {attachments_count} attachments | ~{total} chars{suffix}")

    def _build_quick_action_prompt(self, action_key: str) -> tuple[str, str]:
        """Internal helper for `_build_quick_action_prompt`."""
        key = str(action_key or "").strip().lower()
        window = getattr(self.ai_controller, "window", None)
        tab = window.active_tab() if window is not None and hasattr(window, "active_tab") else None
        selected = str(tab.text_edit.selected_text() or "") if tab is not None else ""
        draft = self.input.toPlainText().strip() if hasattr(self, "input") else ""
        if key == "summarize":
            if selected.strip():
                return f"Summarize the following text:\n\n{selected}", "Quick Action: Summarize selection"
            if draft:
                return f"Summarize the following text:\n\n{draft}", "Quick Action: Summarize draft"
            return "Summarize the current file content with concise key points.", "Quick Action: Summarize current file"
        if key == "fix":
            if selected.strip():
                return (
                    "Fix grammar, spelling, and clarity. Keep original meaning. Return only corrected text.\n\n"
                    f"{selected}"
                ), "Quick Action: Fix selection"
            if draft:
                return (
                    "Fix grammar, spelling, and clarity. Keep original meaning. Return only corrected text.\n\n"
                    f"{draft}"
                ), "Quick Action: Fix draft"
            return "Give a short checklist for improving clarity and grammar in my current text.", "Quick Action: Fix guidance"
        if key == "refactor":
            if selected.strip():
                return (
                    "Refactor this code for readability and maintainability without changing behavior. "
                    "Return code first, then brief notes.\n\n"
                    f"{selected}"
                ), "Quick Action: Refactor selection"
            return "Provide a practical refactor plan for the current file.", "Quick Action: Refactor current file"
        if key == "test":
            if selected.strip():
                return (
                    "Write focused unit tests for this code. Include edge cases and expected behavior.\n\n"
                    f"{selected}"
                ), "Quick Action: Generate tests from selection"
            return "Propose a concise unit test plan for the current file.", "Quick Action: Test plan for current file"
        return "", ""

    def _run_quick_action(self, action_key: str) -> None:
        """Internal helper for `_run_quick_action`."""
        if not self.send_btn.isEnabled():
            return
        prompt, visible = self._build_quick_action_prompt(action_key)
        if not prompt.strip():
            return
        self.send_prompt(prompt=prompt, visible_prompt=visible)

    def focus_prompt(self) -> None:
        """Execute the `focus_prompt` workflow."""
        self.input.setFocus()

    def _current_model_name(self) -> str:
        """Internal helper for `_current_model_name`."""
        window = getattr(self.ai_controller, "window", None)
        settings = getattr(window, "settings", {}) if window is not None else {}
        return str(settings.get("ai_model", "gemini-3-flash-preview") or "gemini-3-flash-preview")

    def _refresh_model_button_label(self) -> None:
        """Internal helper for `_refresh_model_button_label`."""
        model = self._current_model_name()
        short = model if len(model) <= 18 else model[:15] + "..."
        self.model_btn.setText(f"Model: {short}")
        self.model_btn.setToolTip(f"AI model\nCurrent: {model}\nShortcut: Alt+M")

    def _choose_chat_model(self) -> None:
        """Internal helper for `_choose_chat_model`."""
        window = getattr(self.ai_controller, "window", None)
        if window is None:
            return
        current = self._current_model_name()
        presets = [
            "gemini-3-flash-preview",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            current,
            "Custom...",
        ]
        seen: set[str] = set()
        choices: list[str] = []
        for item in presets:
            key = str(item).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            choices.append(key)
        chosen, ok = QInputDialog.getItem(self, "AI Chat Model", "Select model:", choices, max(0, choices.index(current)) if current in choices else 0, False)
        if not ok or not chosen:
            return
        model = str(chosen).strip()
        if model == "Custom...":
            model, ok = QInputDialog.getText(self, "AI Chat Model", "Custom model name:", text=current)
            if not ok:
                return
            model = str(model).strip()
        if not model or model == current:
            return
        window.settings["ai_model"] = model
        if hasattr(window, "save_settings_to_disk"):
            window.save_settings_to_disk()
        if hasattr(window, "show_status_message"):
            window.show_status_message(f"AI model set to {model}", 3000)
        self._refresh_model_button_label()

    @staticmethod
    def _new_chat_id() -> str:
        """Internal helper for `_new_chat_id`."""
        return f"chat-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    @staticmethod
    def _chat_title_from_prompt(prompt: str) -> str:
        """Internal helper for `_chat_title_from_prompt`."""
        text = (prompt or "").strip().replace("\r", " ").replace("\n", " ")
        if not text:
            return "New Chat"
        if len(text) > 48:
            return text[:45].rstrip() + "..."
        return text

    @staticmethod
    def _normalize_chat_title(value: str) -> str:
        """Internal helper for `_normalize_chat_title`."""
        raw = re.sub(r"\s+", " ", str(value or "").strip())
        # Defensive fallback: if a base64 payload reaches title apply, decode it here.
        maybe_b64 = raw.strip().strip("\"'")
        if (
            maybe_b64
            and re.fullmatch(r"[A-Za-z0-9+/=\s]{4,}", maybe_b64)
            and any(ch in maybe_b64 for ch in "+/=")
        ):
            try:
                decoded = base64.b64decode(maybe_b64).decode("utf-8", errors="replace").strip()
                if decoded and all((ch.isprintable() or ch.isspace()) for ch in decoded):
                    raw = decoded
            except Exception:
                pass
        title = raw
        if not title:
            return "New Chat"
        if len(title) > 72:
            title = title[:69].rstrip(" ,.;:-") + "..."
        return title or "New Chat"

    @staticmethod
    def _default_memory_policy() -> dict[str, object]:
        """Internal helper for `_default_memory_policy`."""
        return {
            "include_current_file_auto": False,
            "include_workspace_snippets_auto": False,
            "strict_citations_only": False,
            "allow_hidden_apply_commands": True,
        }

    def _memory_policy_defaults_from_settings(self) -> dict[str, object]:
        """Internal helper for `_memory_policy_defaults_from_settings`."""
        window = getattr(self.ai_controller, "window", None)
        settings = getattr(window, "settings", {}) if window is not None else {}
        base = self._default_memory_policy()
        return {
            "include_current_file_auto": bool(
                settings.get("ai_session_default_include_current_file_auto", base["include_current_file_auto"])
            ),
            "include_workspace_snippets_auto": bool(
                settings.get(
                    "ai_session_default_include_workspace_snippets_auto",
                    base["include_workspace_snippets_auto"],
                )
            ),
            "strict_citations_only": bool(
                settings.get("ai_session_default_strict_citations_only", base["strict_citations_only"])
            ),
            "allow_hidden_apply_commands": bool(
                settings.get(
                    "ai_session_default_allow_hidden_apply_commands",
                    base["allow_hidden_apply_commands"],
                )
            ),
        }

    @classmethod
    def _sanitize_memory_policy(cls, raw: object) -> dict[str, object]:
        """Internal helper for `_sanitize_memory_policy`."""
        base = cls._default_memory_policy()
        if not isinstance(raw, dict):
            return dict(base)
        out = dict(base)
        for key in base:
            out[key] = bool(raw.get(key, base[key]))
        return out

    @staticmethod
    def _sanitize_context_attachments(raw: object) -> list[dict[str, object]]:
        """Internal helper for `_sanitize_context_attachments`."""
        out: list[dict[str, object]] = []
        def _to_int(v: object) -> int:
            """Internal helper for `_to_int`."""
            try:
                return int(v)
            except Exception:
                return 0
        if not isinstance(raw, list):
            return out
        for item in raw[-50:]:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind", "") or "").strip()
            title = str(item.get("title", "") or "").strip()
            content = str(item.get("content", "") or "")
            if kind not in {"current_file", "selection", "workspace_search", "manual_snippet"}:
                continue
            if not title:
                title = kind.replace("_", " ").title()
            out.append(
                {
                    "id": str(item.get("id", "") or f"att-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"),
                    "kind": kind,
                    "title": title,
                    "source_path": str(item.get("source_path", "") or ""),
                    "line_start": _to_int(item.get("line_start", 0)),
                    "line_end": _to_int(item.get("line_end", 0)),
                    "content": content[:20000],
                    "created_at": str(item.get("created_at", "") or datetime.now().isoformat(timespec="seconds")),
                }
            )
        return out

    def _default_chat_session(self, *, title: str = "New Chat") -> dict[str, object]:
        """Internal helper for `_default_chat_session`."""
        now = datetime.now().isoformat(timespec="seconds")
        return {
            "id": self._new_chat_id(),
            "title": str(title or "New Chat"),
            "title_auto": True,
            "title_fallback_attempted": False,
            "pinned": False,
            "archived": False,
            "project": False,
            "created_at": now,
            "updated_at": now,
            "messages": [],
            "context_attachments": [],
            "memory_policy": self._memory_policy_defaults_from_settings(),
        }

    def _session_sort_key(self, session: dict[str, object]) -> tuple[int, str, str]:
        """Internal helper for `_session_sort_key`."""
        pinned = bool(session.get("pinned", False))
        updated = str(session.get("updated_at", "") or "")
        title = str(session.get("title", "") or "New Chat").lower()
        return (0 if pinned else 1, "-" + updated, title)

    def _sanitize_chat_sessions(self, raw: object) -> list[dict[str, object]]:
        """Internal helper for `_sanitize_chat_sessions`."""
        sessions: list[dict[str, object]] = []
        if not isinstance(raw, list):
            return sessions
        for item in raw:
            if not isinstance(item, dict):
                continue
            sid = str(item.get("id", "") or "").strip() or self._new_chat_id()
            title = str(item.get("title", "") or "New Chat").strip() or "New Chat"
            messages_raw = item.get("messages", [])
            messages: list[dict[str, str]] = []
            if isinstance(messages_raw, list):
                for row in messages_raw[-200:]:
                    if not isinstance(row, dict):
                        continue
                    role = str(row.get("role", "")).strip().lower()
                    text = str(row.get("text", ""))
                    if role in {"user", "assistant"}:
                        messages.append({"role": role, "text": text})
            sessions.append(
                {
                    "id": sid,
                    "storage_file": str(item.get("storage_file", "") or "").strip(),
                    "title": title,
                    "title_auto": bool(item.get("title_auto", True)),
                    "title_fallback_attempted": bool(item.get("title_fallback_attempted", False)),
                    "pinned": bool(item.get("pinned", False)),
                    "archived": bool(item.get("archived", False)),
                    "project": bool(item.get("project", False)),
                    "created_at": str(item.get("created_at", "") or datetime.now().isoformat(timespec="seconds")),
                    "updated_at": str(item.get("updated_at", "") or datetime.now().isoformat(timespec="seconds")),
                    "messages": messages,
                    "context_attachments": self._sanitize_context_attachments(item.get("context_attachments", [])),
                    "memory_policy": self._sanitize_memory_policy(item.get("memory_policy", {})),
                }
            )
        return sessions

    def _clear_messages_ui(self) -> None:
        """Internal helper for `_clear_messages_ui`."""
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _current_session(self) -> dict[str, object] | None:
        """Internal helper for `_current_session`."""
        sid = str(self._active_chat_id or "")
        for session in self._chat_sessions:
            if str(session.get("id", "")) == sid:
                return session
        return None

    def _ensure_active_session(self, *, create_if_missing: bool = True) -> dict[str, object] | None:
        """Internal helper for `_ensure_active_session`."""
        session = self._current_session()
        if session is not None:
            return session
        if not create_if_missing:
            return None
        session = self._default_chat_session()
        self._chat_sessions.insert(0, session)
        self._active_chat_id = str(session.get("id", ""))
        self._history = []
        self._persist_history(save=True)
        self._refresh_chat_session_header()
        return session

    def _refresh_chat_session_header(self) -> None:
        """Internal helper for `_refresh_chat_session_header`."""
        session = self._current_session()
        if session is None:
            self.chat_title_label.setText("New Chat")
            return
        title = str(session.get("title", "") or "New Chat")
        badges: list[str] = []
        if bool(session.get("pinned", False)):
            badges.append("Pinned")
        if bool(session.get("archived", False)):
            badges.append("Archived")
        if bool(session.get("project", False)):
            badges.append("Project")
        suffix = f" [{', '.join(badges)}]" if badges else ""
        self.chat_title_label.setText(f"{title}{suffix}")
        self.chat_title_label.setToolTip(title)

    def _set_active_chat(self, session_id: str, *, persist: bool = True) -> None:
        """Internal helper for `_set_active_chat`."""
        target = None
        for session in self._chat_sessions:
            if str(session.get("id", "")) == str(session_id):
                target = session
                break
        if target is None:
            return
        self._active_chat_id = str(target.get("id", ""))
        messages = target.get("messages", [])
        self._history = list(messages if isinstance(messages, list) else [])
        self._pending_prompt_edit_row = None
        self._active_reply_bubble = None
        self._active_reply_index = None
        self._pending_insert_offer = None
        self._pending_set_file_offer = None
        self._pending_patch_offer = None
        self._pending_local_action = None
        self._pending_apply_correlation_id = None
        self._refresh_pending_insert_indicator()
        self._clear_messages_ui()
        for item in self._history:
            if isinstance(item, dict):
                role = str(item.get("role", "")).strip().lower()
                text = str(item.get("text", ""))
                if role in {"user", "assistant"}:
                    self._add_bubble(text, role, persist=False)
        self._refresh_chat_session_header()
        self._refresh_attachment_chips()
        if persist:
            self._persist_history(save=True)

    def _new_chat(self) -> None:
        """Internal helper for `_new_chat`."""
        session = self._default_chat_session()
        self._chat_sessions.insert(0, session)
        self._set_active_chat(str(session.get("id", "")), persist=True)
        self.input.setFocus()

    def _rename_current_chat(self) -> None:
        """Internal helper for `_rename_current_chat`."""
        session = self._ensure_active_session(create_if_missing=False)
        if session is None:
            return
        current = str(session.get("title", "") or "New Chat")
        title, ok = QInputDialog.getText(self, "Rename Chat", "Chat name:", text=current)
        if not ok:
            return
        title = title.strip() or "New Chat"
        session["title"] = title
        session["title_auto"] = False
        session["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._refresh_chat_session_header()
        self._persist_history(save=True)

    def _toggle_current_chat_flag(self, key: str) -> None:
        """Internal helper for `_toggle_current_chat_flag`."""
        session = self._ensure_active_session(create_if_missing=False)
        if session is None:
            return
        session[key] = not bool(session.get(key, False))
        session["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._refresh_chat_session_header()
        self._persist_history(save=True)

    def _delete_current_chat(self) -> None:
        """Internal helper for `_delete_current_chat`."""
        session = self._current_session()
        if session is None:
            return
        title = str(session.get("title", "") or "New Chat")
        ans = QMessageBox.question(
            self,
            "Delete Chat",
            f'Delete chat "{title}"?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return
        current_id = str(session.get("id", ""))
        self._chat_sessions = [s for s in self._chat_sessions if str(s.get("id", "")) != current_id]
        if self._chat_sessions:
            self._set_active_chat(str(self._chat_sessions[0].get("id", "")), persist=True)
        else:
            self._active_chat_id = ""
            self._history = []
            self._clear_messages_ui()
            self._refresh_chat_session_header()
            self._persist_history(save=True)

    def _session_by_id(self, session_id: str) -> dict[str, object] | None:
        """Internal helper for `_session_by_id`."""
        wanted = str(session_id or "")
        for session in self._chat_sessions:
            if str(session.get("id", "")) == wanted:
                return session
        return None

    def _rename_chat_by_id(self, session_id: str) -> None:
        """Internal helper for `_rename_chat_by_id`."""
        session = self._session_by_id(session_id)
        if session is None:
            return
        current = str(session.get("title", "") or "New Chat")
        title, ok = QInputDialog.getText(self, "Rename Chat", "Chat name:", text=current)
        if not ok:
            return
        title = title.strip() or "New Chat"
        session["title"] = title
        session["title_auto"] = False
        session["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._refresh_chat_session_header()
        self._persist_history(save=True)

    def _toggle_chat_flag_by_id(self, session_id: str, key: str) -> None:
        """Internal helper for `_toggle_chat_flag_by_id`."""
        session = self._session_by_id(session_id)
        if session is None:
            return
        session[key] = not bool(session.get(key, False))
        session["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._refresh_chat_session_header()
        self._persist_history(save=True)

    def _delete_chat_by_id(self, session_id: str) -> None:
        """Internal helper for `_delete_chat_by_id`."""
        session = self._session_by_id(session_id)
        if session is None:
            return
        title = str(session.get("title", "") or "New Chat")
        ans = QMessageBox.question(
            self,
            "Delete Chat",
            f'Delete chat "{title}"?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return
        current_id = str(session.get("id", ""))
        self._chat_sessions = [s for s in self._chat_sessions if str(s.get("id", "")) != current_id]
        if self._chat_sessions:
            if current_id == self._active_chat_id:
                self._set_active_chat(str(self._chat_sessions[0].get("id", "")), persist=True)
            else:
                self._persist_history(save=True)
        else:
            self._active_chat_id = ""
            self._history = []
            self._clear_messages_ui()
            self._refresh_chat_session_header()
            self._persist_history(save=True)

    def _chat_transcript_text(self, session: dict[str, object]) -> str:
        """Internal helper for `_chat_transcript_text`."""
        title = str(session.get("title", "") or "New Chat")
        lines = [f"# {title}", ""]
        for item in session.get("messages", []) if isinstance(session.get("messages", []), list) else []:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "")).strip().lower()
            text = str(item.get("text", "")).strip()
            if not role or not text:
                continue
            lines.append(f"## {role.title()}")
            lines.append(text)
            lines.append("")
        return "\n".join(lines).strip()

    def _add_current_chat_to_project(self) -> None:
        """Internal helper for `_add_current_chat_to_project`."""
        session = self._ensure_active_session(create_if_missing=False)
        if session is None:
            return
        session["project"] = True
        session["updated_at"] = datetime.now().isoformat(timespec="seconds")
        window = getattr(self.ai_controller, "window", None)
        workspace_root = str(getattr(window, "settings", {}).get("workspace_root", "") or "").strip() if window is not None else ""
        if workspace_root:
            try:
                folder = Path(workspace_root) / ".pypad_ai_chats"
                folder.mkdir(parents=True, exist_ok=True)
                safe_name = re.sub(r"[^A-Za-z0-9._ -]+", "_", str(session.get("title", "New Chat"))).strip() or "chat"
                target = folder / f"{safe_name}.md"
                if target.exists():
                    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    target = folder / f"{safe_name}_{stamp}.md"
                target.write_text(self._chat_transcript_text(session), encoding="utf-8")
                QMessageBox.information(self, "Add Chat to Project", f"Saved chat transcript to:\n{target}")
            except Exception as exc:
                QMessageBox.warning(self, "Add Chat to Project", f"Could not save transcript:\n{exc}")
        self._refresh_chat_session_header()
        self._persist_history(save=True)

    def _extract_current_chat_tasks_to_project(self) -> None:
        """Internal helper for `_extract_current_chat_tasks_to_project`."""
        session = self._ensure_active_session(create_if_missing=False)
        if session is None:
            return
        window = getattr(self.ai_controller, "window", None)
        workspace_root = str(getattr(window, "settings", {}).get("workspace_root", "") or "").strip() if window is not None else ""
        if not workspace_root:
            QMessageBox.information(self, "Extract Tasks", "Set a workspace folder first.")
            return
        title = str(session.get("title", "") or "Chat Tasks")
        messages = session.get("messages", [])
        assistant_text = ""
        if isinstance(messages, list):
            for item in reversed(messages):
                if isinstance(item, dict) and str(item.get("role", "")).lower() == "assistant":
                    assistant_text = str(item.get("text", "") or "").strip()
                    if assistant_text:
                        break
        if not assistant_text:
            assistant_text = self._chat_transcript_text(session)
        task_lines: list[str] = []
        for line in assistant_text.splitlines():
            s = line.strip()
            if not s:
                continue
            if re.match(r"^(?:[-*]\s+|\d+\.\s+|\[\s?\]\s+)", s):
                s = re.sub(r"^(?:[-*]\s+|\d+\.\s+|\[\s?\]\s+)", "", s).strip()
                if s:
                    task_lines.append(s)
        if not task_lines:
            # Fallback heuristic: sentences ending in action verbs are too fuzzy; keep simple.
            task_lines = [f"Review AI chat and extract tasks manually: {title}"]
        folder = Path(workspace_root) / ".pypad_ai_tasks"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = folder / f"tasks_{stamp}.md"
        body = [
            f"# Tasks from AI Chat: {title}",
            "",
            f"- Source chat id: {session.get('id', '')}",
            f"- Exported: {datetime.now().isoformat(timespec='seconds')}",
            "",
            "## Tasks",
            "",
        ]
        body.extend(f"- [ ] {row}" for row in task_lines[:200])
        body.extend(["", "## Notes", "", "Generated from the current AI chat session."])
        target.write_text("\n".join(body).strip() + "\n", encoding="utf-8")
        if window is not None:
            self._open_file_path_and_line(str(target), line=1)
            window.show_status_message(f"Saved AI tasks: {target.name}", 3500)

    def _search_chat_sessions(self) -> None:
        """Internal helper for `_search_chat_sessions`."""
        if not self._chat_sessions:
            QMessageBox.information(self, "Search Chats", "No saved chats yet.")
            return
        query, ok = QInputDialog.getText(self, "Search Chats", "Find chat by title or content:")
        if not ok:
            return
        query = query.strip().lower()
        if not query:
            return
        matches: list[dict[str, object]] = []
        for session in self._chat_sessions:
            title = str(session.get("title", "") or "New Chat")
            haystack_parts = [title.lower()]
            messages = session.get("messages", [])
            if isinstance(messages, list):
                for item in messages[-50:]:
                    if isinstance(item, dict):
                        haystack_parts.append(str(item.get("text", "")).lower())
            haystack = "\n".join(haystack_parts)
            if query in haystack:
                matches.append(session)
        if not matches:
            QMessageBox.information(self, "Search Chats", "No chats matched your search.")
            return
        if len(matches) == 1:
            self._set_active_chat(str(matches[0].get("id", "")), persist=True)
            return
        labels: list[str] = []
        for session in matches[:200]:
            title = str(session.get("title", "") or "New Chat")
            tags: list[str] = []
            if bool(session.get("pinned", False)):
                tags.append("Pinned")
            if bool(session.get("archived", False)):
                tags.append("Archived")
            if bool(session.get("project", False)):
                tags.append("Project")
            suffix = f" [{' | '.join(tags)}]" if tags else ""
            labels.append(f"{title}{suffix}")
        choice, ok = QInputDialog.getItem(self, "Search Chats", "Matches:", labels, 0, False)
        if not ok or not choice:
            return
        idx = labels.index(choice)
        self._set_active_chat(str(matches[idx].get("id", "")), persist=True)

    def _start_menu_matches_filter(self, session: dict[str, object], query: str) -> bool:
        """Internal helper for `_start_menu_matches_filter`."""
        q = str(query or "").strip().lower()
        if not q:
            return True
        title = str(session.get("title", "") or "New Chat").lower()
        if q in title:
            return True
        messages = session.get("messages", [])
        if isinstance(messages, list):
            for item in messages[-50:]:
                if isinstance(item, dict) and q in str(item.get("text", "")).lower():
                    return True
        return False

    def _on_start_menu_search_text_changed(self, text: str) -> None:
        """Internal helper for `_on_start_menu_search_text_changed`."""
        self._start_menu_filter_text = str(text or "")
        if self._start_menu_rebuild_active:
            return
        self._rebuild_start_menu()
        edit = getattr(self, "_start_menu_search_edit", None)
        if isinstance(edit, QLineEdit):
            edit.setFocus()
            edit.setCursorPosition(len(edit.text()))

    def _add_start_menu_search_widget(self, menu: QMenu) -> None:
        """Internal helper for `_add_start_menu_search_widget`."""
        action = QWidgetAction(menu)
        host = QWidget(menu)
        lay = QHBoxLayout(host)
        lay.setContentsMargins(8, 6, 8, 6)
        edit = QLineEdit(host)
        edit.setPlaceholderText("Filter chats...")
        edit.setClearButtonEnabled(True)
        edit.setText(self._start_menu_filter_text)
        edit.textChanged.connect(self._on_start_menu_search_text_changed)
        lay.addWidget(edit)
        action.setDefaultWidget(host)
        menu.addAction(action)
        self._start_menu_search_edit = edit

    def _rebuild_start_menu(self) -> None:
        """Internal helper for `_rebuild_start_menu`."""
        menu = self.start_menu
        self._start_menu_rebuild_active = True
        menu.clear()
        current = self._current_session()
        self._add_start_menu_search_widget(menu)
        menu.addSeparator()

        new_action = menu.addAction("New Chat")
        new_action.triggered.connect(self._new_chat)
        open_saved_action = menu.addAction("Open Saved Chats...")
        open_saved_action.triggered.connect(self._open_saved_chats_dialog)
        if current is not None:
            menu.addSeparator()
            rename_action = menu.addAction("Rename Current Chat...")
            rename_action.triggered.connect(self._rename_current_chat)
            pin_text = "Unpin Current Chat" if bool(current.get("pinned", False)) else "Pin Current Chat"
            pin_action = menu.addAction(pin_text)
            pin_action.triggered.connect(lambda: self._toggle_current_chat_flag("pinned"))
            arch_text = "Unarchive Current Chat" if bool(current.get("archived", False)) else "Archive Current Chat"
            arch_action = menu.addAction(arch_text)
            arch_action.triggered.connect(lambda: self._toggle_current_chat_flag("archived"))
            project_text = "Add Current Chat to Project" if not bool(current.get("project", False)) else "Mark Current Chat in Project"
            project_action = menu.addAction(project_text)
            project_action.triggered.connect(self._add_current_chat_to_project)
            tasks_action = menu.addAction("Extract Tasks to Project")
            tasks_action.triggered.connect(self._extract_current_chat_tasks_to_project)
            attach_menu = menu.addMenu("Attachments")
            attach_current = attach_menu.addAction("Attach Current File")
            attach_current.triggered.connect(self._attach_current_file_to_chat)
            attach_sel = attach_menu.addAction("Attach Selection")
            attach_sel.triggered.connect(self._attach_selection_to_chat)
            attach_search = attach_menu.addAction("Attach Workspace Search Results")
            attach_search.triggered.connect(self._attach_workspace_search_results_to_chat)
            add_manual = attach_menu.addAction("Add Manual Snippet...")
            add_manual.triggered.connect(self._add_manual_snippet_to_chat)
            manage_attach = attach_menu.addAction("Manage Attachments...")
            manage_attach.triggered.connect(self._manage_chat_attachments)
            mem_menu = menu.addMenu("Memory & Safety")
            policy = self._sanitize_memory_policy(current.get("memory_policy", {}))
            for key, label in [
                ("include_current_file_auto", "Auto include current file"),
                ("include_workspace_snippets_auto", "Auto include workspace snippets"),
                ("strict_citations_only", "Strict citations only"),
                ("allow_hidden_apply_commands", "Allow hidden apply commands"),
            ]:
                act = mem_menu.addAction(label)
                act.setCheckable(True)
                act.setChecked(bool(policy.get(key, False)))
                act.triggered.connect(lambda _checked=False, k=key: self._toggle_memory_policy(k))
            delete_action = menu.addAction("Delete Current Chat")
            delete_action.triggered.connect(self._delete_current_chat)

        visible_sessions = [
            s for s in self._chat_sessions
            if (not bool(s.get("archived", False))) and self._start_menu_matches_filter(s, self._start_menu_filter_text)
        ]
        archived_sessions = [
            s for s in self._chat_sessions
            if bool(s.get("archived", False)) and self._start_menu_matches_filter(s, self._start_menu_filter_text)
        ]

        def _add_session_entries(parent_menu: QMenu, sessions: list[dict[str, object]]) -> None:
            """Internal helper for `_add_session_entries`."""
            for session in sorted(sessions, key=self._session_sort_key):
                sid = str(session.get("id", ""))
                title = str(session.get("title", "") or "New Chat")
                prefix = "📌 " if bool(session.get("pinned", False)) else ""
                project_prefix = "📁 " if bool(session.get("project", False)) else ""
                label = f"{prefix}{project_prefix}{title}"
                action = parent_menu.addAction(label)
                action.setCheckable(True)
                action.setChecked(sid == self._active_chat_id)
                action.triggered.connect(lambda _checked=False, chat_id=sid: self._set_active_chat(chat_id, persist=True))

        if visible_sessions:
            menu.addSeparator()
            chats_menu = menu.addMenu("Saved Chats")
            _add_session_entries(chats_menu, visible_sessions)
        if archived_sessions:
            archived_menu = menu.addMenu("Archived Chats")
            _add_session_entries(archived_menu, archived_sessions)
        elif self._start_menu_filter_text.strip():
            menu.addSeparator()
            empty = menu.addAction("No chats match filter")
            empty.setEnabled(False)
        self._start_menu_rebuild_active = False

    def _chat_description(self, session: dict[str, object]) -> str:
        """Internal helper for `_chat_description`."""
        messages = session.get("messages", [])
        preview = ""
        if isinstance(messages, list):
            for row in reversed(messages):
                if isinstance(row, dict):
                    text = str(row.get("text", "")).strip()
                    if text:
                        preview = re.sub(r"\s+", " ", text)
                        break
        if len(preview) > 120:
            preview = preview[:117].rstrip() + "..."
        tags: list[str] = []
        if bool(session.get("pinned", False)):
            tags.append("Pinned")
        if bool(session.get("archived", False)):
            tags.append("Archived")
        if bool(session.get("project", False)):
            tags.append("Project")
        updated = str(session.get("updated_at", "") or "")
        meta = " | ".join(tags + ([updated] if updated else []))
        if preview and meta:
            return f"{preview}\n{meta}"
        if preview:
            return preview
        return meta or "No messages yet"

    def _open_saved_chats_dialog(self) -> None:
        """Internal helper for `_open_saved_chats_dialog`."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Saved Chats")
        dlg.resize(760, 560)
        layout = QVBoxLayout(dlg)
        search = QLineEdit(dlg)
        search.setPlaceholderText("Filter chats...")
        layout.addWidget(search)
        listing = QListWidget(dlg)
        listing.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(listing, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=dlg)
        layout.addWidget(buttons)
        buttons.rejected.connect(dlg.reject)

        def rebuild() -> None:
            """Execute the `rebuild` workflow."""
            listing.clear()
            query = str(search.text() or "").strip().lower()
            ordered = sorted(self._chat_sessions, key=self._session_sort_key)
            for session in ordered:
                if query and not self._start_menu_matches_filter(session, query):
                    continue
                sid = str(session.get("id", ""))
                title = str(session.get("title", "") or "New Chat")
                item = QListWidgetItem(listing)
                row = QWidget(listing)
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(10, 8, 10, 8)
                row_layout.setSpacing(8)
                text_host = QWidget(row)
                text_layout = QVBoxLayout(text_host)
                text_layout.setContentsMargins(0, 0, 0, 0)
                text_layout.setSpacing(2)
                title_label = QLabel(title, text_host)
                desc_label = QLabel(self._chat_description(session), text_host)
                desc_label.setWordWrap(True)
                text_layout.addWidget(title_label)
                text_layout.addWidget(desc_label)
                row_layout.addWidget(text_host, 1)
                menu_btn = QToolButton(row)
                menu_btn.setText("≡")
                menu_btn.setToolTip("Chat actions")
                menu_btn.setPopupMode(QToolButton.InstantPopup)
                actions = QMenu(menu_btn)
                open_action = actions.addAction("Open")
                open_action.triggered.connect(lambda _checked=False, chat_id=sid: self._set_active_chat(chat_id, persist=True))
                rename_action = actions.addAction("Rename")
                rename_action.triggered.connect(lambda _checked=False, chat_id=sid: (self._rename_chat_by_id(chat_id), rebuild()))
                pin_text = "Unpin" if bool(session.get("pinned", False)) else "Pin"
                pin_action = actions.addAction(pin_text)
                pin_action.triggered.connect(
                    lambda _checked=False, chat_id=sid: (self._toggle_chat_flag_by_id(chat_id, "pinned"), rebuild())
                )
                archive_text = "Unarchive" if bool(session.get("archived", False)) else "Archive"
                archive_action = actions.addAction(archive_text)
                archive_action.triggered.connect(
                    lambda _checked=False, chat_id=sid: (self._toggle_chat_flag_by_id(chat_id, "archived"), rebuild())
                )
                actions.addSeparator()
                delete_action = actions.addAction("Delete")
                delete_action.triggered.connect(lambda _checked=False, chat_id=sid: (self._delete_chat_by_id(chat_id), rebuild()))
                menu_btn.setMenu(actions)
                row_layout.addWidget(menu_btn, 0)
                item.setData(Qt.UserRole, sid)
                item.setSizeHint(row.sizeHint())
                listing.addItem(item)
                listing.setItemWidget(item, row)

        def open_selected(item: QListWidgetItem) -> None:
            """Open the UI or resource handled by `open_selected`."""
            sid = str(item.data(Qt.UserRole) or "")
            if not sid:
                return
            self._set_active_chat(sid, persist=True)
            dlg.accept()

        listing.itemDoubleClicked.connect(open_selected)
        search.textChanged.connect(lambda _t: rebuild())
        rebuild()
        dlg.exec()

    def clear_chat(self) -> None:
        """Execute the `clear_chat` workflow."""
        _LOGGER.debug("AI chat clear_chat active_chat_id=%s history_items=%d", self._active_chat_id, len(self._history))
        self._set_generation_state("idle")
        self._pending_prompt_edit_row = None
        self._active_reply_bubble = None
        self._active_reply_index = None
        self._pending_insert_offer = None
        self._pending_set_file_offer = None
        self._pending_patch_offer = None
        self._pending_local_action = None
        self._refresh_pending_insert_indicator()
        self._clear_messages_ui()
        self._history = []
        session = self._current_session()
        if session is not None:
            session["messages"] = []
            session["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._persist_history(save=True)
        self._refresh_attachment_chips()

    def _send_prompt(self) -> None:
        """Internal helper for `_send_prompt`."""
        prompt = self.input.toPlainText().strip()
        if not prompt:
            return
        if self._try_send_edited_prompt_retry():
            return
        _LOGGER.debug("AI chat _send_prompt start chars=%d active_chat_id=%s", len(prompt), self._active_chat_id)
        if self._try_handle_insert_offer_response(prompt):
            _LOGGER.debug("AI chat _send_prompt consumed local offer response")
            self.input.clear()
            return
        if not self._has_internet_connection():
            _LOGGER.debug("AI chat _send_prompt blocked offline")
            self._add_bubble("You're offline! Check your connection and try again.", "assistant", persist=True)
            self._scroll_to_bottom()
            return
        self._ensure_active_session(create_if_missing=True)
        self._maybe_name_current_chat_from_first_prompt(prompt)
        context_prefix = self._build_session_context_prefix(prompt)
        effective_prompt = ("\n\n".join([p for p in [context_prefix, prompt] if str(p).strip()])).strip()
        self.input.clear()
        self._external_on_done = None
        self._add_bubble(prompt, "user", persist=True)
        self._active_reply_bubble = self._add_bubble("", "assistant")
        self._active_reply_index = len(self._history)
        self._history.append({"role": "assistant", "text": ""})
        self._scroll_to_bottom(force=True)
        self._received_stream_content = False
        self._start_typing_animation()
        self._persist_history(save=False)
        self.send_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._set_generation_state("thinking")
        cid = self._new_response_correlation_id()
        self._active_response_correlation_id = cid
        _LOGGER.debug("AI chat response cycle start cid=%s source=_send_prompt", cid)
        self.ai_controller.ask_ai_chat(
            effective_prompt,
            on_chunk=self._on_stream_chunk,
            on_done=self._on_stream_done,
            on_error=self._on_stream_error,
            on_cancel=self._on_stream_cancel,
            debug_correlation_id=cid,
        )
        _LOGGER.debug("AI chat _send_prompt dispatched effective_chars=%d", len(effective_prompt))

    def send_prompt(self, *, prompt: str, visible_prompt: str | None = None, on_done=None) -> None:
        """Execute the `send_prompt` workflow."""
        prompt = (prompt or "").strip()
        if not prompt:
            return
        _LOGGER.debug(
            "AI chat send_prompt start chars=%d visible_chars=%s on_done=%s active_chat_id=%s",
            len(prompt),
            (len(visible_prompt) if isinstance(visible_prompt, str) else None),
            bool(on_done),
            self._active_chat_id,
        )
        if self._try_handle_insert_offer_response(prompt):
            _LOGGER.debug("AI chat send_prompt consumed local offer response")
            self.input.clear()
            return
        if not self._has_internet_connection():
            _LOGGER.debug("AI chat send_prompt blocked offline")
            self._add_bubble("You're offline! Check your connection and try again.", "assistant", persist=True)
            self._scroll_to_bottom()
            return
        self._ensure_active_session(create_if_missing=True)
        self._maybe_name_current_chat_from_first_prompt(visible_prompt if visible_prompt is not None else prompt)
        context_prefix = self._build_session_context_prefix(prompt)
        effective_prompt = ("\n\n".join([p for p in [context_prefix, prompt] if str(p).strip()])).strip()
        if visible_prompt is None:
            visible_prompt = prompt
        self.input.clear()
        self._external_on_done = on_done
        if visible_prompt.strip():
            self._add_bubble(visible_prompt, "user", persist=True)
        self._active_reply_bubble = self._add_bubble("", "assistant")
        self._active_reply_index = len(self._history)
        self._history.append({"role": "assistant", "text": ""})
        self._scroll_to_bottom(force=True)
        self._received_stream_content = False
        self._start_typing_animation()
        self._persist_history(save=False)
        self.send_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._set_generation_state("thinking")
        cid = self._new_response_correlation_id()
        self._active_response_correlation_id = cid
        _LOGGER.debug("AI chat response cycle start cid=%s source=send_prompt external_on_done=%s", cid, bool(on_done))
        self.ai_controller.ask_ai_chat(
            effective_prompt,
            on_chunk=self._on_stream_chunk,
            on_done=self._on_stream_done,
            on_error=self._on_stream_error,
            on_cancel=self._on_stream_cancel,
            debug_correlation_id=cid,
        )
        _LOGGER.debug("AI chat send_prompt dispatched effective_chars=%d", len(effective_prompt))

    def _maybe_name_current_chat_from_first_prompt(self, prompt: str) -> None:
        # Title is now owned by the AI hidden title-command flow.
        # Keep the method as a no-op to avoid changing multiple send paths.
        """Internal helper for `_maybe_name_current_chat_from_first_prompt`."""
        return

    def _apply_ai_chat_title_command(self, title: str) -> None:
        """Internal helper for `_apply_ai_chat_title_command`."""
        session = self._current_session()
        if session is None:
            return
        suggested = self._normalize_chat_title(title)
        if not suggested:
            return
        session["title"] = suggested
        session["title_auto"] = True
        session["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._refresh_chat_session_header()

    def _request_ai_chat_title_fallback(self) -> None:
        """Internal helper for `_request_ai_chat_title_fallback`."""
        session = self._current_session()
        if session is None:
            return
        if not bool(session.get("title_auto", True)):
            return
        if bool(session.get("title_fallback_attempted", False)):
            return
        messages = session.get("messages", [])
        if not isinstance(messages, list):
            return
        assistant_count = sum(
            1
            for m in messages
            if isinstance(m, dict) and str(m.get("role", "")).strip().lower() == "assistant"
        )
        if assistant_count != 1:
            return

        session["title_fallback_attempted"] = True
        self._persist_history(save=False)
        target_chat_id = str(session.get("id", ""))

        transcript_lines: list[str] = []
        for item in messages[-8:]:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "")).strip().lower()
            text = str(item.get("text", "")).strip()
            if role not in {"user", "assistant"} or not text:
                continue
            transcript_lines.append(f"{role.upper()}:\n{text}")
        transcript = "\n\n".join(transcript_lines).strip()
        if not transcript:
            return

        prompt = (
            "Generate a short chat title (2-8 words) for this conversation.\n"
            "Return ONLY the hidden title command block and no other text.\n"
            "Format exactly:\n"
            "[PYPAD_CMD_SET_CHAT_TITLE_BEGIN]\n"
            "base64:<UTF-8 title encoded in base64>\n"
            "[PYPAD_CMD_SET_CHAT_TITLE_END]\n\n"
            "Conversation:\n"
            f"{transcript}"
        )

        parts: list[str] = []

        def _on_chunk(piece: str) -> None:
            """Internal helper for `_on_chunk`."""
            if piece:
                parts.append(piece)

        def _on_done(text: str) -> None:
            """Internal helper for `_on_done`."""
            payload = text or "".join(parts)
            _clean, _insert, _set_file, set_title, _patch, _action = self._extract_hidden_commands(payload)
            if not set_title:
                return
            if str(self._active_chat_id or "") != target_chat_id:
                return
            active = self._current_session()
            if active is None or str(active.get("id", "")) != target_chat_id:
                return
            if not bool(active.get("title_auto", True)):
                return
            self._apply_ai_chat_title_command(set_title)
            self._persist_history(save=True)

    def _add_context_attachment(self, attachment: dict[str, object]) -> None:
        """Internal helper for `_add_context_attachment`."""
        session = self._ensure_active_session(create_if_missing=True)
        if session is None:
            return
        rows = session.get("context_attachments", [])
        if not isinstance(rows, list):
            rows = []
            session["context_attachments"] = rows
        rows.append(dict(attachment))
        session["context_attachments"] = self._sanitize_context_attachments(rows)
        session["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._persist_history(save=True)
        self._refresh_attachment_chips()

    def _attach_current_file_to_chat(self) -> None:
        """Internal helper for `_attach_current_file_to_chat`."""
        window = getattr(self.ai_controller, "window", None)
        tab = window.active_tab() if window is not None and hasattr(window, "active_tab") else None
        if tab is None:
            QMessageBox.information(self, "Attach to Chat", "Open a tab first.")
            return
        text = str(tab.text_edit.get_text() or "")
        _LOGGER.debug("AI chat attach current_file path=%s chars=%d", str(getattr(tab, "current_file", "") or ""), len(text))
        self._add_context_attachment(
            {
                "id": f"att-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                "kind": "current_file",
                "title": f"File: {Path(str(getattr(tab, 'current_file', '') or 'Untitled')).name}",
                "source_path": str(getattr(tab, "current_file", "") or ""),
                "content": text[:20000],
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        self.ai_controller.window.show_status_message("Attached current file to chat.", 2500)

    @staticmethod
    def _read_attachment_file_text(path: Path) -> str:
        """Internal helper for `_read_attachment_file_text`."""
        try:
            raw = path.read_bytes()
        except Exception:
            return ""
        for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
            try:
                return raw.decode(encoding)
            except Exception:
                continue
        return raw.decode("utf-8", errors="replace")

    def _attach_files_to_chat(self) -> None:
        """Internal helper for `_attach_files_to_chat`."""
        window = getattr(self.ai_controller, "window", None)
        start_dir = ""
        if window is not None and hasattr(window, "active_tab"):
            tab = window.active_tab()
            current_file = str(getattr(tab, "current_file", "") or "") if tab is not None else ""
            if current_file:
                start_dir = str(Path(current_file).parent)
        files, _filter = QFileDialog.getOpenFileNames(
            self,
            "Add Files to Chat",
            start_dir,
            "All Files (*.*)",
        )
        if not files:
            return
        attached = 0
        skipped = 0
        for file_path in files[:12]:
            path = Path(str(file_path or "")).expanduser()
            if not path.exists() or not path.is_file():
                skipped += 1
                continue
            text = self._read_attachment_file_text(path)
            if not text.strip():
                skipped += 1
                continue
            self._add_context_attachment(
                {
                    "id": f"att-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                    "kind": "file",
                    "title": f"File: {path.name}",
                    "source_path": str(path),
                    "content": text[:20000],
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
            attached += 1
        if window is not None and hasattr(window, "show_status_message"):
            if attached > 0:
                if skipped > 0:
                    window.show_status_message(f"Added {attached} file(s), skipped {skipped}.", 3000)
                else:
                    window.show_status_message(f"Added {attached} file(s) to chat.", 3000)
            else:
                window.show_status_message("No readable text files were added.", 3000)

    def _attach_selection_to_chat(self) -> None:
        """Internal helper for `_attach_selection_to_chat`."""
        window = getattr(self.ai_controller, "window", None)
        tab = window.active_tab() if window is not None and hasattr(window, "active_tab") else None
        if tab is None:
            QMessageBox.information(self, "Attach to Chat", "Open a tab first.")
            return
        selection = str(tab.text_edit.selected_text() or "")
        if not selection.strip():
            QMessageBox.information(self, "Attach to Chat", "Select text first.")
            return
        _LOGGER.debug("AI chat attach selection path=%s chars=%d", str(getattr(tab, "current_file", "") or ""), len(selection))
        self._add_context_attachment(
            {
                "id": f"att-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                "kind": "selection",
                "title": "Selection",
                "source_path": str(getattr(tab, "current_file", "") or ""),
                "content": selection[:20000],
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        self.ai_controller.window.show_status_message("Attached selection to chat.", 2500)

    def _attach_workspace_search_results_to_chat(self) -> None:
        """Internal helper for `_attach_workspace_search_results_to_chat`."""
        window = getattr(self.ai_controller, "window", None)
        if window is None:
            return
        workspace_root = str(getattr(window, "settings", {}).get("workspace_root", "") or "").strip()
        if not workspace_root:
            QMessageBox.information(self, "Attach Search Results", "Set a workspace folder first.")
            return
        query, ok = QInputDialog.getText(self, "Attach Workspace Search Results", "Search query:")
        if not ok or not query.strip():
            return
        _LOGGER.debug("AI chat attach workspace search query=%r root=%s", query.strip(), workspace_root)
        files = collect_workspace_files(workspace_root, max_files=1000)
        hits = search_files_for_query(files, query.strip(), max_results=50)
        _LOGGER.debug("AI chat workspace search files=%d hits=%d query=%r", len(files), len(hits), query.strip())
        if not hits:
            QMessageBox.information(self, "Attach Search Results", "No matches found.")
            return
        lines = []
        for hit in hits[:50]:
            lines.append(f"{hit.path}:{hit.line_no}: {hit.line_text}")
        self._add_context_attachment(
            {
                "id": f"att-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                "kind": "workspace_search",
                "title": f"Workspace search: {query.strip()}",
                "source_path": workspace_root,
                "content": "\n".join(lines)[:20000],
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        window.show_status_message("Attached workspace search results to chat.", 2500)

    def _add_manual_snippet_to_chat(self) -> None:
        """Internal helper for `_add_manual_snippet_to_chat`."""
        session = self._ensure_active_session(create_if_missing=True)
        if session is None:
            return
        title, ok = QInputDialog.getText(self, "Add Chat Attachment", "Attachment title:")
        if not ok:
            return
        title = title.strip() or "Manual Snippet"
        body, ok = QInputDialog.getMultiLineText(self, "Add Chat Attachment", "Attachment content:")
        if not ok or not body.strip():
            return
        self._add_context_attachment(
            {
                "id": f"att-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                "kind": "manual_snippet",
                "title": title,
                "source_path": "",
                "content": body[:20000],
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        self.ai_controller.window.show_status_message("Added manual chat attachment.", 2500)

    def _manage_chat_attachments(self) -> None:
        """Internal helper for `_manage_chat_attachments`."""
        session = self._ensure_active_session(create_if_missing=False)
        if session is None:
            return
        rows = session.get("context_attachments", [])
        if not isinstance(rows, list) or not rows:
            rows = []
        dlg = QDialog(self)
        dlg.setWindowTitle("Chat Attachments")
        dlg.resize(840, 520)
        root = QVBoxLayout(dlg)
        root.addWidget(QLabel("Manage saved context attachments for this chat session.", dlg))
        split = QSplitter(Qt.Orientation.Horizontal, dlg)
        root.addWidget(split, 1)
        list_widget = QListWidget(split)
        preview = QTextEdit(split)
        preview.setReadOnly(True)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)

        def _refresh_list() -> None:
            """Internal helper for `_refresh_list`."""
            list_widget.clear()
            current_rows = session.get("context_attachments", [])
            if not isinstance(current_rows, list):
                current_rows = []
            for idx, item in enumerate(current_rows):
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title", "") or "(untitled)")
                kind = str(item.get("kind", "") or "attachment")
                path = str(item.get("source_path", "") or "")
                label = f"{kind}: {title}"
                if path:
                    label += f" ({Path(path).name})"
                lw_item = QListWidgetItem(label, list_widget)
                lw_item.setData(Qt.ItemDataRole.UserRole, idx)
            if list_widget.count() > 0 and list_widget.currentRow() < 0:
                list_widget.setCurrentRow(0)

        def _refresh_preview() -> None:
            """Internal helper for `_refresh_preview`."""
            item = list_widget.currentItem()
            if item is None:
                preview.clear()
                return
            idx_val = item.data(Qt.ItemDataRole.UserRole)
            current_rows = session.get("context_attachments", [])
            if not isinstance(idx_val, int) or not isinstance(current_rows, list) or not (0 <= idx_val < len(current_rows)):
                preview.clear()
                return
            row = current_rows[idx_val]
            if not isinstance(row, dict):
                preview.clear()
                return
            text = [
                f"Title: {row.get('title', '')}",
                f"Kind: {row.get('kind', '')}",
            ]
            source_path = str(row.get("source_path", "") or "")
            if source_path:
                text.append(f"Source: {source_path}")
            ls = int(row.get("line_start", 0) or 0)
            le = int(row.get("line_end", 0) or 0)
            if ls or le:
                text.append(f"Lines: {ls}-{le or ls}")
            text.extend(["", str(row.get("content", "") or "")])
            preview.setPlainText("\n".join(text))

        list_widget.currentItemChanged.connect(lambda _cur, _prev: _refresh_preview())

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, Qt.Orientation.Horizontal, dlg)
        add_manual_btn = btns.addButton("Add Manual", QDialogButtonBox.ButtonRole.ActionRole)
        remove_btn = btns.addButton("Remove Selected", QDialogButtonBox.ButtonRole.ActionRole)
        clear_btn = btns.addButton("Clear All", QDialogButtonBox.ButtonRole.DestructiveRole)
        root.addWidget(btns)
        btns.rejected.connect(dlg.reject)
        btns.button(QDialogButtonBox.StandardButton.Close).clicked.connect(dlg.accept)

        def _remove_selected() -> None:
            """Internal helper for `_remove_selected`."""
            item = list_widget.currentItem()
            if item is None:
                return
            idx_val = item.data(Qt.ItemDataRole.UserRole)
            current_rows = session.get("context_attachments", [])
            if not isinstance(idx_val, int) or not isinstance(current_rows, list) or not (0 <= idx_val < len(current_rows)):
                return
            del current_rows[idx_val]
            session["context_attachments"] = self._sanitize_context_attachments(current_rows)
            self._persist_history(save=True)
            self._refresh_attachment_chips()
            _refresh_list()
            _refresh_preview()

        def _clear_all() -> None:
            """Internal helper for `_clear_all`."""
            current_rows = session.get("context_attachments", [])
            if not isinstance(current_rows, list) or not current_rows:
                return
            ans = QMessageBox.question(
                dlg,
                "Clear Attachments",
                "Remove all attachments from this chat?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                return
            session["context_attachments"] = []
            self._persist_history(save=True)
            self._refresh_attachment_chips()
            _refresh_list()
            _refresh_preview()

        def _add_manual() -> None:
            """Internal helper for `_add_manual`."""
            title, ok = QInputDialog.getText(dlg, "Add Manual Attachment", "Title:")
            if not ok:
                return
            title = title.strip() or "Manual Snippet"
            body, ok = QInputDialog.getMultiLineText(dlg, "Add Manual Attachment", "Content:")
            if not ok or not body.strip():
                return
            self._add_context_attachment(
                {
                    "id": f"att-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                    "kind": "manual_snippet",
                    "title": title,
                    "source_path": "",
                    "content": body[:20000],
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
            self._refresh_attachment_chips()
            _refresh_list()
            _refresh_preview()

        add_manual_btn.clicked.connect(_add_manual)
        remove_btn.clicked.connect(_remove_selected)
        clear_btn.clicked.connect(_clear_all)
        _refresh_list()
        _refresh_preview()
        dlg.exec()

    def _toggle_memory_policy(self, key: str) -> None:
        """Internal helper for `_toggle_memory_policy`."""
        session = self._ensure_active_session(create_if_missing=True)
        if session is None:
            return
        policy = self._sanitize_memory_policy(session.get("memory_policy", {}))
        policy[key] = not bool(policy.get(key, False))
        session["memory_policy"] = policy
        session["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._persist_history(save=True)

    def _build_session_context_prefix(self, prompt: str) -> str:
        """Internal helper for `_build_session_context_prefix`."""
        session = self._current_session()
        if session is None:
            return ""
        policy = self._sanitize_memory_policy(session.get("memory_policy", {}))
        parts: list[str] = []
        if bool(policy.get("strict_citations_only", False)):
            parts.append(
                "Use citations for factual/code claims when possible. If evidence is insufficient, say what is missing."
            )
        if not bool(policy.get("allow_hidden_apply_commands", True)):
            parts.append("Do not emit hidden apply commands for insert/file/patch actions in this chat session.")
        attachments = session.get("context_attachments", [])
        if isinstance(attachments, list) and attachments:
            rendered: list[str] = []
            for item in attachments[-12:]:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title", "") or "Attachment")
                kind = str(item.get("kind", "") or "attachment")
                source_path = str(item.get("source_path", "") or "").strip()
                content = str(item.get("content", "") or "").strip()
                if not content:
                    continue
                header = f"[{kind}] {title}" + (f" ({source_path})" if source_path else "")
                rendered.append(f"{header}\n{content[:4000]}")
            if rendered:
                parts.append("[CHAT_CONTEXT_ATTACHMENTS]\n" + "\n\n".join(rendered) + "\n[/CHAT_CONTEXT_ATTACHMENTS]")
        window = getattr(self.ai_controller, "window", None)
        if bool(policy.get("include_current_file_auto", False)) and window is not None and hasattr(window, "active_tab"):
            tab = window.active_tab()
            if tab is not None:
                file_name = str(getattr(tab, "current_file", "") or "Untitled")
                file_text = str(tab.text_edit.get_text() or "")
                parts.append(
                    "[AUTO_CURRENT_FILE]\n"
                    f"file={file_name}\n"
                    f"{file_text[:12000]}\n"
                    "[/AUTO_CURRENT_FILE]"
                )
        if bool(policy.get("include_workspace_snippets_auto", False)) and window is not None:
            workspace_root = str(getattr(window, "settings", {}).get("workspace_root", "") or "").strip()
            if workspace_root:
                try:
                    files = collect_workspace_files(workspace_root, max_files=800)
                    max_files = int(getattr(window, "settings", {}).get("ai_workspace_qa_max_files", 6) or 6)
                    max_lines = int(getattr(window, "settings", {}).get("ai_workspace_qa_max_lines_per_file", 30) or 30)
                    snippets = build_workspace_citation_snippets(prompt, files, max_files=max_files, max_lines_per_file=max_lines, max_total_chars=12000)
                    if snippets:
                        sections = [f"FILE: {s.path}\n{s.excerpt}" for s in snippets]
                        parts.append("[AUTO_WORKSPACE_SNIPPETS]\n" + "\n\n".join(sections) + "\n[/AUTO_WORKSPACE_SNIPPETS]")
                except Exception:
                    pass
        out = ("\n\n".join(p for p in parts if str(p).strip())).strip()
        if out:
            self._log_ai_chat(
                "context prefix built "
                f"chars={len(out)} attachments={len(session.get('context_attachments', [])) if isinstance(session.get('context_attachments', []), list) else 0} "
                f"strict_citations={bool(policy.get('strict_citations_only', False))} "
                f"allow_hidden_apply={bool(policy.get('allow_hidden_apply_commands', True))}"
            )
        return out

        def _on_error(_message: str) -> None:
            """Internal helper for `_on_error`."""
            return

        self.ai_controller.ask_ai_chat(
            prompt,
            on_chunk=_on_chunk,
            on_done=_on_done,
            on_error=_on_error,
            on_cancel=lambda _partial: None,
        )

    @staticmethod
    def _has_internet_connection(timeout_sec: float = 0.8) -> bool:
        """Internal helper for `_has_internet_connection`."""
        try:
            sock = socket.create_connection(("1.1.1.1", 53), timeout=timeout_sec)
            sock.close()
            return True
        except OSError:
            return False

    def _on_stream_chunk(self, text: str) -> None:
        """Internal helper for `_on_stream_chunk`."""
        cid = self._active_response_correlation_id or "none"
        _LOGGER.debug("AI chat on_stream_chunk cid=%s chars=%d", cid, len(text or ""))
        self._set_generation_state("streaming")
        if self._active_reply_bubble is None:
            self._active_reply_bubble = self._add_bubble("", "assistant")
            self._active_reply_index = len(self._history)
            self._history.append({"role": "assistant", "text": ""})
        if not self._received_stream_content:
            self._received_stream_content = True
            self._stop_typing_animation(clear=True)
            if self._active_reply_bubble is not None:
                self._active_reply_bubble.set_text("")
        self._active_reply_bubble.append_text(text)
        if self._active_reply_index is not None and 0 <= self._active_reply_index < len(self._history):
            self._history[self._active_reply_index]["text"] += text
            self._persist_history(save=False)
        self._scroll_to_bottom()

    def _on_stream_done(self, full_text: str) -> None:
        """Internal helper for `_on_stream_done`."""
        cid = self._active_response_correlation_id or "none"
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._set_generation_state("idle")
        self._stop_typing_animation(clear=not self._received_stream_content)
        _LOGGER.debug(
            "AI chat on_stream_done start cid=%s full_chars=%d received_stream_content=%s",
            cid,
            len(full_text or ""),
            self._received_stream_content,
        )
        clean_text, offered_text, set_file_text, set_chat_title, offered_patch, offered_action = self._extract_hidden_commands(
            full_text,
            debug_correlation_id=cid,
        )
        session = self._current_session()
        memory_policy = self._sanitize_memory_policy(session.get("memory_policy", {})) if isinstance(session, dict) else self._default_memory_policy()
        allow_hidden_apply = bool(memory_policy.get("allow_hidden_apply_commands", True))
        self._pending_patch_offer = None
        self._pending_local_action = None
        if not offered_text and not set_file_text:
            offered_text = self._infer_plaintext_insert_offer(clean_text)
        if set_file_text and not allow_hidden_apply:
            set_file_text = ""
        if offered_text and not allow_hidden_apply:
            offered_text = ""
        if offered_patch and not allow_hidden_apply:
            offered_patch = None
        self._log_ai_chat(
            "stream done parsed commands "
            f"insert={bool(offered_text)} set_file={bool(set_file_text)} patch={bool(offered_patch)} "
            f"local_action={bool(offered_action)} title={bool(set_chat_title)} allow_hidden_apply={allow_hidden_apply}"
        )
        _LOGGER.debug(
            "AI chat on_stream_done parsed cid=%s clean_chars=%d insert_chars=%d set_file_chars=%d has_patch=%s has_local_action=%s title_chars=%d allow_hidden_apply=%s",
            cid,
            len(clean_text or ""),
            len(offered_text or ""),
            len(set_file_text or ""),
            bool(offered_patch),
            bool(offered_action),
            len(set_chat_title or ""),
            allow_hidden_apply,
        )
        if set_file_text:
            self._pending_set_file_offer = set_file_text
            self._pending_insert_offer = None
            self._pending_patch_offer = None
            self._pending_local_action = None
            self._refresh_pending_insert_indicator()
            if not re.search(r"\b(should|would|want).{0,60}\b(replace|set|update)\b.{0,30}\b(tab|file)\b", clean_text, re.IGNORECASE):
                clean_text = (clean_text.rstrip() + "\n\nShould I replace your current tab with this result?").strip()
        elif offered_patch:
            self._pending_patch_offer = offered_patch
            self._pending_insert_offer = None
            self._pending_set_file_offer = None
            self._pending_local_action = None
            self._refresh_pending_insert_indicator()
            if not re.search(r"\b(should|would|want).{0,60}\b(apply|review|patch|update)\b", clean_text, re.IGNORECASE):
                clean_text = (clean_text.rstrip() + "\n\nShould I review and apply this patch to your current tab?").strip()
        elif offered_text:
            self._pending_insert_offer = offered_text
            self._pending_set_file_offer = None
            self._pending_patch_offer = None
            self._pending_local_action = None
            self._refresh_pending_insert_indicator()
            if not re.search(r"\b(should|would|want).{0,40}\b(insert|add|paste)\b", clean_text, re.IGNORECASE):
                clean_text = (clean_text.rstrip() + "\n\nShould I insert this into your current tab?").strip()
        elif offered_action:
            self._pending_local_action = offered_action
            self._pending_insert_offer = None
            self._pending_set_file_offer = None
            self._pending_patch_offer = None
            self._refresh_pending_insert_indicator()
            if not re.search(r"\b(should|would|want).{0,60}\b(open|run|do|execute)\b", clean_text, re.IGNORECASE):
                label = str(offered_action.get("label", "this local action") or "this local action")
                clean_text = (clean_text.rstrip() + f"\n\nShould I run this local action: {label}?").strip()
        self._log_ai_chat(
            "pending action state "
            f"insert={bool(self._pending_insert_offer)} set_file={bool(self._pending_set_file_offer)} "
            f"patch={bool(self._pending_patch_offer)} local_action={bool(self._pending_local_action)}"
        )
        self._pending_apply_correlation_id = (
            cid if (self._pending_insert_offer or self._pending_set_file_offer or self._pending_patch_offer or self._pending_local_action) else None
        )
        _LOGGER.debug("AI chat on_stream_done pending_apply cid=%s pending_apply_cid=%s", cid, self._pending_apply_correlation_id)
        if not clean_text.strip():
            if self._pending_insert_offer or self._pending_set_file_offer or self._pending_patch_offer or self._pending_local_action:
                clean_text = "Ready to apply the pending AI action. Reply yes or no."
            else:
                clean_text = "(No visible response text.)"
        if self._active_reply_bubble is not None:
            self._active_reply_bubble.set_text(clean_text)
            row = self._find_bubble_row(self._active_reply_bubble)
            if isinstance(row, _HoverActionRow):
                row.set_actions_enabled(bool(clean_text.strip()))
        if self._active_reply_index is not None and 0 <= self._active_reply_index < len(self._history):
            self._history[self._active_reply_index]["text"] = clean_text
        if set_chat_title:
            self._apply_ai_chat_title_command(set_chat_title)
        callback = self._external_on_done
        self._external_on_done = None
        if callable(callback):
            try:
                _LOGGER.debug("AI chat on_stream_done invoking external callback cid=%s clean_chars=%d", cid, len(clean_text or ""))
                callback(clean_text)
            except Exception:
                _LOGGER.exception("AI chat on_stream_done external callback failed")
                pass
        self._active_reply_bubble = None
        self._active_reply_index = None
        self._received_stream_content = False
        _LOGGER.debug("AI chat response cycle stream complete cid=%s", cid)
        self._active_response_correlation_id = None
        self._persist_history(save=True)
        if not set_chat_title:
            self._request_ai_chat_title_fallback()
        self._scroll_to_bottom()

    def _on_stream_error(self, message: str) -> None:
        """Internal helper for `_on_stream_error`."""
        cid = self._active_response_correlation_id or "none"
        _LOGGER.debug("AI chat on_stream_error cid=%s message_len=%d", cid, len(message or ""))
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._set_generation_state("error")
        self._stop_typing_animation(clear=True)
        error_text = f"Error: {message}"
        if self._active_reply_bubble is not None:
            self._active_reply_bubble.set_text(error_text)
            if self._active_reply_index is not None and 0 <= self._active_reply_index < len(self._history):
                self._history[self._active_reply_index]["text"] = error_text
            else:
                self._history.append({"role": "assistant", "text": error_text})
        else:
            self._add_bubble(error_text, "assistant", persist=True)
        self._active_reply_bubble = None
        self._active_reply_index = None
        self._received_stream_content = False
        self._active_response_correlation_id = None
        self._persist_history(save=True)
        self._scroll_to_bottom()

    def _on_stream_cancel(self, _partial: str) -> None:
        """Internal helper for `_on_stream_cancel`."""
        cid = self._active_response_correlation_id or "none"
        _LOGGER.debug("AI chat on_stream_cancel cid=%s", cid)
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._set_generation_state("idle")
        self._stop_typing_animation(clear=not self._received_stream_content)
        self._active_reply_bubble = None
        self._active_reply_index = None
        self._received_stream_content = False
        self._active_response_correlation_id = None
        self._persist_history(save=True)
        self._scroll_to_bottom()

    def _start_typing_animation(self) -> None:
        """Internal helper for `_start_typing_animation`."""
        if self._active_reply_bubble is None:
            return
        self._typing_step = 0
        self._typing_active = True
        self._active_reply_bubble.set_text(".")
        self._typing_timer.start()

    def _stop_typing_animation(self, *, clear: bool) -> None:
        """Internal helper for `_stop_typing_animation`."""
        if self._typing_timer.isActive():
            self._typing_timer.stop()
        self._typing_active = False
        self._typing_step = 0
        if clear and self._active_reply_bubble is not None:
            self._active_reply_bubble.set_text("")

    def _advance_typing_animation(self) -> None:
        """Internal helper for `_advance_typing_animation`."""
        if not self._typing_active or self._active_reply_bubble is None:
            self._typing_timer.stop()
            return
        self._typing_step = (self._typing_step % 5) + 1
        self._active_reply_bubble.set_text("." * self._typing_step)

    def _add_bubble(self, text: str, role: str, *, persist: bool = False) -> _Bubble:
        """Internal helper for `_add_bubble`."""
        bubble = _Bubble(
            text,
            role,
            self.messages_host,
            copy_icon_data_uri=self._copy_code_icon_data_uri,
            on_pypad_link=self._handle_pypad_link,
        )
        row = _HoverActionRow(self.messages_host)
        row.setObjectName("aiChatRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        actions = QWidget(row)
        actions.setObjectName("aiChatBubbleActions")

        if role == "user":
            actions_layout = QVBoxLayout(actions)
            actions_layout.setContentsMargins(4, 0, 0, 0)
            actions_layout.setSpacing(4)
            row_layout.addStretch(1)
            row_layout.addWidget(bubble, 0)
            edit_btn = self._create_bubble_action_button(actions, icon_name="ai-inline-edit", tooltip="Edit prompt", text="Edit")
            copy_btn = self._create_bubble_action_button(actions, icon_name="edit-copy", tooltip="Copy", text="Copy")
            edit_btn.clicked.connect(lambda: self._edit_bubble_text(bubble))
            copy_btn.clicked.connect(lambda: self._copy_bubble_text(bubble))
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(copy_btn)
            actions_layout.addStretch(1)
            row_layout.addWidget(actions, 0)
        else:
            bubble_col = QWidget(row)
            bubble_col_layout = QVBoxLayout(bubble_col)
            bubble_col_layout.setContentsMargins(0, 0, 0, 0)
            bubble_col_layout.setSpacing(4)
            bubble_col_layout.addWidget(bubble, 0)
            actions_layout = _FlowLayout(actions, h_spacing=6, v_spacing=6)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            retry_btn = self._create_bubble_action_button(actions, icon_name="sync-horizontal", tooltip="Retry", text="Retry")
            copy_btn = self._create_bubble_action_button(actions, icon_name="edit-copy", tooltip="Copy", text="Copy")
            insert_btn = self._create_bubble_action_button(actions, icon_name="edit-paste", tooltip="Insert to tab", text="Insert")
            replace_btn = self._create_bubble_action_button(actions, icon_name="edit-find-replace", tooltip="Replace selection", text="Replace")
            append_btn = self._create_bubble_action_button(actions, icon_name="edit-paste", tooltip="Append to tab", text="Append")
            new_tab_btn = self._create_bubble_action_button(actions, icon_name="document-new", tooltip="Open in new tab", text="New Tab")
            replace_file_btn = self._create_bubble_action_button(
                actions,
                icon_name="document-save",
                tooltip="Replace whole file (with preview)",
                text="Replace File",
            )
            diff_btn = self._create_bubble_action_button(actions, icon_name="edit-find-replace", tooltip="Open diff preview", text="Diff")
            retry_btn.clicked.connect(lambda: self._retry_bubble_response(row))
            copy_btn.clicked.connect(lambda: self._copy_bubble_text(bubble))
            insert_btn.clicked.connect(lambda: self._insert_bubble_text_to_tab(bubble))
            replace_btn.clicked.connect(lambda: self._replace_selection_with_bubble_text(bubble))
            append_btn.clicked.connect(lambda: self._append_bubble_text_to_tab(bubble))
            new_tab_btn.clicked.connect(lambda: self._new_tab_from_bubble_text(bubble))
            replace_file_btn.clicked.connect(lambda: self._replace_whole_file_with_bubble_text(bubble))
            diff_btn.clicked.connect(lambda: self._open_bubble_diff_preview(bubble))
            actions_layout.addWidget(retry_btn)
            actions_layout.addWidget(copy_btn)
            actions_layout.addWidget(insert_btn)
            actions_layout.addWidget(replace_btn)
            actions_layout.addWidget(append_btn)
            actions_layout.addWidget(new_tab_btn)
            actions_layout.addWidget(replace_file_btn)
            actions_layout.addWidget(diff_btn)
            bubble_col_layout.addWidget(actions, 0)
            row_layout.addWidget(bubble_col, 0)
            row_layout.addStretch(1)

        row.set_actions_widget(actions)
        row.set_actions_enabled(bool(bubble.text().strip()))
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, row)
        if persist:
            self._history.append({"role": role, "text": text})
            self._persist_history(save=True)
        self._scroll_to_bottom()
        return bubble

    def _create_bubble_action_button(
        self,
        parent: QWidget,
        *,
        icon_name: str,
        tooltip: str,
        text: str,
        icon_only: bool = True,
    ) -> QPushButton:
        """Internal helper for `_create_bubble_action_button`."""
        btn = QPushButton(text, parent)
        btn.setObjectName("aiChatBubbleActionButton")
        btn.setProperty("ai_icon_name", icon_name)
        btn.setToolTip(tooltip)
        btn.setMinimumSize(28, 24)
        icon = self._icon(icon_name, size=14)
        if not icon.isNull():
            btn.setIcon(icon)
            if icon_only:
                btn.setText("")
                btn.setMaximumWidth(32)
        return btn

    def _copy_bubble_text(self, bubble: _Bubble) -> None:
        """Internal helper for `_copy_bubble_text`."""
        QApplication.clipboard().setText(bubble.text())

    def _edit_bubble_text(self, bubble: _Bubble) -> None:
        """Internal helper for `_edit_bubble_text`."""
        text = bubble.text().strip()
        if not text:
            return
        row = self._find_bubble_row(bubble)
        self._pending_prompt_edit_row = row
        window = getattr(self.ai_controller, "window", None)
        if window is not None and hasattr(window, "show_status_message"):
            window.show_status_message(
                "Editing this prompt will replace the messages after it when you send, so the reply stays consistent.",
                5000,
            )
        self.input.setPlainText(text)
        cursor = self.input.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.input.setTextCursor(cursor)
        self.input.setFocus()

    def _retry_bubble_response(self, row: QWidget) -> None:
        """Internal helper for `_retry_bubble_response`."""
        if not self.send_btn.isEnabled():
            return
        prompt = self._previous_user_prompt_for_row(row)
        if not prompt:
            return
        self.send_prompt(prompt=prompt, visible_prompt=prompt)

    def _find_bubble_row(self, bubble: _Bubble) -> QWidget | None:
        """Internal helper for `_find_bubble_row`."""
        parent = bubble.parentWidget()
        while parent is not None and parent is not self.messages_host:
            if parent.objectName() == "aiChatRow":
                return parent
            parent = parent.parentWidget()
        return None

    def _history_index_for_row(self, row: QWidget | None) -> int | None:
        """Internal helper for `_history_index_for_row`."""
        if row is None:
            return None
        for i in range(self.messages_layout.count() - 1):
            item = self.messages_layout.itemAt(i)
            widget = item.widget() if item is not None else None
            if widget is row:
                return i
        return None

    def _remove_rows_from_history_index(self, start_index: int) -> None:
        """Internal helper for `_remove_rows_from_history_index`."""
        if start_index < 0:
            start_index = 0
        while self.messages_layout.count() - 1 > start_index:
            item = self.messages_layout.takeAt(start_index)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

    def _previous_user_prompt_for_row(self, row: QWidget) -> str:
        """Internal helper for `_previous_user_prompt_for_row`."""
        target_index = -1
        for i in range(self.messages_layout.count()):
            item = self.messages_layout.itemAt(i)
            widget = item.widget() if item is not None else None
            if widget is row:
                target_index = i
                break
        if target_index <= 0:
            return ""
        for i in range(target_index - 1, -1, -1):
            item = self.messages_layout.itemAt(i)
            widget = item.widget() if item is not None else None
            if widget is None:
                continue
            for candidate in widget.findChildren(_Bubble):
                if getattr(candidate, "_role", "") == "user":
                    return candidate.text().strip()
        return ""

    def _try_send_edited_prompt_retry(self) -> bool:
        """Internal helper for `_try_send_edited_prompt_retry`."""
        row = self._pending_prompt_edit_row
        if row is None:
            return False
        edited_prompt = self.input.toPlainText().strip()
        if not edited_prompt:
            return False
        if not self.send_btn.isEnabled():
            return True
        prompt_index = self._history_index_for_row(row)
        if prompt_index is None or prompt_index < 0 or prompt_index >= len(self._history):
            self._pending_prompt_edit_row = None
            return False
        if str(self._history[prompt_index].get("role", "")) != "user":
            self._pending_prompt_edit_row = None
            return False
        for candidate in row.findChildren(_Bubble):
            if getattr(candidate, "_role", "") == "user":
                candidate.set_text(edited_prompt)
                break
        self._history[prompt_index]["text"] = edited_prompt
        del self._history[prompt_index + 1 :]
        self._remove_rows_from_history_index(prompt_index + 1)
        self._active_reply_bubble = None
        self._active_reply_index = None
        self._pending_prompt_edit_row = None
        self._persist_history(save=True)
        self.send_prompt(prompt=edited_prompt, visible_prompt="")
        return True

    def _refresh_pending_insert_indicator(self) -> None:
        """Internal helper for `_refresh_pending_insert_indicator`."""
        label = getattr(self, "pending_insert_label", None)
        if label is None:
            return
        pending = (self._pending_insert_offer or "").strip()
        pending_set = (self._pending_set_file_offer or "").strip()
        pending_patch = self._pending_patch_offer or {}
        pending_action = self._pending_local_action or {}
        if not pending and not pending_set and not pending_patch and not pending_action:
            label.setVisible(False)
            label.setText("Pending AI action: none")
            label.setToolTip("")
            return
        label.setVisible(True)
        if pending_action:
            preview = str(pending_action.get("summary") or pending_action.get("label") or "Local action")
            label.setText(f"Pending AI action: local action ({preview})")
            label.setToolTip(preview)
            return
        if pending_patch:
            scope = str(pending_patch.get("scope", "whole_file") or "whole_file")
            summary = str(pending_patch.get("summary", "") or "").strip() or f"{scope} patch"
            label.setText(f"Pending AI action: patch ready ({summary})")
            label.setToolTip(summary)
            return
        active = pending_set or pending
        preview = active.replace("\r", " ").replace("\n", " ").strip()
        if len(preview) > 90:
            preview = preview[:87] + "..."
        kind = "set file" if pending_set else "insert"
        label.setText(f"Pending AI action: {kind} ready ({len(active)} chars)")
        label.setToolTip(preview)

    @staticmethod
    def _is_affirmative(text: str) -> bool:
        """Internal helper for `_is_affirmative`."""
        value = re.sub(r"[^a-z]+", " ", text.lower()).strip()
        if not value:
            return False
        words = set(value.split())
        if value in {"y", "yes", "yeah", "yep", "sure", "ok", "okay"}:
            return True
        if value.startswith(("yes ", "yeah ", "yep ", "sure ", "ok ", "okay ")):
            return True
        if "go ahead" in value or "do it" in value:
            return True
        # Natural confirmations like "yes please insert it" / "please paste it"
        if words & {"insert", "paste", "add"} and words & {"yes", "yeah", "yep", "sure", "ok", "okay", "please"}:
            return True
        return False

    @staticmethod
    def _is_negative(text: str) -> bool:
        """Internal helper for `_is_negative`."""
        value = re.sub(r"[^a-z]+", " ", text.lower()).strip()
        if not value:
            return False
        if value in {"n", "no", "nope", "nah", "cancel", "skip"}:
            return True
        if value.startswith(("no ", "nope ", "nah ")):
            return True
        if "do not" in value or "dont" in value or "don't" in text.lower() or "not now" in value:
            return True
        return False

    @staticmethod
    def _looks_like_insert_confirmation(text: str) -> bool:
        """Internal helper for `_looks_like_insert_confirmation`."""
        value = re.sub(r"[^a-z]+", " ", text.lower()).strip()
        if not value:
            return False
        return bool(re.search(r"\b(insert|paste|add)\b", value))

    @staticmethod
    def _looks_like_set_file_confirmation(text: str) -> bool:
        """Internal helper for `_looks_like_set_file_confirmation`."""
        value = re.sub(r"[^a-z]+", " ", text.lower()).strip()
        if not value:
            return False
        return bool(re.search(r"\b(replace|set|update|overwrite)\b", value) and re.search(r"\b(file|tab|document)\b", value))

    def _insert_text_to_active_tab(self, text: str) -> bool:
        """Internal helper for `_insert_text_to_active_tab`."""
        tab = self.ai_controller.window.active_tab()
        if tab is None:
            QMessageBox.information(self, "Insert", "Open a tab first.")
            return False
        body = (text or "").strip()
        if not body:
            return False
        if tab.text_edit.get_text().strip():
            tab.text_edit.insert_text("\n\n")
        tab.text_edit.insert_text(body)
        return True

    def _set_text_to_active_tab(self, text: str) -> bool:
        """Internal helper for `_set_text_to_active_tab`."""
        tab = self.ai_controller.window.active_tab()
        if tab is None:
            QMessageBox.information(self, "Set File", "Open a tab first.")
            return False
        if tab.text_edit.is_read_only():
            QMessageBox.information(self, "Set File", "Current tab is read-only.")
            return False
        body = str(text or "")
        tab.text_edit.set_text(body)
        try:
            tab.text_edit.set_modified(True)
        except Exception:
            pass
        return True

    def _apply_review_mode(self) -> str:
        """Internal helper for `_apply_review_mode`."""
        window = getattr(self.ai_controller, "window", None)
        settings = getattr(window, "settings", {}) if window is not None else {}
        mode = str(settings.get("ai_apply_review_mode", "always_preview") or "always_preview").strip().lower()
        if mode not in {"always_preview", "direct_insert_only", "legacy_direct_apply"}:
            mode = "always_preview"
        return mode

    @staticmethod
    def _sha256_text(text: str) -> str:
        """Internal helper for `_sha256_text`."""
        return hashlib.sha256((text or "").encode("utf-8")).hexdigest()

    @staticmethod
    def _decode_hidden_json_payload(payload: str) -> dict[str, object] | None:
        """Internal helper for `_decode_hidden_json_payload`."""
        stripped = str(payload or "").strip()
        if not stripped:
            return None
        if stripped.lower().startswith("base64:"):
            try:
                stripped = base64.b64decode(stripped.split(":", 1)[1].strip()).decode("utf-8", errors="replace")
            except Exception:
                return None
        try:
            obj = json.loads(stripped)
        except Exception:
            return None
        return obj if isinstance(obj, dict) else None

    @staticmethod
    def _safe_int(value: object, default: int = 0) -> int:
        """Internal helper for `_safe_int`."""
        try:
            return int(value)
        except Exception:
            return default

    @classmethod
    def _parse_patch_offer(cls, payload: str) -> dict[str, object] | None:
        """Internal helper for `_parse_patch_offer`."""
        data = cls._decode_hidden_json_payload(payload)
        if not isinstance(data, dict):
            return None
        fmt = str(data.get("format", "") or "").strip().lower()
        target = str(data.get("target", "") or "").strip().lower()
        scope = str(data.get("scope", "") or "").strip().lower()
        base_hash = str(data.get("base_text_hash", "") or "").strip().lower()
        diff_text = str(data.get("diff", "") or "")
        if fmt != "unified_diff" or target != "current_tab":
            return None
        if scope not in {"whole_file", "selection", "paragraph", "function"}:
            return None
        if not re.fullmatch(r"[a-f0-9]{64}", base_hash):
            return None
        if not diff_text.strip():
            return None
        out = {
            "format": fmt,
            "target": target,
            "scope": scope,
            "base_text_hash": base_hash,
            "diff": diff_text,
            "summary": str(data.get("summary", "") or "").strip(),
            "metadata": data.get("metadata", {}) if isinstance(data.get("metadata", {}), dict) else {},
        }
        return out

    @classmethod
    def _parse_proposed_action(cls, payload: str) -> dict[str, object] | None:
        """Internal helper for `_parse_proposed_action`."""
        data = cls._decode_hidden_json_payload(payload)
        if not isinstance(data, dict):
            return None
        action_id = str(data.get("action_id", "") or "").strip().lower()
        if action_id not in {"open_settings", "open_workspace_files", "workspace_search", "open_file", "open_file_line"}:
            return None
        args = data.get("args", {})
        if not isinstance(args, dict):
            args = {}
        return {
            "action_id": action_id,
            "args": dict(args),
            "label": str(data.get("label", "") or action_id.replace("_", " ").title()),
            "summary": str(data.get("summary", "") or ""),
            "requires_confirmation": True,
        }

    @staticmethod
    def _split_unified_lines(text: str) -> list[str]:
        """Internal helper for `_split_unified_lines`."""
        if not text:
            return []
        lines = text.splitlines(keepends=True)
        if lines and not text.endswith(("\n", "\r")):
            lines[-1] = lines[-1]
        return lines

    @classmethod
    def _apply_unified_diff_to_text(cls, original_text: str, diff_text: str) -> str:
        """Internal helper for `_apply_unified_diff_to_text`."""
        original_lines = cls._split_unified_lines(original_text or "")
        diff_lines = cls._split_unified_lines(diff_text or "")
        i = 0
        # Skip optional file headers.
        while i < len(diff_lines):
            line = diff_lines[i]
            if line.startswith("--- ") or line.startswith("+++ "):
                i += 1
                continue
            if line.startswith("@@ "):
                break
            i += 1
        out: list[str] = []
        src_idx = 0
        hunk_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
        while i < len(diff_lines):
            header = diff_lines[i]
            if not header.startswith("@@ "):
                i += 1
                continue
            m = hunk_re.match(header)
            if not m:
                raise ValueError("Invalid unified diff hunk header.")
            old_start = int(m.group(1))
            old_count = int(m.group(2) or "1")
            start_idx = max(0, old_start - 1)
            if start_idx < src_idx:
                raise ValueError("Overlapping unified diff hunks.")
            out.extend(original_lines[src_idx:start_idx])
            src_idx = start_idx
            i += 1
            hunk_old_consumed = 0
            while i < len(diff_lines):
                row = diff_lines[i]
                if row.startswith("@@ "):
                    break
                if row.startswith("\\ No newline at end of file"):
                    i += 1
                    continue
                prefix = row[:1]
                body = row[1:] if prefix in {" ", "+", "-"} else row
                if prefix == " ":
                    if src_idx >= len(original_lines) or original_lines[src_idx] != body:
                        raise ValueError("Unified diff context mismatch.")
                    out.append(body)
                    src_idx += 1
                    hunk_old_consumed += 1
                elif prefix == "-":
                    if src_idx >= len(original_lines) or original_lines[src_idx] != body:
                        raise ValueError("Unified diff delete mismatch.")
                    src_idx += 1
                    hunk_old_consumed += 1
                elif prefix == "+":
                    out.append(body)
                else:
                    raise ValueError("Unsupported unified diff row.")
                i += 1
            if hunk_old_consumed != old_count:
                # Be tolerant when diff omits explicit 0-count quirks; otherwise treat as failure.
                if not (old_count == 0 and hunk_old_consumed == 0):
                    raise ValueError("Unified diff hunk line count mismatch.")
        out.extend(original_lines[src_idx:])
        return "".join(out)

    def _current_scope_bounds(self, scope: str, metadata: dict[str, object] | None = None) -> tuple[int, int, str] | None:
        """Internal helper for `_current_scope_bounds`."""
        tab = self.ai_controller.window.active_tab()
        if tab is None:
            return None
        text = tab.text_edit.get_text()
        scope_key = str(scope or "whole_file")
        if scope_key == "whole_file":
            return (0, len(text), "whole file")
        if scope_key == "selection":
            sel = tab.text_edit.selection_range()
            if not sel:
                return None
            start = tab.text_edit.index_from_line_col(sel[0], sel[1])
            end = tab.text_edit.index_from_line_col(sel[2], sel[3])
            return (start, end, "selection")
        if scope_key == "paragraph":
            start, end = paragraph_bounds(text, tab.text_edit.cursor_index())
            return (start, end, "paragraph")
        if scope_key == "function":
            path = str(getattr(tab, "current_file", "") or "")
            if path.lower().endswith(".py"):
                bounds = self._python_function_bounds(text, tab.text_edit.cursor_index())
                if bounds is not None:
                    return (*bounds, "function")
            sel = tab.text_edit.selection_range()
            if sel:
                start = tab.text_edit.index_from_line_col(sel[0], sel[1])
                end = tab.text_edit.index_from_line_col(sel[2], sel[3])
                return (start, end, "selection")
            return None
        return None

    @staticmethod
    def _python_function_bounds(text: str, cursor_index: int) -> tuple[int, int] | None:
        """Internal helper for `_python_function_bounds`."""
        lines = text.splitlines(keepends=True)
        if not lines:
            return None
        offsets: list[int] = []
        total = 0
        for line in lines:
            offsets.append(total)
            total += len(line)
        line_idx = 0
        for idx, start in enumerate(offsets):
            if idx + 1 < len(offsets):
                if start <= cursor_index < offsets[idx + 1]:
                    line_idx = idx
                    break
            else:
                line_idx = idx
        def_line = None
        indent = 0
        for i in range(line_idx, -1, -1):
            stripped = lines[i].lstrip()
            if stripped.startswith(("def ", "async def ")):
                def_line = i
                indent = len(lines[i]) - len(lines[i].lstrip(" \t"))
                break
        if def_line is None:
            return None
        end_line = len(lines)
        for j in range(def_line + 1, len(lines)):
            raw = lines[j]
            if not raw.strip():
                continue
            cur_indent = len(raw) - len(raw.lstrip(" \t"))
            if cur_indent <= indent and raw.lstrip().startswith(("def ", "async def ", "class ")):
                end_line = j
                break
        start = offsets[def_line]
        end = sum(len(lines[k]) for k in range(end_line))
        return (start, end)

    def _preview_and_apply_text(self, *, title: str, proposed_text: str, success_message: str) -> bool:
        """Internal helper for `_preview_and_apply_text`."""
        tab = self.ai_controller.window.active_tab()
        if tab is None:
            _LOGGER.debug("AI chat preview/apply blocked title=%s reason=no_active_tab", title)
            QMessageBox.information(self, title, "Open a tab first.")
            return False
        if tab.text_edit.is_read_only():
            _LOGGER.debug("AI chat preview/apply blocked title=%s reason=read_only", title)
            QMessageBox.information(self, title, "Current tab is read-only.")
            return False
        mode = self._apply_review_mode()
        _LOGGER.debug(
            "AI chat preview/apply start title=%s mode=%s original_chars=%d proposed_chars=%d",
            title,
            mode,
            len(str(tab.text_edit.get_text() or "")),
            len(proposed_text or ""),
        )
        if mode == "legacy_direct_apply" and len(proposed_text or "") <= 20000:
            _LOGGER.debug("AI chat preview/apply using legacy_direct_apply title=%s", title)
            return self._set_text_to_active_tab(proposed_text)
        if mode == "legacy_direct_apply":
            _LOGGER.debug(
                "AI chat preview/apply forcing preview despite legacy mode title=%s reason=large_payload",
                title,
            )
        original = tab.text_edit.get_text()
        dlg = AIEditPreviewDialog(self, original, proposed_text, title=f"{title} Preview")
        if dlg.exec() != QDialog.Accepted:
            _LOGGER.debug("AI chat preview/apply canceled in preview dialog title=%s", title)
            return False
        tab.text_edit.set_text(dlg.final_text)
        try:
            tab.text_edit.set_modified(True)
        except Exception:
            pass
        self.ai_controller.window.show_status_message(success_message, 3000)
        _LOGGER.debug("AI chat preview/apply applied title=%s final_chars=%d", title, len(str(dlg.final_text or "")))
        return True

    def _try_apply_pending_patch_offer(self) -> tuple[bool, str]:
        """Internal helper for `_try_apply_pending_patch_offer`."""
        offer = self._pending_patch_offer or {}
        if not offer:
            self._log_ai_chat("patch apply requested without pending patch")
            _LOGGER.debug("AI chat patch apply requested without pending patch offer")
            return False, "No patch offer."
        tab = self.ai_controller.window.active_tab()
        if tab is None:
            return False, "Open a tab first."
        if tab.text_edit.is_read_only():
            return False, "Current tab is read-only."
        scope = str(offer.get("scope", "whole_file") or "whole_file")
        metadata = offer.get("metadata", {})
        _LOGGER.debug(
            "AI chat patch apply start scope=%s has_metadata=%s diff_chars=%d",
            scope,
            isinstance(metadata, dict),
            len(str(offer.get("diff", "") or "")),
        )
        bounds = self._current_scope_bounds(scope, metadata if isinstance(metadata, dict) else {})
        if bounds is None:
            self._log_ai_chat(f"patch apply blocked invalid scope target scope={scope!r}")
            _LOGGER.debug("AI chat patch apply blocked invalid bounds scope=%s", scope)
            return False, f"Couldn't determine a valid {scope} target in the current tab."
        start, end, scope_label = bounds
        full_text = tab.text_edit.get_text()
        target_text = full_text[start:end]
        expected_hash = str(offer.get("base_text_hash", "") or "").lower()
        if self._sha256_text(target_text) != expected_hash:
            self._log_ai_chat(f"patch apply blocked hash mismatch scope={scope!r}")
            _LOGGER.debug(
                "AI chat patch apply hash mismatch scope=%s target_chars=%d expected_hash_len=%d",
                scope,
                len(target_text),
                len(expected_hash),
            )
            return False, f"The current {scope_label} changed since the AI generated the patch. Regenerate and try again."
        diff_text = str(offer.get("diff", "") or "")
        try:
            patched_target = self._apply_unified_diff_to_text(target_text, diff_text)
        except Exception:
            self._log_ai_chat(f"patch apply failed diff parse scope={scope!r}")
            _LOGGER.exception("AI chat patch apply diff parse failure scope=%s", scope)
            return False, "Couldn't parse/apply the AI patch safely. Ask AI to regenerate."
        proposed_full = full_text[:start] + patched_target + full_text[end:]
        ok = self._preview_and_apply_text(
            title="Patch Apply",
            proposed_text=proposed_full,
            success_message=f"Applied AI {scope_label} patch (after review).",
        )
        self._log_ai_chat(f"patch apply completed success={ok} scope={scope!r}")
        _LOGGER.debug("AI chat patch apply finished success=%s scope=%s scope_label=%s", ok, scope, scope_label)
        if ok:
            self.apply_completed.emit("patch", True, scope_label)
        return ok, ("Applied AI patch." if ok else "Patch apply canceled.")

    def _try_execute_pending_local_action(self) -> tuple[bool, str]:
        """Internal helper for `_try_execute_pending_local_action`."""
        action = self._pending_local_action or {}
        if not action:
            return False, "No local action."
        window = getattr(self.ai_controller, "window", None)
        if window is None:
            return False, "Main window unavailable."
        action_id = str(action.get("action_id", "") or "")
        args = action.get("args", {})
        if not isinstance(args, dict):
            args = {}
        try:
            if action_id == "open_settings":
                section = str(args.get("section", "") or "").strip() or None
                if hasattr(window, "open_settings"):
                    window.open_settings(initial_section=section)
                    self._log_ai_chat(f"local action executed open_settings section={section!r}")
                    self.apply_completed.emit("local_action", True, "open_settings")
                    return True, "Opened settings."
            elif action_id == "open_workspace_files":
                if hasattr(window, "show_workspace_files"):
                    window.show_workspace_files()
                    self._log_ai_chat("local action executed open_workspace_files")
                    self.apply_completed.emit("local_action", True, "open_workspace_files")
                    return True, "Opened workspace files."
            elif action_id == "workspace_search":
                q = str(args.get("q", "") or "").strip()
                if q and hasattr(window, "search_workspace"):
                    window.search_workspace()
                    self._log_ai_chat(f"local action executed workspace_search q={q!r}")
                    self.apply_completed.emit("local_action", True, "workspace_search")
                    return True, "Opened workspace search."
            elif action_id in {"open_file", "open_file_line"}:
                path = str(args.get("path", "") or "").strip()
                line = self._safe_int(args.get("line", 0), 0)
                if self._open_file_path_and_line(path, line=line if action_id == "open_file_line" else 0):
                    self._log_ai_chat(f"local action executed {action_id} path={path!r} line={line}")
                    self.apply_completed.emit("local_action", True, action_id)
                    return True, "Opened file."
        except Exception as exc:
            self._log_ai_chat(f"local action failed action_id={action_id} error={exc!r}")
            return False, f"Couldn't run local action: {exc}"
        self._log_ai_chat(f"local action unavailable action_id={action_id}")
        return False, "This AI local action isn't available in this window yet."

    def _open_file_path_and_line(self, raw_path: str, *, line: int = 0) -> bool:
        """Internal helper for `_open_file_path_and_line`."""
        window = getattr(self.ai_controller, "window", None)
        if window is None:
            return False
        raw_path = str(raw_path or "").strip()
        if not raw_path:
            return False
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            workspace_root = str(getattr(window, "settings", {}).get("workspace_root", "") or "").strip()
            if workspace_root:
                candidate = Path(workspace_root) / raw_path
        candidate = candidate.resolve()
        if not candidate.exists() or not candidate.is_file():
            QMessageBox.information(self, "Open File", f"File not found:\n{candidate}")
            return False
        opened = False
        for name in ("open_file_by_path", "open_file", "load_file"):
            fn = getattr(window, name, None)
            if callable(fn):
                try:
                    fn(str(candidate))
                    opened = True
                    break
                except TypeError:
                    continue
        if not opened:
            return False
        if line > 0:
            tab = window.active_tab() if hasattr(window, "active_tab") else None
            if tab is not None and hasattr(tab, "text_edit"):
                try:
                    tab.text_edit.set_cursor_position(max(0, line - 1), 0)
                except Exception:
                    pass
        return True

    def _confirm_set_file_apply(self) -> bool:
        """Internal helper for `_confirm_set_file_apply`."""
        window = getattr(self.ai_controller, "window", None)
        parent = window if window is not None else self
        reply = QMessageBox.question(
            parent,
            "Replace Current Tab?",
            "This will replace everything in your current tab with the AI result.\n\nDo you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    def _try_handle_insert_offer_response(self, prompt: str) -> bool:
        """Internal helper for `_try_handle_insert_offer_response`."""
        pending = (self._pending_insert_offer or "").strip()
        pending_set = (self._pending_set_file_offer or "").strip()
        pending_patch = self._pending_patch_offer or {}
        pending_action = self._pending_local_action or {}
        cid = self._pending_apply_correlation_id or "none"
        is_yes = self._is_affirmative(prompt)
        is_no = self._is_negative(prompt)
        _LOGGER.debug(
            "AI chat pending-apply response eval cid=%s yes=%s no=%s pending_insert=%s pending_set=%s pending_patch=%s pending_action=%s prompt_chars=%d",
            cid,
            is_yes,
            is_no,
            bool(pending),
            bool(pending_set),
            bool(pending_patch),
            bool(pending_action),
            len(prompt or ""),
        )
        if not pending and not pending_set and not pending_patch and not pending_action:
            if is_yes and (self._looks_like_insert_confirmation(prompt) or self._looks_like_set_file_confirmation(prompt)):
                _LOGGER.debug("AI chat yes/no apply response without pending action; emitting guidance bubble cid=%s", cid)
                self._add_bubble(prompt, "user", persist=True)
                self._add_bubble(
                    "I don't have a pending AI apply action for that message. Ask me to regenerate, then confirm when I ask to apply it.",
                    "assistant",
                    persist=True,
                )
                self._scroll_to_bottom()
                return True
            return False
        if is_yes:
            if pending_set and not self._confirm_set_file_apply():
                self._log_ai_chat("user canceled pending set-file apply from confirmation popup")
                if hasattr(self.ai_controller.window, "show_status_message"):
                    self.ai_controller.window.show_status_message("Canceled. Your current tab was not replaced.", 3000)
                return True
            self._log_ai_chat(
                "user confirmed pending action "
                f"set_file={bool(pending_set)} patch={bool(pending_patch)} insert={bool(pending)} local_action={bool(pending_action)}"
            )
            self._add_bubble(prompt, "user", persist=True)
            if pending_action:
                _LOGGER.debug("AI chat applying pending local action cid=%s", cid)
                applied, msg = self._try_execute_pending_local_action()
                self._add_bubble(msg, "assistant", persist=True)
            elif pending_patch:
                _LOGGER.debug("AI chat applying pending patch offer cid=%s", cid)
                applied, msg = self._try_apply_pending_patch_offer()
                self._add_bubble(msg, "assistant", persist=True)
            elif pending_set:
                mode = self._apply_review_mode()
                _LOGGER.debug("AI chat applying pending set_file cid=%s mode=%s chars=%d", cid, mode, len(pending_set))
                if mode == "legacy_direct_apply":
                    applied = self._set_text_to_active_tab(pending_set)
                else:
                    applied = self._preview_and_apply_text(
                        title="Set File",
                        proposed_text=pending_set,
                        success_message="Replaced your current tab with the AI result (after review).",
                    )
                if applied:
                    self._log_ai_chat(f"set-file apply completed success=True mode={mode}")
                    self.apply_completed.emit("set_file", True, "current_tab")
                    self._add_bubble("Replaced your current tab with the AI result.", "assistant", persist=True)
                else:
                    self._log_ai_chat(f"set-file apply completed success=False mode={mode}")
                    self._add_bubble("Couldn't replace/apply the current tab yet (or review was canceled).", "assistant", persist=True)
            else:
                _LOGGER.debug("AI chat applying pending insert cid=%s chars=%d", cid, len(pending))
                inserted = self._insert_text_to_active_tab(pending)
                if inserted:
                    self._log_ai_chat("insert apply completed success=True")
                    self.apply_completed.emit("insert", True, "current_tab")
                    self._add_bubble("Inserted into your current tab.", "assistant", persist=True)
                else:
                    self._log_ai_chat("insert apply completed success=False")
                    self._add_bubble("Couldn't insert yet. Open a tab first.", "assistant", persist=True)
            self._pending_insert_offer = None
            self._pending_set_file_offer = None
            self._pending_patch_offer = None
            self._pending_local_action = None
            self._refresh_pending_insert_indicator()
            self._scroll_to_bottom()
            _LOGGER.debug("AI chat pending action cleared after affirmative response cid=%s", cid)
            self._pending_apply_correlation_id = None
            return True
        if is_no:
            self._log_ai_chat(
                "user declined pending action "
                f"set_file={bool(pending_set)} patch={bool(pending_patch)} insert={bool(pending)} local_action={bool(pending_action)}"
            )
            self._add_bubble(prompt, "user", persist=True)
            self._add_bubble("Okay, I won't apply it.", "assistant", persist=True)
            if pending_set:
                self.apply_completed.emit("set_file", False, "declined")
            elif pending_patch:
                self.apply_completed.emit("patch", False, "declined")
            elif pending:
                self.apply_completed.emit("insert", False, "declined")
            elif pending_action:
                self.apply_completed.emit("local_action", False, "declined")
            self._pending_insert_offer = None
            self._pending_set_file_offer = None
            self._pending_patch_offer = None
            self._pending_local_action = None
            self._refresh_pending_insert_indicator()
            self._scroll_to_bottom()
            _LOGGER.debug("AI chat pending action cleared after decline response cid=%s", cid)
            self._pending_apply_correlation_id = None
            return True
        return False

    @classmethod
    def _extract_hidden_commands(
        cls,
        text: str,
        *,
        debug_correlation_id: str | None = None,
    ) -> tuple[str, str, str, str, dict[str, object] | None, dict[str, object] | None]:
        """Internal helper for `_extract_hidden_commands`."""
        raw = text or ""
        _LOGGER.debug("AI chat extract_hidden_commands start cid=%r chars=%d", debug_correlation_id, len(raw))
        offered_insert = ""
        offered_set_file = ""
        offered_chat_title = ""
        offered_patch: dict[str, object] | None = None
        offered_action: dict[str, object] | None = None

        def _decode(payload: str) -> str | None:
            """Internal helper for `_decode`."""
            stripped = payload.strip()
            if stripped.lower().startswith("base64:"):
                b64 = stripped.split(":", 1)[1].strip()
                try:
                    return base64.b64decode(b64).decode("utf-8", errors="replace").strip()
                except Exception:
                    return None
            return stripped or None

        def _decode_chat_title(payload: str) -> str | None:
            """Internal helper for `_decode_chat_title`."""
            stripped = str(payload or "").strip()
            decoded = _decode(stripped)
            if decoded is None:
                return None
            if stripped.lower().startswith("base64:"):
                return decoded
            # Be tolerant if the model forgets the `base64:` prefix for title commands.
            maybe_b64 = stripped.strip().strip("\"'")
            if re.fullmatch(r"[A-Za-z0-9+/=\s]{4,}", maybe_b64) and any(ch in maybe_b64 for ch in "+/="):
                try:
                    recovered = base64.b64decode(maybe_b64).decode("utf-8", errors="replace").strip()
                    if recovered:
                        return recovered
                except Exception:
                    pass
            return decoded

        def _replace_insert(match: re.Match[str]) -> str:
            """Internal helper for `_replace_insert`."""
            nonlocal offered_insert
            payload = str(match.group(1) or "")
            decoded = _decode(payload)
            if decoded:
                offered_insert = decoded
                _LOGGER.debug("AI chat extract command insert cid=%r chars=%d", debug_correlation_id, len(decoded))
            else:
                _LOGGER.debug(
                    "AI chat extract command insert cid=%r decode_failed payload_chars=%d",
                    debug_correlation_id,
                    len(payload),
                )
            return ""

        def _replace_set_file(match: re.Match[str]) -> str:
            """Internal helper for `_replace_set_file`."""
            nonlocal offered_set_file
            payload = str(match.group(1) or "")
            decoded = _decode(payload)
            if decoded is not None:
                offered_set_file = decoded
                _LOGGER.debug("AI chat extract command set_file cid=%r chars=%d", debug_correlation_id, len(decoded))
            else:
                _LOGGER.debug(
                    "AI chat extract command set_file cid=%r decode_failed payload_chars=%d",
                    debug_correlation_id,
                    len(payload),
                )
            return ""

        def _replace_set_chat_title(match: re.Match[str]) -> str:
            """Internal helper for `_replace_set_chat_title`."""
            nonlocal offered_chat_title
            payload = str(match.group(1) or "")
            decoded = _decode_chat_title(payload)
            if decoded is not None:
                offered_chat_title = decoded
                _LOGGER.debug("AI chat extract command set_chat_title cid=%r chars=%d", debug_correlation_id, len(decoded))
            else:
                _LOGGER.debug(
                    "AI chat extract command set_chat_title cid=%r decode_failed payload_chars=%d",
                    debug_correlation_id,
                    len(payload),
                )
            return ""

        def _replace_patch(match: re.Match[str]) -> str:
            """Internal helper for `_replace_patch`."""
            nonlocal offered_patch
            payload = str(match.group(1) or "")
            parsed = cls._parse_patch_offer(payload)
            if parsed is not None:
                offered_patch = parsed
                _LOGGER.debug(
                    "AI chat extract command patch cid=%r scope=%s diff_chars=%d",
                    debug_correlation_id,
                    str(parsed.get("scope", "") if isinstance(parsed, dict) else ""),
                    len(str(parsed.get("diff", "") if isinstance(parsed, dict) else "")),
                )
            else:
                _LOGGER.debug(
                    "AI chat extract command patch cid=%r parse_failed payload_chars=%d",
                    debug_correlation_id,
                    len(payload),
                )
            return ""

        def _replace_proposed_action(match: re.Match[str]) -> str:
            """Internal helper for `_replace_proposed_action`."""
            nonlocal offered_action
            payload = str(match.group(1) or "")
            parsed = cls._parse_proposed_action(payload)
            if parsed is not None:
                offered_action = parsed
                _LOGGER.debug(
                    "AI chat extract command local_action cid=%r action_id=%s",
                    debug_correlation_id,
                    str(parsed.get("action_id", "") if isinstance(parsed, dict) else ""),
                )
            else:
                _LOGGER.debug(
                    "AI chat extract command local_action cid=%r parse_failed payload_chars=%d",
                    debug_correlation_id,
                    len(payload),
                )
            return ""

        cleaned = cls._INSERT_CMD_RE.sub(_replace_insert, raw)
        cleaned = cls._SET_FILE_CMD_RE.sub(_replace_set_file, cleaned).strip()
        cleaned = cls._SET_CHAT_TITLE_CMD_RE.sub(_replace_set_chat_title, cleaned).strip()
        cleaned = cls._PATCH_CMD_RE.sub(_replace_patch, cleaned).strip()
        cleaned = cls._PROPOSE_ACTION_CMD_RE.sub(_replace_proposed_action, cleaned).strip()
        _LOGGER.debug(
            "AI chat extract_hidden_commands done cid=%r clean_chars=%d insert=%s set_file=%s title=%s patch=%s local_action=%s",
            debug_correlation_id,
            len(cleaned),
            bool(offered_insert),
            bool(offered_set_file),
            bool(offered_chat_title),
            bool(offered_patch),
            bool(offered_action),
        )
        return cleaned, offered_insert, offered_set_file, offered_chat_title, offered_patch, offered_action

    @classmethod
    def _infer_plaintext_insert_offer(cls, text: str) -> str | None:
        # Fallback: if the assistant returns a long standalone prose block without the hidden
        # command protocol, treat it as an insert offer so the yes/no flow still works.
        """Internal helper for `_infer_plaintext_insert_offer`."""
        cleaned = (text or "").strip()
        if not cleaned:
            return None
        if len(cleaned) < 220:
            return None
        lowered = cleaned.lower()
        if "```" in cleaned or "pypad://" in lowered:
            return None
        if lowered.startswith(("error:", "i don't have ", "i cant ", "i can't ")):
            return None
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if not lines:
            return None
        bullet_like = sum(
            1
            for line in lines
            if re.match(r"^(?:[-*]\s+|\d+\.\s+|[A-Za-z]:\s+)", line)
        )
        if len(lines) >= 3 and bullet_like / max(1, len(lines)) > 0.45:
            return None
        sentence_hits = len(re.findall(r"[.!?](?:\s|$)", cleaned))
        if sentence_hits < 2:
            return None

        # If the assistant already asked an insert question visibly, exclude it from the offered text.
        payload = re.sub(
            r"(?:\n\s*){1,3}(?:should|would|do)\b.{0,120}\b(insert|add|paste)\b.*$",
            "",
            cleaned,
            flags=re.IGNORECASE | re.DOTALL,
        ).strip()
        return payload or cleaned

    def _handle_pypad_link(self, href: str) -> bool:
        """Internal helper for `_handle_pypad_link`."""
        window = getattr(self.ai_controller, "window", None)
        if window is None:
            _LOGGER.debug("AI chat pypad link ignored no-window href=%r", href)
            return False
        self._log_ai_chat(f"open deep link href={href!r}")
        _LOGGER.debug("AI chat pypad link start href=%r", href)
        parsed = urlparse(href.strip())
        normalized = href.strip().lower()
        target = normalized.split("?", 1)[0].split("#", 1)[0].strip()
        try:
            if target.startswith("pypad://settings"):
                if hasattr(window, "open_settings"):
                    section = ""
                    prefix = "pypad://settings/"
                    if target.startswith(prefix):
                        section = target[len(prefix):].strip("/")
                    _LOGGER.debug("AI chat pypad link route=settings section=%r", section)
                    window.open_settings(initial_section=section or None)
                    return True
                return False
            if target == "pypad://ai/chat":
                if hasattr(window, "toggle_ai_chat_panel"):
                    _LOGGER.debug("AI chat pypad link route=ai_chat")
                    window.toggle_ai_chat_panel(True)
                    return True
                return False
            if target == "pypad://workspace":
                if hasattr(window, "open_workspace_folder"):
                    _LOGGER.debug("AI chat pypad link route=workspace")
                    window.open_workspace_folder()
                    return True
                return False
            if target == "pypad://workspace/files":
                if hasattr(window, "show_workspace_files"):
                    _LOGGER.debug("AI chat pypad link route=workspace_files")
                    window.show_workspace_files()
                    return True
                return False
            if target == "pypad://workspace/search":
                qs = parse_qs(parsed.query or "")
                q = (qs.get("q", [""])[0] or "").strip()
                _LOGGER.debug("AI chat pypad link route=workspace_search q=%r", q)
                if hasattr(window, "search_workspace"):
                    window.search_workspace()
                    if q:
                        self.ai_controller.window.show_status_message(f"Workspace search hint: {q}", 3000)
                    return True
                return False
            if target == "pypad://file/open":
                qs = parse_qs(parsed.query or "")
                path = unquote((qs.get("path", [""])[0] or "").strip())
                line = 0
                if parsed.fragment and parsed.fragment.lower().startswith("line="):
                    line = self._safe_int(parsed.fragment.split("=", 1)[1], 0)
                if "line" in qs:
                    line = self._safe_int(qs.get("line", ["0"])[0], line)
                _LOGGER.debug("AI chat pypad link route=file_open path=%r line=%d", path, line)
                if self._open_file_path_and_line(path, line=line):
                    return True
                return False
        except Exception as exc:
            _LOGGER.exception("AI chat pypad link failed href=%r", href)
            self._log_ai_chat(f"deep link failed href={href!r} error={exc!r}")
            QMessageBox.warning(self, "PyPad Link", f"Could not open link:\n{href}\n\n{exc}")
            return True
        self._log_ai_chat(f"deep link unmapped href={href!r}")
        _LOGGER.debug("AI chat pypad link unmapped href=%r target=%r", href, target)
        QMessageBox.information(self, "PyPad Link", f"Link not yet mapped:\n{href}")
        return True

    def _insert_bubble_text_to_tab(self, bubble: _Bubble) -> None:
        """Internal helper for `_insert_bubble_text_to_tab`."""
        tab = self.ai_controller.window.active_tab()
        if tab is None:
            QMessageBox.information(self, "Insert", "Open a tab first.")
            return
        text = bubble.text().strip()
        if not text:
            return
        if tab.text_edit.get_text().strip():
            tab.text_edit.insert_text("\n\n")
        tab.text_edit.insert_text(text)

    def _replace_selection_with_bubble_text(self, bubble: _Bubble) -> None:
        """Internal helper for `_replace_selection_with_bubble_text`."""
        window = self.ai_controller.window
        tab = window.active_tab()
        if tab is None:
            QMessageBox.information(self, "Replace Selection", "Open a tab first.")
            return
        if tab.text_edit.is_read_only():
            QMessageBox.information(self, "Replace Selection", "Current tab is read-only.")
            return
        if not tab.text_edit.has_selection():
            QMessageBox.information(self, "Replace Selection", "Select text first.")
            return
        text = bubble.text().strip()
        if not text:
            return
        tab.text_edit.replace_selection(text)

    def _append_bubble_text_to_tab(self, bubble: _Bubble) -> None:
        """Internal helper for `_append_bubble_text_to_tab`."""
        window = self.ai_controller.window
        tab = window.active_tab()
        if tab is None:
            QMessageBox.information(self, "Append", "Open a tab first.")
            return
        if tab.text_edit.is_read_only():
            QMessageBox.information(self, "Append", "Current tab is read-only.")
            return
        text = bubble.text().strip()
        if not text:
            return
        existing = tab.text_edit.get_text()
        end_line = max(0, len(existing.splitlines()) - 1) if existing else 0
        end_col = len(existing.splitlines()[-1]) if existing.splitlines() else 0
        tab.text_edit.set_cursor_position(end_line, end_col)
        if existing.strip():
            tab.text_edit.insert_text("\n\n")
        tab.text_edit.insert_text(text)

    def _new_tab_from_bubble_text(self, bubble: _Bubble) -> None:
        """Internal helper for `_new_tab_from_bubble_text`."""
        window = self.ai_controller.window
        text = bubble.text().strip()
        if not text:
            return
        if not hasattr(window, "add_new_tab"):
            QMessageBox.information(self, "New Tab", "Couldn't create a new tab.")
            return
        window.add_new_tab(text=text, make_current=True)

    def _replace_whole_file_with_bubble_text(self, bubble: _Bubble) -> None:
        """Internal helper for `_replace_whole_file_with_bubble_text`."""
        text = bubble.text().strip()
        if not text:
            return
        self._preview_and_apply_text(
            title="Replace Whole File",
            proposed_text=text,
            success_message="Replaced your current tab with the AI result (after review).",
        )

    def _open_bubble_diff_preview(self, bubble: _Bubble) -> None:
        """Internal helper for `_open_bubble_diff_preview`."""
        tab = self.ai_controller.window.active_tab()
        if tab is None:
            QMessageBox.information(self, "Diff Preview", "Open a tab first.")
            return
        if tab.text_edit.is_read_only():
            QMessageBox.information(self, "Diff Preview", "Current tab is read-only.")
            return
        proposed = bubble.text().strip()
        if not proposed:
            return
        original = tab.text_edit.get_text()
        dlg = AIEditPreviewDialog(self, original, proposed, title="Bubble Diff Preview")
        if dlg.exec() != QDialog.Accepted:
            return
        tab.text_edit.set_text(dlg.final_text)
        try:
            tab.text_edit.set_modified(True)
        except Exception:
            pass
        if hasattr(self.ai_controller.window, "show_status_message"):
            self.ai_controller.window.show_status_message("Applied changes from diff preview.", 3000)

    def _stop_generation(self) -> None:
        """Internal helper for `_stop_generation`."""
        self.ai_controller.cancel_active_chat_request()

    def _load_history(self) -> None:
        """Internal helper for `_load_history`."""
        settings = getattr(self.ai_controller.window, "settings", {})
        self._chat_sessions = self._load_chat_sessions_from_disk(settings)
        if not self._chat_sessions:
            self._chat_sessions = self._sanitize_chat_sessions(settings.get("ai_chat_sessions", []))
        if not self._chat_sessions:
            legacy = settings.get("ai_chat_history", [])
            if isinstance(legacy, list) and legacy:
                boot = self._default_chat_session(title="Previous Chat")
                boot_msgs: list[dict[str, str]] = []
                for item in legacy[-200:]:
                    if not isinstance(item, dict):
                        continue
                    role = str(item.get("role", "")).strip().lower()
                    text = str(item.get("text", ""))
                    if role in {"user", "assistant"}:
                        boot_msgs.append({"role": role, "text": text})
                boot["messages"] = boot_msgs
                self._chat_sessions = [boot]
        if not self._chat_sessions:
            self._chat_sessions = [self._default_chat_session()]
        requested = str(settings.get("ai_chat_active_session_id", "") or "")
        if requested and any(str(s.get("id", "")) == requested for s in self._chat_sessions):
            self._active_chat_id = requested
        else:
            self._active_chat_id = str(self._chat_sessions[0].get("id", ""))
        self._set_active_chat(self._active_chat_id, persist=False)
        self._persist_history(save=False)

    def _chat_storage_dir(self) -> Path:
        """Internal helper for `_chat_storage_dir`."""
        return get_ai_chats_dir_path()

    def _chat_storage_file_name(self, session: dict[str, object]) -> str:
        """Internal helper for `_chat_storage_file_name`."""
        value = str(session.get("storage_file", "") or "").strip()
        if value:
            return value
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        value = f"{stamp}.json"
        session["storage_file"] = value
        return value

    def _write_chat_session_to_disk(self, session: dict[str, object]) -> None:
        """Internal helper for `_write_chat_session_to_disk`."""
        folder = self._chat_storage_dir()
        folder.mkdir(parents=True, exist_ok=True)
        file_name = self._chat_storage_file_name(session)
        path = folder / file_name
        path.write_bytes(json.dumps(session, indent=2).encode("utf-8"))

    def _load_chat_sessions_from_disk(self, settings: dict[str, object]) -> list[dict[str, object]]:
        """Internal helper for `_load_chat_sessions_from_disk`."""
        folder = self._chat_storage_dir()
        file_names: list[str] = []
        raw_names = settings.get("ai_chat_session_files")
        if isinstance(raw_names, list):
            file_names = [str(item).strip() for item in raw_names if str(item).strip()]
        elif folder.exists():
            file_names = [p.name for p in sorted(folder.glob("*.json"))]
        sessions: list[dict[str, object]] = []
        for name in file_names:
            path = folder / name
            if not path.exists():
                continue
            try:
                loaded = json.loads(path.read_bytes().decode("utf-8"))
            except Exception:
                _LOGGER.exception("Failed to read AI chat session from %s", path)
                continue
            if isinstance(loaded, dict):
                loaded["storage_file"] = name
                sessions.append(loaded)
        return self._sanitize_chat_sessions(sessions)

    def _prune_orphaned_chat_files(self, referenced_file_names: set[str]) -> None:
        """Internal helper for `_prune_orphaned_chat_files`."""
        folder = self._chat_storage_dir()
        if not folder.exists():
            return
        for path in folder.glob("*.json"):
            if path.name in referenced_file_names:
                continue
            try:
                path.unlink()
            except Exception:
                _LOGGER.exception("Failed to remove orphaned AI chat file: %s", path)

    def _persist_history(self, *, save: bool) -> None:
        """Internal helper for `_persist_history`."""
        window = self.ai_controller.window
        session = self._current_session()
        if session is not None:
            session["messages"] = list(self._history[-200:])
            session["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._chat_sessions = self._sanitize_chat_sessions(self._chat_sessions)
        if not self._chat_sessions:
            self._chat_sessions = [self._default_chat_session()]
            self._active_chat_id = str(self._chat_sessions[0].get("id", ""))
        file_names: list[str] = []
        for item in self._chat_sessions[-200:]:
            try:
                file_name = self._chat_storage_file_name(item)
                file_names.append(file_name)
                self._write_chat_session_to_disk(item)
            except Exception:
                _LOGGER.exception("Failed to persist AI chat session to disk")
                continue
        self._prune_orphaned_chat_files(set(file_names))
        window.settings["ai_chat_session_files"] = file_names
        window.settings["ai_chat_active_session_id"] = str(self._active_chat_id or "")
        self._history = list(self._history[-200:])
        self._refresh_chat_session_header()
        if save and hasattr(window, "save_settings_to_disk"):
            window.save_settings_to_disk()

    def _is_chat_near_bottom(self, *, threshold_px: int = 48) -> bool:
        """Internal helper for `_is_chat_near_bottom`."""
        bar = self.scroll.verticalScrollBar()
        return (bar.maximum() - bar.value()) <= max(0, int(threshold_px))

    def _update_chat_stick_to_bottom_state(self) -> None:
        """Internal helper for `_update_chat_stick_to_bottom_state`."""
        self._chat_stick_to_bottom = self._is_chat_near_bottom()

    def _scroll_to_bottom(self, *, force: bool = False) -> None:
        """Internal helper for `_scroll_to_bottom`."""
        if not force and not bool(getattr(self, "_chat_stick_to_bottom", True)):
            return
        def _apply() -> None:
            """Internal helper for `_apply`."""
            if not hasattr(self, "scroll") or self.scroll is None:
                return
            bar = self.scroll.verticalScrollBar()
            bar.setValue(bar.maximum())

        _apply()
        # Some bubble height updates happen after markdown/layout passes; follow-up snaps keep
        # the viewport pinned to the latest message after send/stream updates.
        QTimer.singleShot(0, self, _apply)
        QTimer.singleShot(30, self, _apply)


