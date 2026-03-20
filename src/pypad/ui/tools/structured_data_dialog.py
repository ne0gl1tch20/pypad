"""Offer structured-data formatting, validation, and preview tools for common text formats.

The dialog keeps raw text as the source of truth while providing accessible tree,
table, and validation surfaces that help users inspect JSON, XML, CSV, and YAML.
"""

from __future__ import annotations

import csv
import io
import json
import xml.dom.minidom
import xml.etree.ElementTree as ET
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pypad.ui.theme.theme_tokens import build_dialog_theme_qss_from_tokens, build_tokens_from_settings


class StructuredDataDialog(QDialog):
    """Inspect, validate, and optionally apply structured-data transformations."""

    def __init__(self, parent, *, source_text: str, file_path: str | None) -> None:
        """Create the structured-data dialog and detect the most likely input mode."""
        super().__init__(parent)
        self._window = parent
        self._source_text = str(source_text or "")
        self._file_path = str(file_path or "")
        self._final_text = self._source_text
        self.setWindowTitle("Structured Data Tools")
        self.resize(1080, 720)
        self.setAccessibleName("Structured data tools dialog")
        self.setAccessibleDescription(
            "Validate, format, and preview structured text such as JSON, XML, CSV, and YAML."
        )
        tokens = build_tokens_from_settings(getattr(parent, "settings", {}))
        self.setStyleSheet(build_dialog_theme_qss_from_tokens(tokens))

        root = QVBoxLayout(self)
        intro = QLabel(
            "Choose the content type, review the structured preview, and apply formatting only when the result looks correct.",
            self,
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        top = QHBoxLayout()
        top.addWidget(QLabel("Content type:", self))
        self.kind_combo = QComboBox(self)
        self.kind_combo.addItems(["Auto", "JSON", "XML", "CSV", "YAML"])
        self.kind_combo.setAccessibleName("Content type selector")
        top.addWidget(self.kind_combo)
        top.addWidget(QLabel("CSV delimiter:", self))
        self.delimiter_combo = QComboBox(self)
        self.delimiter_combo.addItem("Comma (,)", ",")
        self.delimiter_combo.addItem("Semicolon (;)", ";")
        self.delimiter_combo.addItem("Tab", "\t")
        self.delimiter_combo.addItem("Pipe (|)", "|")
        self.delimiter_combo.setAccessibleName("CSV delimiter selector")
        top.addWidget(self.delimiter_combo)
        top.addStretch(1)
        root.addLayout(top)

        split = QSplitter(Qt.Horizontal, self)
        split.setChildrenCollapsible(False)
        root.addWidget(split, 1)

        left = QWidget(split)
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Structure / table preview", left))
        self.tree = QTreeWidget(left)
        self.tree.setHeaderLabels(["Name", "Value"])
        self.tree.setAccessibleName("Structured data tree preview")
        self.tree.setAccessibleDescription("Shows the parsed structure of JSON, XML, or YAML content.")
        self.table = QTableWidget(left)
        self.table.setAccessibleName("CSV table preview")
        self.table.setAccessibleDescription("Shows the parsed rows and columns for CSV content.")
        left_layout.addWidget(self.tree, 1)
        left_layout.addWidget(self.table, 1)

        right = QWidget(split)
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Formatted preview", right))
        self.preview = QTextEdit(right)
        self.preview.setReadOnly(True)
        self.preview.setAccessibleName("Formatted structured-data preview")
        self.preview.setAccessibleDescription("Shows formatted output or parser feedback for the selected content type.")
        right_layout.addWidget(self.preview, 1)
        self.summary = QLabel(right)
        self.summary.setWordWrap(True)
        self.summary.setObjectName("structuredDataSummary")
        self.summary.setAccessibleName("Validation summary")
        right_layout.addWidget(self.summary)
        split.setSizes([420, 620])

        buttons = QDialogButtonBox(self)
        self.apply_btn = buttons.addButton("Apply to Current Tab", QDialogButtonBox.AcceptRole)
        self.new_tab_btn = buttons.addButton("Open in New Tab", QDialogButtonBox.ActionRole)
        self.close_btn = buttons.addButton(QDialogButtonBox.Close)
        root.addWidget(buttons)

        self.kind_combo.currentTextChanged.connect(self._refresh)
        self.delimiter_combo.currentTextChanged.connect(self._refresh)
        self.apply_btn.clicked.connect(self.accept)
        self.new_tab_btn.clicked.connect(self._open_new_tab)
        self.close_btn.clicked.connect(self.reject)

        self.kind_combo.setCurrentText(self._detect_kind())
        self._refresh()

    @property
    def final_text(self) -> str:
        """Return the last successfully formatted text preview."""
        return self._final_text

    def _detect_kind(self) -> str:
        """Choose a sensible initial parser mode from the file path or content."""
        suffix = Path(self._file_path).suffix.lower()
        if suffix == ".json":
            return "JSON"
        if suffix == ".xml":
            return "XML"
        if suffix == ".csv":
            return "CSV"
        if suffix in {".yml", ".yaml"}:
            return "YAML"
        stripped = self._source_text.lstrip()
        if stripped.startswith("{") or stripped.startswith("["):
            return "JSON"
        if stripped.startswith("<"):
            return "XML"
        return "Auto"

    def _refresh(self) -> None:
        """Rebuild the preview panes based on the selected parser mode."""
        kind = self.kind_combo.currentText().strip().upper()
        if kind == "AUTO":
            kind = self._detect_kind().upper()
        self.tree.setVisible(kind != "CSV")
        self.table.setVisible(kind == "CSV")
        try:
            if kind == "JSON":
                self._show_json()
            elif kind == "XML":
                self._show_xml()
            elif kind == "CSV":
                self._show_csv()
            else:
                self._show_yaml_outline()
        except Exception as exc:  # noqa: BLE001
            self.summary.setText(f"Validation error: {exc}")
            self.preview.setPlainText(self._source_text)

    def _show_json(self) -> None:
        """Parse JSON into both tree and formatted-text previews."""
        payload = json.loads(self._source_text)
        self.tree.clear()
        self._fill_tree(self.tree.invisibleRootItem(), payload, "root")
        self._final_text = json.dumps(payload, indent=2, ensure_ascii=False)
        self.preview.setPlainText(self._final_text)
        self.summary.setText("JSON is valid and ready to format.")

    def _show_xml(self) -> None:
        """Parse XML, build a tree preview, and show pretty-printed text."""
        root = ET.fromstring(self._source_text)
        self.tree.clear()
        self._fill_xml_tree(self.tree.invisibleRootItem(), root)
        pretty = xml.dom.minidom.parseString(self._source_text.encode("utf-8")).toprettyxml(indent="  ")
        self._final_text = "\n".join(line for line in pretty.splitlines() if line.strip())
        self.preview.setPlainText(self._final_text)
        self.summary.setText("XML is valid and ready to format.")

    def _show_csv(self) -> None:
        """Parse CSV rows into a table preview and normalized text output."""
        delimiter = self.delimiter_combo.currentData()
        reader = list(csv.reader(io.StringIO(self._source_text), delimiter=str(delimiter or ",")))
        headers = reader[0] if reader else []
        rows = reader[1:] if len(reader) > 1 else []
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers or ["Column"])
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col_index, value in enumerate(row):
                self.table.setItem(row_index, col_index, QTableWidgetItem(value))
        self._final_text = self._source_text
        self.preview.setPlainText(self._source_text)
        self.summary.setText(f"CSV preview loaded with {len(rows)} data row(s).")

    def _show_yaml_outline(self) -> None:
        """Show a simple indentation-based YAML outline when no parser is bundled."""
        self.tree.clear()
        parent_stack: list[tuple[int, QTreeWidgetItem]] = []
        for raw_line in self._source_text.splitlines():
            if not raw_line.strip():
                continue
            indent = len(raw_line) - len(raw_line.lstrip(" "))
            item = QTreeWidgetItem([raw_line.strip(), ""])
            while parent_stack and parent_stack[-1][0] >= indent:
                parent_stack.pop()
            if parent_stack:
                parent_stack[-1][1].addChild(item)
            else:
                self.tree.addTopLevelItem(item)
            parent_stack.append((indent, item))
        self._final_text = self._source_text
        self.preview.setPlainText(self._source_text)
        self.summary.setText("YAML outline preview is available. Full validation requires a YAML parser dependency.")

    def _fill_tree(self, parent: QTreeWidgetItem, value, name: str) -> None:
        """Recursively map JSON-like values into a tree widget."""
        if isinstance(value, dict):
            node = QTreeWidgetItem([name, "object"])
            parent.addChild(node)
            for key, child in value.items():
                self._fill_tree(node, child, str(key))
            return
        if isinstance(value, list):
            node = QTreeWidgetItem([name, f"list ({len(value)})"])
            parent.addChild(node)
            for index, child in enumerate(value):
                self._fill_tree(node, child, f"[{index}]")
            return
        parent.addChild(QTreeWidgetItem([name, str(value)]))

    def _fill_xml_tree(self, parent: QTreeWidgetItem, element: ET.Element) -> None:
        """Recursively map XML elements into a readable tree structure."""
        text = (element.text or "").strip()
        node = QTreeWidgetItem([element.tag, text])
        parent.addChild(node)
        for key, value in element.attrib.items():
            node.addChild(QTreeWidgetItem([f"@{key}", value]))
        for child in list(element):
            self._fill_xml_tree(node, child)

    def _open_new_tab(self) -> None:
        """Open the formatted result in a new tab for safe review."""
        if hasattr(self._window, "add_new_tab"):
            self._window.add_new_tab(text=self._final_text, make_current=True)
            if hasattr(self._window, "show_status_message"):
                self._window.show_status_message("Opened structured-data result in a new tab.", 3000)
