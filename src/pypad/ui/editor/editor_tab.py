"""Represent a single editor tab and the supporting UI elements bound to one open document.

This module belongs to the editor widget and text-manipulation UI layer. It helps explain how `pypad.ui.editor` is structured and where this file fits into the runtime workflow.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMenu,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)
import re
from typing import Any

from pypad.ui.editor.editor_widget import EditorWidget
from pypad.ui.document.document_fidelity import render_markdown_to_mathjax_html

from pypad.ui.system.version_history import VersionHistory

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except Exception:
    QWebEngineView = None


class MarkdownPreviewPane(QWidget):
    """Preview pane that renders Markdown as plain rich text or MathJax HTML when available."""
    def __init__(self, parent=None) -> None:
        """Create the fallback text preview and optional web-based MathJax renderer."""
        super().__init__(parent)
        self._text_preview = QTextEdit(self)
        self._text_preview.setReadOnly(True)
        self._text_preview.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._text_preview.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._web_preview = None
        if QWebEngineView is not None:
            try:
                self._web_preview = QWebEngineView(self)
                self._web_preview.hide()
            except Exception:
                self._web_preview = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._text_preview)
        if self._web_preview is not None:
            layout.addWidget(self._web_preview)

    def supports_mathjax(self) -> bool:
        """Return whether the web preview backend is available for MathJax rendering."""
        return self._web_preview is not None

    def setMarkdown(self, text: str) -> None:
        """Compatibility wrapper that renders Markdown using the plain preview path."""
        self.set_markdown(text, enable_mathjax=False, dark_mode=False)

    def set_markdown(self, text: str, *, enable_mathjax: bool, dark_mode: bool) -> None:
        """Render Markdown using either QTextEdit or a MathJax-capable web preview."""
        self._text_preview.setLayoutDirection(self.layoutDirection())
        if enable_mathjax and self._web_preview is not None:
            self._text_preview.hide()
            self._web_preview.show()
            self._web_preview.setHtml(render_markdown_to_mathjax_html(text, dark_mode=dark_mode))
            return
        if self._web_preview is not None:
            self._web_preview.hide()
        self._text_preview.show()
        self._text_preview.setMarkdown(text)

    def clear(self) -> None:
        """Clear both preview backends so the pane has no visible content."""
        if self._web_preview is not None:
            self._web_preview.setHtml("")
        self._text_preview.clear()


class EditorTab(QWidget):
    """Stateful container for one open document, including editor, preview, and tab metadata."""
    def __init__(self, parent=None) -> None:
        """Construct the editor container and initialize all per-tab runtime state."""
        super().__init__(parent)
        self.text_edit = EditorWidget(self)
        if hasattr(self.text_edit.widget, "setVerticalScrollBarPolicy"):
            self.text_edit.widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        if hasattr(self.text_edit.widget, "setHorizontalScrollBarPolicy"):
            self.text_edit.widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.editor_splitter = QSplitter(Qt.Horizontal, self)
        self.editor_splitter.addWidget(self.text_edit.widget)
        self.editor_splitter.setStretchFactor(0, 1)
        self._main_stack = QStackedWidget(self)
        self._main_stack.addWidget(self.editor_splitter)
        self._media_page = QWidget(self)
        self._media_page_layout = QVBoxLayout(self._media_page)
        self._media_page_layout.setContentsMargins(0, 0, 0, 0)
        self._main_stack.addWidget(self._media_page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._main_stack)

        self.current_file: str | None = None
        self.zoom_steps = 0
        self.markdown_mode_enabled = False
        self.track_changes_enabled = False
        self.version_history = VersionHistory()
        self.last_snapshot_time: float | None = None
        self.syntax_highlighter: Any = None
        self.syntax_language_override: str | None = None
        self.autosave_id: str | None = None
        self.autosave_path: str | None = None
        self.pinned = False
        self.favorite = False
        self.read_only = False
        self.tab_color: str | None = None
        self.bookmarks: set[int] = set()
        self.bookmark_marker_id: int | None = None
        self.encoding: str | None = None
        self.eol_mode: str | None = None
        self.large_file = False
        self.large_file_notice_shown = False
        self.partial_large_preview = False
        self.large_file_total_lines = 0
        self.large_file_total_chars = 0
        self.clone_editor: EditorWidget | None = None
        self.split_mode: str | None = None
        self.column_mode = False
        self.multi_caret = False
        self.code_folding = True
        self.show_space_tab = False
        self.show_eol = False
        self.show_non_printing = False
        self.show_control_chars = False
        self.show_all_chars = False
        self.show_indent_guides = True
        self.show_wrap_symbol = False
        self.show_line_numbers = True
        self.auto_completion_mode = "all"
        self.tags: list[str] = []
        self.encryption_enabled = False
        self.encryption_password: str | None = None
        self.trust_state = "trusted"
        self.trust_source = "unknown"
        self.trust_persisted = False
        self.trust_reason: str | None = None
        self.trust_banner_dismissed = False
        self.save_restrictions: set[str] = set()
        self.opened_via_startup_arg = False
        self.quiz_mode_enabled = False
        self.quiz_items: list[dict[str, Any]] = []
        self.quiz_user_answers: dict[int, str] = {}
        self.quiz_score_result: dict[str, Any] | None = None
        self.quiz_original_text: str | None = None
        self.typing_test_mode_enabled = False
        self.typing_test_config: dict[str, Any] = {}
        self.typing_test_source_text: str = ""
        self.typing_test_original_text: str | None = None
        self.typing_test_started_at: float | None = None
        self.typing_test_finished = False
        self.typing_test_result: dict[str, Any] | None = None
        self.media_mode_enabled = False
        self.media_path: str | None = None

        self._setup_editor_context_menu()

    def clear_media_mode(self) -> None:
        """Remove any active media widget and return the tab to normal editor mode."""
        while self._media_page_layout.count():
            item = self._media_page_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.media_mode_enabled = False
        self.media_path = None
        self._main_stack.setCurrentWidget(self.editor_splitter)

    def set_media_widget(self, widget: QWidget, path: str) -> None:
        """Replace editor mode with a media-view widget for the supplied file path."""
        self.clear_media_mode()
        self._media_page_layout.addWidget(widget)
        self.media_mode_enabled = True
        self.media_path = path
        self._main_stack.setCurrentWidget(self._media_page)

    def _setup_editor_context_menu(self) -> None:
        """Install the custom context-menu hook on the underlying editor widget."""
        widget = self.text_edit.widget
        if not hasattr(widget, "setContextMenuPolicy") or not hasattr(widget, "customContextMenuRequested"):
            return
        widget.setContextMenuPolicy(Qt.CustomContextMenu)
        widget.customContextMenuRequested.connect(self._show_editor_context_menu)

    def _main_window(self):
        """Return the owning main window when the tab is attached to one."""
        window = self.window()
        return window if window is not None else None

    @staticmethod
    def _context_icon(window, icon_name: str, size: int = 14) -> QIcon:
        """Resolve a context-menu icon through the main window's shared icon helper."""
        icon_fn = getattr(window, "_icon", None)
        if callable(icon_fn):
            try:
                return icon_fn(icon_name, size=size)
            except Exception:
                return QIcon()
        return QIcon()

    @classmethod
    def _context_icon_name_for_action(cls, action_attr: str) -> str | None:
        """Map known window action names to the icon identifiers used in the context menu."""
        mapping = {
            "explain_selection_ai_action": "ai-explain",
            "ai_inline_edit_action": "ai-inline-edit",
            "ai_rewrite_shorten_action": "ai-refactor",
            "ai_rewrite_formal_action": "ai-refactor",
            "ai_rewrite_grammar_action": "ai-refactor",
            "ai_rewrite_summarize_action": "ai-refactor",
            "ai_attach_selection_chat_action": "ai-attach",
            "ai_attach_current_file_chat_action": "ai-attach",
            "ai_attach_workspace_search_chat_action": "ai-attach-search",
            "ai_ask_context_action": "ai-citations",
            "ai_workspace_citations_action": "ai-workspace-cite",
            "homework_solve_ai_action": "ai-explain",
            "homework_solve_solutions_ai_action": "ai-refactor",
            "homework_answer_ai_action": "ai-sparkles",
            "workspace_search_action": "edit-find",
            "find_action": "edit-find",
            "replace_action": "edit-find-replace",
            "find_next_action": "edit-find",
            "find_prev_action": "edit-find",
            "search_selection_web_action": "ai-sparkles",
            "open_selection_file_action": "document-list",
            "open_selection_folder_action": "document-map",
            "comment_toggle_action": "md-quote",
            "comment_single_action": "md-quote",
            "comment_single_un_action": "md-quote",
            "comment_block_action": "md-code-block",
            "comment_block_un_action": "md-code-block",
            "add_comment_action": "collab-presence",
            "review_comments_action": "collab-resolve",
            "convert_uppercase_action": "format-bold",
            "convert_lowercase_action": "format-italic",
            "convert_propercase_action": "format-text-wrapping",
            "convert_sentencecase_action": "format-text-wrapping",
            "convert_invertcase_action": "show-symbol",
            "convert_randomcase_action": "show-all-chars",
            "style_all_occurrences_action": "sync-horizontal",
            "style_one_token_action": "sync-vertical",
            "clear_style_action": "ai-clear",
            "copy_styled_text_action": "edit-copy",
            "indent_action": "indent-guide",
            "unindent_action": "indent-guide",
            "blank_trim_trailing_action": "tail-follow",
            "line_duplicate_action": "md-bullets",
            "line_join_action": "md-link",
            "line_split_action": "sync-vertical",
            "line_remove_empty_action": "ai-clear",
        }
        return mapping.get(action_attr)

    @classmethod
    def _set_action_context_icon(cls, window, action, action_attr: str) -> None:
        """Apply the appropriate themed icon to a context-menu action when available."""
        if action is None:
            return
        icon_name = cls._context_icon_name_for_action(action_attr)
        if not icon_name:
            return
        icon = cls._context_icon(window, icon_name)
        if not icon.isNull():
            action.setIcon(icon)

    @staticmethod
    def _add_window_action(menu: QMenu, window, action_attr: str) -> bool:
        """Add an action from the owning window to a menu if that action exists."""
        action = getattr(window, action_attr, None)
        if action is None:
            return False
        menu.addAction(action)
        return True

    @staticmethod
    def _swatch_icon(color_hex: str) -> QIcon:
        """Create a small solid-color icon used for style-token menu entries."""
        pix = QPixmap(12, 12)
        pix.fill(QColor(color_hex))
        return QIcon(pix)

    @classmethod
    def _add_window_action_if_enabled(cls, menu: QMenu, window, action_attr: str) -> bool:
        """Add an enabled window action to a menu and apply its context icon."""
        action = getattr(window, action_attr, None)
        if action is None or not action.isEnabled():
            return False
        cls._set_action_context_icon(window, action, action_attr)
        menu.addAction(action)
        return True

    @staticmethod
    def _prune_empty_menu(parent_menu: QMenu, submenu: QMenu) -> None:
        """Remove an empty submenu so the final context menu only shows usable sections."""
        if not submenu.actions():
            submenu.menuAction().setVisible(False)
            try:
                parent_menu.removeAction(submenu.menuAction())
            except Exception:
                pass

    def _build_basic_fallback_menu(self, window) -> QMenu:
        """Build a minimal editing menu used when the richer menu cannot be assembled."""
        menu = QMenu(self.text_edit.widget)
        for attr in (
            "cut_action",
            "copy_action",
            "paste_action",
            "delete_action",
            "select_all_action",
        ):
            self._add_window_action(menu, window, attr)
        self._add_window_action_if_enabled(menu, window, "spell_check_word_action")
        self._add_window_action_if_enabled(menu, window, "spell_check_document_action")
        return menu

    def _add_quick_ai_row(self, menu: QMenu, window) -> bool:
        """Insert a compact row of high-frequency AI actions at the top of the context menu."""
        entries = [
            ("Explain", "explain_selection_ai_action", "ai-explain"),
            ("Rewrite", "ai_inline_edit_action", "ai-inline-edit"),
            ("Attach", "ai_attach_selection_chat_action", "ai-attach"),
        ]
        enabled_entries = []
        for label, attr, icon_name in entries:
            action = getattr(window, attr, None)
            if action is None or not action.isEnabled():
                continue
            enabled_entries.append((label, action, icon_name))
        if not enabled_entries:
            return False
        row_host = QWidget(menu)
        row_layout = QHBoxLayout(row_host)
        row_layout.setContentsMargins(6, 4, 6, 4)
        row_layout.setSpacing(6)
        for label, action, icon_name in enabled_entries:
            btn = QToolButton(row_host)
            btn.setText(label)
            btn.setAutoRaise(False)
            btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            icon = self._context_icon(window, icon_name, size=14)
            if not icon.isNull():
                btn.setIcon(icon)
            shortcut_text = action.shortcut().toString() if hasattr(action, "shortcut") else ""
            tooltip = action.text()
            if shortcut_text:
                tooltip += f" ({shortcut_text})"
            btn.setToolTip(tooltip)
            btn.clicked.connect(lambda _checked=False, a=action, m=menu: (m.close(), a.trigger()))
            row_layout.addWidget(btn)
        row_layout.addStretch(1)
        row_action = QWidgetAction(menu)
        row_action.setDefaultWidget(row_host)
        menu.addAction(row_action)
        return True

    def _attach_more_ai_button(self, menu: QMenu, ai_menu: QMenu) -> None:
        """Attach a 'More AI' button to the quick-action row that opens the full AI submenu."""
        if ai_menu is None or not ai_menu.actions():
            return
        row_action = None
        for act in menu.actions():
            if isinstance(act, QWidgetAction):
                row_action = act
                break
        if row_action is None:
            return
        row_host = row_action.defaultWidget()
        if row_host is None:
            return
        row_layout = row_host.layout()
        if not isinstance(row_layout, QHBoxLayout):
            return
        more_btn = QToolButton(row_host)
        more_btn.setText("More AI...")
        more_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        icon = self._context_icon(self._main_window(), "ai-sparkles", size=14)
        if not icon.isNull():
            more_btn.setIcon(icon)
        more_btn.setToolTip("Open the full AI context submenu")
        more_btn.clicked.connect(
            lambda _checked=False, m=menu, sub=ai_menu, btn=more_btn: sub.exec(btn.mapToGlobal(btn.rect().bottomLeft()))
        )
        row_layout.insertWidget(max(0, row_layout.count() - 1), more_btn)

    def _add_style_swatch_submenus(self, style_menu: QMenu, window) -> bool:
        """Populate token-styling submenus with swatch icons and available style actions."""
        swatches = [
            ("Using 1st Style", "style_all_1_action", "style_one_1_action", "#8fb6a2"),
            ("Using 2nd Style", "style_all_2_action", "style_one_2_action", "#e6ea8e"),
            ("Using 3rd Style", "style_all_3_action", "style_one_3_action", "#e293ab"),
            ("Using 4th Style", "style_all_4_action", "style_one_4_action", "#53aa66"),
            ("Using 5th Style", "style_all_5_action", "style_one_5_action", "#8f7ce8"),
        ]
        any_added = False
        style_all_menu = style_menu.addMenu("Style all occurrences of token")
        style_one_menu = style_menu.addMenu("Style one token")
        clear_menu = style_menu.addMenu("Clear style")
        for label, all_attr, one_attr, color in swatches:
            all_action = getattr(window, all_attr, None)
            if all_action is not None and all_action.isEnabled():
                all_action.setIcon(self._swatch_icon(color))
                style_all_menu.addAction(all_action)
                any_added = True
            one_action = getattr(window, one_attr, None)
            if one_action is not None and one_action.isEnabled():
                one_action.setIcon(self._swatch_icon(color))
                style_one_menu.addAction(one_action)
                any_added = True
        clear_added = False
        for idx, color in enumerate(["#8fb6a2", "#e6ea8e", "#e293ab", "#53aa66", "#8f7ce8"], start=1):
            clear_action = getattr(window, f"clear_style_{idx}_action", None)
            if clear_action is not None and clear_action.isEnabled():
                clear_action.setIcon(self._swatch_icon(color))
                clear_menu.addAction(clear_action)
                clear_added = True
                any_added = True
        clear_all_action = getattr(window, "clear_style_all_action", None)
        if clear_all_action is not None and clear_all_action.isEnabled():
            clear_menu.addSeparator()
            clear_menu.addAction(clear_all_action)
            clear_added = True
            any_added = True
        self._prune_empty_menu(style_menu, style_all_menu)
        self._prune_empty_menu(style_menu, style_one_menu)
        if not clear_added:
            self._prune_empty_menu(style_menu, clear_menu)
        return any_added

    def _add_selection_tools_submenu(self, selection_menu: QMenu, window, selected_text: str) -> bool:
        """Add selection-adjacent built-in tools to the context menu."""
        if not str(selected_text or "").strip():
            return False
        tools_menu = selection_menu.addMenu("Tools")
        tools_icon = self._context_icon(window, "command-palette")
        if not tools_icon.isNull():
            tools_menu.setIcon(tools_icon)
        added = False

        text_tool_actions = (
            "password_generator_action",
            "qr_tools_action",
            "annotations_manager_action",
            "taskers_action",
            "reminders_hub_action",
        )
        numeric_tool_actions = (
            "random_number_action",
            "finance_calculator_action",
            "scientific_calculator_action",
            "unit_converter_action",
            "equation_solver_action",
            "graph_viewer_action",
            "currency_converter_action",
            "color_picker_action",
            "world_clock_action",
            "timer_stopwatch_action",
            "reader_mode_action",
        )

        for attr in text_tool_actions:
            added = self._add_window_action_if_enabled(tools_menu, window, attr) or added
        if self._selection_looks_like_math(selected_text):
            if added:
                tools_menu.addSeparator()
            for attr in numeric_tool_actions:
                added = self._add_window_action_if_enabled(tools_menu, window, attr) or added
        if not added:
            self._prune_empty_menu(selection_menu, tools_menu)
        return added

    def _show_editor_context_menu(self, pos) -> None:
        """Build and show the full editor context menu based on selection and action state."""
        window = self._main_window()
        if window is None:
            return
        if hasattr(window, "update_action_states"):
            try:
                window.update_action_states()
            except Exception:
                pass

        widget = self.text_edit.widget
        menu = QMenu(widget)
        added_quick_ai = self._add_quick_ai_row(menu, window)
        if added_quick_ai:
            menu.addSeparator()
        for attr in (
            "cut_action",
            "copy_action",
            "paste_action",
            "delete_action",
            "select_all_action",
        ):
            self._add_window_action(menu, window, attr)
        self._add_window_action_if_enabled(menu, window, "spell_check_word_action")
        self._add_window_action_if_enabled(menu, window, "spell_check_document_action")
        selected_text = ""
        try:
            selected_text = str(self.text_edit.selected_text() or "")
        except Exception:
            selected_text = ""
        if selected_text.strip() and self._selection_looks_like_math(selected_text):
            menu.addSeparator()
            for attr in (
                "homework_solve_ai_action",
                "homework_solve_solutions_ai_action",
                "homework_answer_ai_action",
            ):
                self._add_window_action_if_enabled(menu, window, attr)
        menu.addSeparator()
        selection_menu = menu.addMenu("Selection")
        selection_icon = self._context_icon(window, "edit-copy")
        if not selection_icon.isNull():
            selection_menu.setIcon(selection_icon)

        selection_search_menu = selection_menu.addMenu("Search / Open")
        search_icon = self._context_icon(window, "edit-find")
        if not search_icon.isNull():
            selection_search_menu.setIcon(search_icon)
        selection_search_added = False
        for attr in (
            "open_selection_file_action",
            "open_selection_folder_action",
            "search_selection_web_action",
            "find_next_action",
            "find_prev_action",
        ):
            selection_search_added = self._add_window_action_if_enabled(selection_search_menu, window, attr) or selection_search_added
        if not selection_search_added:
            self._prune_empty_menu(selection_menu, selection_search_menu)

        convert_menu = selection_menu.addMenu("Convert Case")
        convert_icon = self._context_icon(window, "format-text-wrapping")
        if not convert_icon.isNull():
            convert_menu.setIcon(convert_icon)
        convert_added = False
        for attr in (
            "convert_uppercase_action",
            "convert_lowercase_action",
            "convert_propercase_action",
            "convert_sentencecase_action",
            "convert_invertcase_action",
            "convert_randomcase_action",
        ):
            convert_added = self._add_window_action_if_enabled(convert_menu, window, attr) or convert_added
        if not convert_added:
            self._prune_empty_menu(selection_menu, convert_menu)

        comment_menu = selection_menu.addMenu("Comment / Review")
        comment_icon = self._context_icon(window, "md-quote")
        if not comment_icon.isNull():
            comment_menu.setIcon(comment_icon)
        comment_count = 0
        for attr in (
            "comment_toggle_action",
            "comment_single_action",
            "comment_single_un_action",
            "comment_block_action",
            "comment_block_un_action",
        ):
            if self._add_window_action_if_enabled(comment_menu, window, attr):
                comment_count += 1
        review_added = False
        for attr in ("add_comment_action", "review_comments_action"):
            review_added = self._add_window_action_if_enabled(comment_menu, window, attr) or review_added
        if review_added and comment_count:
            comment_menu.addSeparator()
        if not comment_count and not review_added:
            self._prune_empty_menu(selection_menu, comment_menu)

        style_menu = selection_menu.addMenu("Style Tokens")
        style_icon = self._context_icon(window, "sync-horizontal")
        if not style_icon.isNull():
            style_menu.setIcon(style_icon)
        style_added = False
        for attr in ("copy_styled_text_action",):
            style_added = self._add_window_action_if_enabled(style_menu, window, attr) or style_added
        if self._add_style_swatch_submenus(style_menu, window):
            style_added = True
        if not style_added:
            self._prune_empty_menu(selection_menu, style_menu)

        self._add_selection_tools_submenu(selection_menu, window, selected_text)

        ai_menu = menu.addMenu("AI")
        ai_icon = self._context_icon(window, "ai-sparkles")
        if not ai_icon.isNull():
            ai_menu.setIcon(ai_icon)
        ai_added = False
        for attr in ("explain_selection_ai_action", "ai_inline_edit_action"):
            ai_added = self._add_window_action_if_enabled(ai_menu, window, attr) or ai_added
        rewrite_menu = ai_menu.addMenu("Rewrite Selection")
        rewrite_icon = self._context_icon(window, "ai-refactor")
        if not rewrite_icon.isNull():
            rewrite_menu.setIcon(rewrite_icon)
        rewrite_added = False
        for attr in (
            "ai_rewrite_shorten_action",
            "ai_rewrite_formal_action",
            "ai_rewrite_grammar_action",
            "ai_rewrite_summarize_action",
        ):
            rewrite_added = self._add_window_action_if_enabled(rewrite_menu, window, attr) or rewrite_added
        if rewrite_added:
            ai_added = True
        else:
            self._prune_empty_menu(ai_menu, rewrite_menu)
        attach_menu = ai_menu.addMenu("Attach to AI Chat")
        attach_icon = self._context_icon(window, "ai-attach")
        if not attach_icon.isNull():
            attach_menu.setIcon(attach_icon)
        attach_added = False
        for attr in (
            "ai_attach_selection_chat_action",
            "ai_attach_current_file_chat_action",
            "ai_attach_workspace_search_chat_action",
        ):
            attach_added = self._add_window_action_if_enabled(attach_menu, window, attr) or attach_added
        if attach_added:
            ai_added = True
        else:
            self._prune_empty_menu(ai_menu, attach_menu)
        for attr in ("ai_ask_context_action", "ai_workspace_citations_action"):
            ai_added = self._add_window_action_if_enabled(ai_menu, window, attr) or ai_added
        if not ai_added:
            self._prune_empty_menu(menu, ai_menu)
        elif added_quick_ai:
            self._attach_more_ai_button(menu, ai_menu)

        advanced_menu = menu.addMenu("Advanced")
        advanced_icon = self._context_icon(window, "command-palette")
        if not advanced_icon.isNull():
            advanced_menu.setIcon(advanced_icon)
        advanced_added = False

        search_menu = advanced_menu.addMenu("Search")
        if not search_icon.isNull():
            search_menu.setIcon(search_icon)
        search_added = False
        for attr in ("find_action", "replace_action", "workspace_search_action"):
            search_added = self._add_window_action_if_enabled(search_menu, window, attr) or search_added
        if search_added:
            advanced_added = True
        else:
            self._prune_empty_menu(advanced_menu, search_menu)

        lines_menu = advanced_menu.addMenu("Lines / Text")
        lines_icon = self._context_icon(window, "md-bullets")
        if not lines_icon.isNull():
            lines_menu.setIcon(lines_icon)
        lines_added = False
        for attr in (
            "indent_action",
            "unindent_action",
            "blank_trim_trailing_action",
            "line_duplicate_action",
            "line_join_action",
            "line_split_action",
            "line_remove_empty_action",
        ):
            lines_added = self._add_window_action_if_enabled(lines_menu, window, attr) or lines_added
        if lines_added:
            advanced_added = True
        else:
            self._prune_empty_menu(advanced_menu, lines_menu)

        if not selection_menu.actions():
            self._prune_empty_menu(menu, selection_menu)
        if not advanced_added:
            self._prune_empty_menu(menu, advanced_menu)
        if menu.actions() and menu.actions()[-1].isSeparator():
            menu.removeAction(menu.actions()[-1])

        global_pos = widget.mapToGlobal(pos) if hasattr(widget, "mapToGlobal") else pos
        menu.exec(global_pos)

    @staticmethod
    def _selection_looks_like_math(text: str) -> bool:
        """Heuristically detect whether selected text resembles mathematical content."""
        probe = str(text or "").strip()
        if not probe:
            return False
        patterns = (
            r"\$[^$]+\$",
            r"\$\$[\s\S]+\$\$",
            r"\\\([^\)]+\\\)",
            r"\\\[[\s\S]+\\\]",
            r"\\begin\{[a-zA-Z*]+\}",
            r"[A-Za-z]\s*=\s*[^=\n]+",
            r"\d+\s*[-+*/=^]\s*\d+",
            r"[A-Za-z0-9\)\]]\s*[-+*/=]\s*[A-Za-z0-9\(\[]",
            r"\b(sin|cos|tan|log|ln|exp|sqrt)\b",
            r"\^|_|\\frac|\\sqrt|\\sum|\\int|\\alpha|\\beta|\\theta|\\pi",
        )
        return any(re.search(pattern, probe) for pattern in patterns)


