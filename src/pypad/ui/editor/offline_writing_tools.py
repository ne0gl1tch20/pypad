"""Offline grammar review, paraphrase, and humanize helpers for local writing workflows."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import re
import threading
from typing import Any

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
    if bool((settings or {}).get("writing_tools_use_language_tool", True)):
        suggestions.extend(_language_tool_suggestions(probe, language))
    ai_score, ai_signals = estimate_ai_likelihood(probe, settings=settings)
    suggestions.sort(key=lambda row: (row.start, row.end, row.category))
    return WritingAnalysis(suggestions=suggestions, ai_score=ai_score, ai_signals=ai_signals, stats=stats)


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
