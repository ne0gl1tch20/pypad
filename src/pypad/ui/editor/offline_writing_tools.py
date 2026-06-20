"""Offline grammar review, paraphrase, and humanize helpers for local writing workflows."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
import importlib
import re
import threading
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    import language_tool_python
except Exception:  # pragma: no cover - optional dependency
    language_tool_python = None


_LANGUAGE_TOOL_LOCK = threading.Lock()
_LANGUAGE_TOOL_CACHE: dict[str, Any] = {}


_WEAK_PHRASES: dict[str, str] = {
    "in order to": "to",
    "due to the fact that": "because",
    "at this point in time": "now",
    "has the ability to": "can",
    "for the purpose of": "for",
    "it is important to note that": "",
    "it should be noted that": "",
}

_HUMANIZER_SWAPS: tuple[tuple[str, str], ...] = (
    ("utilize", "use"),
    ("commence", "start"),
    ("therefore", "so"),
    ("however", "but"),
    ("furthermore", "also"),
    ("moreover", "besides"),
    ("individuals", "people"),
    ("numerous", "many"),
    ("demonstrate", "show"),
    ("obtain", "get"),
)

_PARAPHRASE_SWAPS: tuple[tuple[str, str], ...] = (
    ("important", "key"),
    ("help", "support"),
    ("show", "demonstrate"),
    ("start", "begin"),
    ("end", "finish"),
    ("improve", "strengthen"),
    ("change", "adjust"),
    ("use", "apply"),
)


@dataclass(slots=True)
class WritingSuggestion:
    """Represent one local writing suggestion."""

    category: str
    message: str
    start: int
    end: int
    replacement: str = ""
    severity: str = "info"


@dataclass(slots=True)
class WritingAnalysis:
    """Represent a full analysis payload."""

    suggestions: list[WritingSuggestion]
    ai_score: int
    ai_signals: list[str]
    stats: dict[str, int]
    grammar_backend: str = "rule-based"
    grammar_backend_status: str = ""


def offline_writing_tools_available() -> bool:
    """Return whether the offline writing tools can run."""
    return True


def supports_language_tool() -> bool:
    """Return whether the optional local grammar backend is installed."""
    return language_tool_python is not None


def refresh_language_tool_support() -> bool:
    """Refresh the optional LanguageTool import after runtime installation."""
    global language_tool_python
    try:
        language_tool_python = importlib.import_module("language_tool_python")
    except Exception:
        language_tool_python = None
    return language_tool_python is not None


def get_or_create_language_tool(language: str):
    """Return a cached local LanguageTool instance for the requested language."""
    if language_tool_python is None:
        raise RuntimeError("language_tool_python is unavailable.")
    with _LANGUAGE_TOOL_LOCK:
        tool = _LANGUAGE_TOOL_CACHE.get(language)
        if tool is None:
            tool = language_tool_python.LanguageTool(language)
            _LANGUAGE_TOOL_CACHE[language] = tool
    return tool


def warm_language_tool(language: str, *, timeout_sec: float = 8.0) -> tuple[bool, str]:
    """Warm the optional LanguageTool backend with a timeout so UI flows fail open."""
    if language_tool_python is None:
        return False, "language_tool_python is unavailable."
    timeout = max(0.5, float(timeout_sec or 8.0))
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="lt-warmup") as executor:
        future = executor.submit(get_or_create_language_tool, language)
        try:
            future.result(timeout=timeout)
        except FuturesTimeoutError:
            return False, f"Local LanguageTool initialization exceeded {timeout:.1f}s."
        except Exception as exc:
            return False, str(exc) or "Local LanguageTool initialization failed."
    return True, ""


def _stats(text: str) -> dict[str, int]:
    words = re.findall(r"\b[\w'-]+\b", text)
    sentences = [part for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part]
    return {
        "chars": len(text),
        "words": len(words),
        "sentences": len(sentences),
        "paragraphs": len([part for part in re.split(r"\n\s*\n", text) if part.strip()]),
    }


def _iter_phrase_matches(text: str, phrase: str):
    return re.finditer(rf"\b{re.escape(phrase)}\b", text, flags=re.IGNORECASE)


def _rule_based_suggestions(text: str, settings: dict[str, Any] | None = None) -> list[WritingSuggestion]:
    config = settings or {}
    suggestions: list[WritingSuggestion] = []
    if bool(config.get("writing_tools_detect_repeated_words", True)):
        for match in re.finditer(r"\b(\w+)\s+(\1)\b", text, flags=re.IGNORECASE):
            suggestions.append(
                WritingSuggestion(
                    category="grammar",
                    message="Repeated word.",
                    start=match.start(2),
                    end=match.end(2),
                    replacement="",
                    severity="warning",
                )
            )
    if bool(config.get("writing_tools_detect_spacing", True)):
        for match in re.finditer(r"[ \t]{2,}", text):
            suggestions.append(
                WritingSuggestion(
                    category="clarity",
                    message="Extra spacing.",
                    start=match.start(),
                    end=match.end(),
                    replacement=" ",
                    severity="info",
                )
            )
    if bool(config.get("writing_tools_detect_capitalization", True)):
        for match in re.finditer(r"(^|[.!?]\s+)([a-z])", text):
            start = match.start(2)
            end = match.end(2)
            suggestions.append(
                WritingSuggestion(
                    category="grammar",
                    message="Sentence may need capitalization.",
                    start=start,
                    end=end,
                    replacement=text[start:end].upper(),
                    severity="warning",
                )
            )
    if bool(config.get("writing_tools_detect_weak_phrases", True)):
        for phrase, replacement in _WEAK_PHRASES.items():
            for match in _iter_phrase_matches(text, phrase):
                suggestions.append(
                    WritingSuggestion(
                        category="style",
                        message=f"Consider simplifying '{match.group(0)}'.",
                        start=match.start(),
                        end=match.end(),
                        replacement=replacement,
                        severity="info",
                    )
                )
    return suggestions


def _language_tool_suggestions(text: str, language: str) -> list[WritingSuggestion]:
    if language_tool_python is None:
        return []
    try:
        tool = get_or_create_language_tool(language)
    except Exception:
        return []
    try:
        matches = tool.check(text)
    except Exception:
        return []
    rows: list[WritingSuggestion] = []
    for match in matches[:200]:
        replacement = ""
        repls = getattr(match, "replacements", None) or []
        if repls:
            replacement = str(repls[0])
        rows.append(
            WritingSuggestion(
                category="grammar",
                message=str(getattr(match, "message", "Grammar suggestion.")),
                start=int(getattr(match, "offset", 0)),
                end=int(getattr(match, "offset", 0)) + int(getattr(match, "errorLength", 0)),
                replacement=replacement,
                severity="warning",
            )
        )
    return rows


def analyze_writing(text: str, *, settings: dict[str, Any] | None = None, language: str = "en-US") -> WritingAnalysis:
    """Analyze text with local grammar/style rules and heuristic AI-likeness scoring."""
    probe = str(text or "")
    stats = _stats(probe)
    suggestions = _rule_based_suggestions(probe, settings)
    grammar_backend = "rule-based"
    grammar_backend_status = ""
    if bool((settings or {}).get("writing_tools_use_language_tool", True)):
        suggestions.extend(_language_tool_suggestions(probe, language))
        if supports_language_tool():
            grammar_backend = "language-tool"
    ai_score, ai_signals = estimate_ai_likelihood(probe, settings=settings)
    suggestions.sort(key=lambda row: (row.start, row.end, row.category))
    return WritingAnalysis(
        suggestions=suggestions,
        ai_score=ai_score,
        ai_signals=ai_signals,
        stats=stats,
        grammar_backend=grammar_backend,
        grammar_backend_status=grammar_backend_status,
    )


def estimate_ai_likelihood(text: str, *, settings: dict[str, Any] | None = None) -> tuple[int, list[str]]:
    """Return a heuristic AI-likeness score with explanatory signals."""
    probe = str(text or "")
    config = settings or {}
    if not probe.strip():
        return 0, ["No text to score."]
    signals: list[str] = []
    score = 0.0
    words = re.findall(r"\b[\w'-]+\b", probe.lower())
    unique_ratio = (len(set(words)) / len(words)) if words else 0.0
    avg_sentence_words = (len(words) / max(1, len(re.split(r"(?<=[.!?])\s+", probe.strip()))))
    if avg_sentence_words > float(config.get("writing_tools_ai_sentence_threshold", 24)):
        score += 22
        signals.append("Long average sentence length.")
    if unique_ratio < float(config.get("writing_tools_ai_unique_ratio_threshold", 0.42)):
        score += 18
        signals.append("Low vocabulary variation.")
    bulletish = len(re.findall(r"^\s*[-*]\s+", probe, flags=re.MULTILINE))
    if bulletish >= 4:
        score += 12
        signals.append("List-heavy structure.")
    transitions = len(re.findall(r"\b(furthermore|moreover|therefore|however|additionally|overall)\b", probe, flags=re.IGNORECASE))
    if transitions >= 3:
        score += 18
        signals.append("Frequent formal transition words.")
    if re.search(r"\bin conclusion\b|\bin summary\b|\boverall\b", probe, flags=re.IGNORECASE):
        score += 10
        signals.append("Formulaic summary phrasing.")
    if len(re.findall(r"[!?]", probe)) == 0 and len(words) > 120:
        score += 8
        signals.append("Very even punctuation profile.")
    sensitivity = max(0.5, min(1.5, float(config.get("writing_tools_ai_detector_sensitivity", 1.0) or 1.0)))
    final_score = max(0, min(100, int(round(score * sensitivity))))
    if not signals:
        signals.append("No strong automated-writing signals.")
    return final_score, signals


def paraphrase_text(text: str, *, strength: int = 1, settings: dict[str, Any] | None = None) -> str:
    """Apply lightweight local paraphrasing transforms."""
    out = str(text or "")
    config = settings or {}
    swaps = list(_PARAPHRASE_SWAPS)
    if bool(config.get("writing_tools_detect_weak_phrases", True)):
        swaps.extend(_WEAK_PHRASES.items())
    for _ in range(max(1, strength)):
        for old, new in swaps:
            out = re.sub(rf"\b{re.escape(old)}\b", new, out, flags=re.IGNORECASE)
    if bool(config.get("writing_tools_paraphrase_reduce_passive", True)):
        out = re.sub(r"\bwas able to\b", "could", out, flags=re.IGNORECASE)
        out = re.sub(r"\bis being\b", "is", out, flags=re.IGNORECASE)
    return _clean_transform_output(out)


def humanize_text(text: str, *, strength: int = 1, settings: dict[str, Any] | None = None) -> str:
    """Rewrite text toward plainer, less formal language."""
    out = str(text or "")
    config = settings or {}
    for _ in range(max(1, strength)):
        for old, new in _HUMANIZER_SWAPS:
            out = re.sub(rf"\b{re.escape(old)}\b", new, out, flags=re.IGNORECASE)
        out = re.sub(r"\bdo not\b", "don't", out, flags=re.IGNORECASE)
        out = re.sub(r"\bcannot\b", "can't", out, flags=re.IGNORECASE)
        out = re.sub(r"\bit is\b", "it's", out, flags=re.IGNORECASE)
    if bool(config.get("writing_tools_humanizer_break_long_sentences", True)):
        out = re.sub(r",\s+(and|but)\s+", ". \\1 ", out)
    return _clean_transform_output(out)


def apply_suggestion(text: str, suggestion: WritingSuggestion) -> str:
    """Apply one suggestion replacement to text."""
    if suggestion.start < 0 or suggestion.end < suggestion.start:
        return text
    return f"{text[:suggestion.start]}{suggestion.replacement}{text[suggestion.end:]}"


def _clean_transform_output(text: str) -> str:
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() if text.strip() else text


class OfflineWritingStudioWidget(QWidget):
    """Reusable Offline Writing Studio surface for dialogs or tool tabs."""

    apply_requested = Signal(str)

    def __init__(
        self,
        analysis: WritingAnalysis,
        source_text: str,
        *,
        target_is_selection: bool,
        settings: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._analysis = analysis
        self._source_text = str(source_text or "")
        self._target_is_selection = bool(target_is_selection)
        self._settings = settings or {}

        layout = QVBoxLayout(self)
        summary = QLabel(self)
        backend_name = str(getattr(analysis, "grammar_backend", "rule-based") or "rule-based")
        backend_label = "LanguageTool local grammar enabled" if backend_name == "language-tool" else "Rule-based grammar only"
        backend_status = str(getattr(analysis, "grammar_backend_status", "") or "").strip()
        summary.setText(
            f"Scope: {'Selection' if self._target_is_selection else 'Document'} | "
            f"Words: {analysis.stats['words']} | Suggestions: {len(analysis.suggestions)} | "
            f"AI-likeness: {analysis.ai_score}/100 | {backend_label}"
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)
        if backend_status:
            backend_note = QLabel(backend_status, self)
            backend_note.setWordWrap(True)
            backend_note.setProperty("status", "warning")
            layout.addWidget(backend_note)

        transform_row = QHBoxLayout()
        self.mode_combo = QComboBox(self)
        self.mode_combo.addItems(["Analyze only", "Paraphrase", "Humanize"])
        self.strength_spin = QSpinBox(self)
        self.strength_spin.setRange(1, 3)
        self.strength_spin.setValue(1)
        transform_row.addWidget(QLabel("Transform", self))
        transform_row.addWidget(self.mode_combo)
        transform_row.addWidget(QLabel("Strength", self))
        transform_row.addWidget(self.strength_spin)
        transform_row.addStretch(1)
        layout.addLayout(transform_row)

        panes = QSplitter(Qt.Horizontal, self)
        left = QWidget(panes)
        left_layout = QVBoxLayout(left)
        self.suggestion_list = QListWidget(left)
        for row in analysis.suggestions:
            item = QListWidgetItem(f"[{row.category}] {row.message}")
            item.setData(Qt.ItemDataRole.UserRole, row)
            self.suggestion_list.addItem(item)
        left_layout.addWidget(QLabel("Suggestions", left))
        left_layout.addWidget(self.suggestion_list, 1)
        self.signals_view = QTextEdit(left)
        self.signals_view.setReadOnly(True)
        self.signals_view.setPlainText("\n".join(f"- {row}" for row in analysis.ai_signals))
        left_layout.addWidget(QLabel("AI detector signals", left))
        left_layout.addWidget(self.signals_view, 1)

        right = QWidget(panes)
        right_layout = QVBoxLayout(right)
        self.original_view = QTextEdit(right)
        self.original_view.setReadOnly(True)
        self.original_view.setPlainText(self._source_text)
        self.preview_view = QTextEdit(right)
        self.preview_view.setPlainText(self._source_text)
        right_layout.addWidget(QLabel("Original", right))
        right_layout.addWidget(self.original_view, 1)
        right_layout.addWidget(QLabel("Preview", right))
        right_layout.addWidget(self.preview_view, 1)
        panes.addWidget(left)
        panes.addWidget(right)
        panes.setStretchFactor(0, 0)
        panes.setStretchFactor(1, 1)
        layout.addWidget(panes, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, Qt.Horizontal, self)
        self.apply_suggestion_btn = buttons.addButton("Apply Suggestion", QDialogButtonBox.ActionRole)
        self.apply_preview_btn = buttons.addButton("Apply Preview", QDialogButtonBox.AcceptRole)
        layout.addWidget(buttons)

        self.mode_combo.currentTextChanged.connect(lambda _text: self.refresh())
        self.strength_spin.valueChanged.connect(lambda _value: self.refresh())
        self.suggestion_list.itemDoubleClicked.connect(lambda _item: self.apply_selected_suggestion())
        self.apply_suggestion_btn.clicked.connect(self.apply_selected_suggestion)
        self.apply_preview_btn.clicked.connect(self._emit_apply_preview)
        buttons.rejected.connect(self.close_requested)

        self.refresh()

    def refresh(self) -> None:
        """Refresh the preview text for the current transform settings."""
        mode = self.mode_combo.currentText()
        strength = int(self.strength_spin.value())
        if mode == "Paraphrase":
            self.preview_view.setPlainText(paraphrase_text(self._source_text, strength=strength, settings=self._settings))
        elif mode == "Humanize":
            self.preview_view.setPlainText(humanize_text(self._source_text, strength=strength, settings=self._settings))
        else:
            self.preview_view.setPlainText(self._source_text)

    def apply_selected_suggestion(self) -> None:
        """Apply the currently selected suggestion into the preview pane."""
        item = self.suggestion_list.currentItem()
        if item is None:
            return
        suggestion = item.data(Qt.ItemDataRole.UserRole)
        if suggestion is None:
            return
        self.preview_view.setPlainText(apply_suggestion(self.preview_view.toPlainText(), suggestion))

    def _emit_apply_preview(self) -> None:
        """Emit the current preview text so the owner can commit it into the editor."""
        self.apply_requested.emit(self.preview_view.toPlainText())

    def close_requested(self) -> None:
        """Handle Close button presses in embedded mode."""
        window = self.window()
        if window is not None and hasattr(window, "close"):
            window.close()
