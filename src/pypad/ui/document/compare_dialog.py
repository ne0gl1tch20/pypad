"""Present an accessible compare and merge workflow for two plain-text sources.

The dialog is intentionally large and review-oriented so it feels closer to a
serious editor compare surface than a generic modal utility.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from pypad.ui.document.compare_engine import apply_hunk_choices, build_diff_hunks, build_unified_diff
from pypad.ui.document.compare_models import CompareSource
from pypad.ui.theme.theme_tokens import build_dialog_theme_qss_from_tokens, build_tokens_from_settings


class CompareDialog(QDialog):
    """Review two sources side by side and choose how merged output should be built."""

    def __init__(self, parent, *, left: CompareSource, right: CompareSource) -> None:
        """Construct the compare dialog and seed it with the supplied sources."""
        super().__init__(parent)
        self._window = parent
        self._left = left
        self._right = right
        self._hunks = build_diff_hunks(left.text, right.text)
        self._final_text = right.text
        self.setWindowTitle("Compare and Merge")
        self.resize(1180, 760)
        self.setAccessibleName("Compare and merge dialog")
        self.setAccessibleDescription(
            "Review differences between two text sources, choose which side to keep for each change, and apply the merged result."
        )
        tokens = build_tokens_from_settings(getattr(parent, "settings", {}))
        self.setStyleSheet(build_dialog_theme_qss_from_tokens(tokens))

        root = QVBoxLayout(self)
        intro = QLabel(
            "Review the left and right sources, then choose how each changed block should appear in the merged result.",
            self,
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        top = QHBoxLayout()
        self.left_label = QLabel(f"Left source: {left.label}", self)
        self.right_label = QLabel(f"Right source: {right.label}", self)
        self.summary_label = QLabel(self)
        self.summary_label.setObjectName("compareSummaryLabel")
        self.summary_label.setWordWrap(True)
        top.addWidget(self.left_label, 1)
        top.addWidget(self.right_label, 1)
        top.addWidget(self.summary_label, 2)
        root.addLayout(top)

        split = QSplitter(Qt.Horizontal, self)
        split.setChildrenCollapsible(False)
        root.addWidget(split, 1)

        left_panel = QWidget(split)
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel(left.label, left_panel))
        self.left_view = QTextEdit(left_panel)
        self.left_view.setReadOnly(True)
        self.left_view.setPlainText(left.text)
        self.left_view.setAccessibleName("Left source preview")
        self.left_view.setAccessibleDescription("Shows the full left-side source used for comparison.")
        left_layout.addWidget(self.left_view, 1)

        center_panel = QWidget(split)
        center_layout = QVBoxLayout(center_panel)
        center_layout.addWidget(QLabel("Changed blocks", center_panel))
        self.hunk_list = QListWidget(center_panel)
        self.hunk_list.setAccessibleName("Compare results list")
        self.hunk_list.setAccessibleDescription(
            "Lists the changed blocks found between the left and right sources."
        )
        center_layout.addWidget(self.hunk_list, 1)
        self.keep_left_box = QCheckBox("Keep left side for selected change", center_panel)
        self.keep_right_box = QCheckBox("Keep right side for selected change", center_panel)
        center_layout.addWidget(self.keep_left_box)
        center_layout.addWidget(self.keep_right_box)
        nav = QHBoxLayout()
        self.prev_btn = QPushButton("Previous Change", center_panel)
        self.next_btn = QPushButton("Next Change", center_panel)
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.next_btn)
        center_layout.addLayout(nav)

        right_panel = QWidget(split)
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("Merged result preview", right_panel))
        self.result_view = QTextEdit(right_panel)
        self.result_view.setReadOnly(True)
        self.result_view.setAccessibleName("Merged result preview")
        self.result_view.setAccessibleDescription(
            "Shows the final merged text based on the current choices for each changed block."
        )
        right_layout.addWidget(self.result_view, 1)
        self.diff_view = QTextEdit(right_panel)
        self.diff_view.setReadOnly(True)
        self.diff_view.setAccessibleName("Unified diff preview")
        self.diff_view.setAccessibleDescription("Shows the full unified diff between the two selected sources.")
        right_layout.addWidget(self.diff_view, 1)
        split.setSizes([420, 280, 480])

        buttons = QDialogButtonBox(self)
        self.apply_btn = buttons.addButton("Apply to Current Tab", QDialogButtonBox.AcceptRole)
        self.new_tab_btn = buttons.addButton("Open Merged Result in New Tab", QDialogButtonBox.ActionRole)
        self.close_btn = buttons.addButton(QDialogButtonBox.Close)
        root.addWidget(buttons)

        self.hunk_list.currentItemChanged.connect(self._sync_selected_hunk)
        self.keep_left_box.toggled.connect(self._on_choice_toggled)
        self.keep_right_box.toggled.connect(self._on_choice_toggled)
        self.prev_btn.clicked.connect(self._select_previous_hunk)
        self.next_btn.clicked.connect(self._select_next_hunk)
        self.apply_btn.clicked.connect(self.accept)
        self.new_tab_btn.clicked.connect(self._open_in_new_tab)
        self.close_btn.clicked.connect(self.reject)

        self._populate_hunks()
        self._refresh_outputs()

    @property
    def final_text(self) -> str:
        """Return the merged result selected by the user."""
        return self._final_text

    def _populate_hunks(self) -> None:
        """Fill the changed-block list and set the initial summary text."""
        self.hunk_list.clear()
        if not self._hunks:
            self.summary_label.setText("No differences found. These sources currently match.")
            self.keep_left_box.setEnabled(False)
            self.keep_right_box.setEnabled(False)
            return
        self.summary_label.setText(f"{len(self._hunks)} change block(s) found. Review each block before applying.")
        for hunk in self._hunks:
            row = QListWidgetItem(f"{hunk.title}: {hunk.summary}")
            row.setData(Qt.ItemDataRole.UserRole, hunk.index)
            row.setCheckState(Qt.CheckState.Checked)
            self.hunk_list.addItem(row)
        self.hunk_list.setCurrentRow(0)

    def _selected_hunk_index(self) -> int | None:
        """Return the 1-based hunk index for the selected row, if any."""
        item = self.hunk_list.currentItem()
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        return int(value) if value is not None else None

    def _sync_selected_hunk(self) -> None:
        """Mirror the current row state into the keep-left / keep-right controls."""
        index = self._selected_hunk_index()
        if index is None:
            return
        item = self.hunk_list.currentItem()
        if item is None:
            return
        keep_left = item.checkState() == Qt.CheckState.Unchecked
        self.keep_left_box.blockSignals(True)
        self.keep_right_box.blockSignals(True)
        self.keep_left_box.setChecked(keep_left)
        self.keep_right_box.setChecked(not keep_left)
        self.keep_left_box.blockSignals(False)
        self.keep_right_box.blockSignals(False)

    def _on_choice_toggled(self) -> None:
        """Map the selected checkbox choice back onto the changed-block row state."""
        item = self.hunk_list.currentItem()
        if item is None:
            return
        if self.keep_left_box.isChecked() and self.keep_right_box.isChecked():
            sender = self.sender()
            if sender is self.keep_left_box:
                self.keep_right_box.setChecked(False)
            else:
                self.keep_left_box.setChecked(False)
        item.setCheckState(Qt.CheckState.Unchecked if self.keep_left_box.isChecked() else Qt.CheckState.Checked)
        self._refresh_outputs()

    def _selected_left_hunks(self) -> list[int]:
        """Return the list of changed blocks currently assigned to the left source."""
        indices: list[int] = []
        for row in range(self.hunk_list.count()):
            item = self.hunk_list.item(row)
            if item.checkState() == Qt.CheckState.Unchecked:
                indices.append(int(item.data(Qt.ItemDataRole.UserRole)))
        return indices

    def _refresh_outputs(self) -> None:
        """Rebuild the merged result and unified diff previews from current choices."""
        self._final_text = apply_hunk_choices(
            self._left.text,
            self._right.text,
            use_left_hunks=self._selected_left_hunks(),
            use_right_hunks=[],
        )
        self.result_view.setPlainText(self._final_text)
        self.diff_view.setPlainText(
            build_unified_diff(
                self._left.text,
                self._right.text,
                left_label=self._left.label,
                right_label=self._right.label,
            )
            or "No unified diff output is needed because these sources match."
        )

    def _select_previous_hunk(self) -> None:
        """Move the current selection to the previous changed block."""
        row = self.hunk_list.currentRow()
        if row > 0:
            self.hunk_list.setCurrentRow(row - 1)

    def _select_next_hunk(self) -> None:
        """Move the current selection to the next changed block."""
        row = self.hunk_list.currentRow()
        if row < self.hunk_list.count() - 1:
            self.hunk_list.setCurrentRow(row + 1)

    def _open_in_new_tab(self) -> None:
        """Open the merged result in a fresh tab without closing the review dialog."""
        if hasattr(self._window, "add_new_tab"):
            self._window.add_new_tab(text=self._final_text, make_current=True)
            if hasattr(self._window, "show_status_message"):
                self._window.show_status_message("Opened merged result in a new tab.", 3000)

    @classmethod
    def run_for_sources(cls, parent, *, left: CompareSource, right: CompareSource) -> str | None:
        """Open the compare dialog and return merged text if the user applies it."""
        dialog = cls(parent, left=left, right=right)
        if dialog.exec() == QDialog.Accepted:
            return dialog.final_text
        return None
