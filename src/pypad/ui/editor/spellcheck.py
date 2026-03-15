"""Provide spellchecking helpers and state used by the text editor experience.

This module belongs to the editor widget and text-manipulation UI layer. It helps explain how `pypad.ui.editor` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

import re
from difflib import get_close_matches
from functools import lru_cache

try:
    from spellchecker import SpellChecker
except Exception:  # noqa: BLE001
    SpellChecker = None


WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z'_-]{1,}\b")


def iter_words(text: str) -> list[tuple[str, int, int]]:
    """Handle iter words."""
    rows: list[tuple[str, int, int]] = []
    for match in WORD_RE.finditer(str(text or "")):
        rows.append((match.group(0), match.start(), match.end()))
    return rows


def word_span_at(text: str, index: int) -> tuple[str, int, int] | None:
    """Handle word span at."""
    probe = str(text or "")
    cursor = max(0, min(len(probe), int(index)))
    for word, start, end in iter_words(probe):
        if start <= cursor <= end:
            return word, start, end
    return None


@lru_cache(maxsize=8)
def _spellchecker_for_language(language: str):
    """Handle spellchecker for language."""
    if SpellChecker is None:
        return None
    normalized = str(language or "en").strip().lower() or "en"
    try:
        return SpellChecker(language=normalized)
    except Exception:
        try:
            return SpellChecker(language="en")
        except Exception:
            return None


def spellcheck_available() -> bool:
    """Handle spellcheck available."""
    return SpellChecker is not None


def _dictionary_words(engine) -> list[str]:
    """Handle dictionary words."""
    word_frequency = getattr(engine, "word_frequency", None)
    if word_frequency is None:
        return []
    for attr_name in ("dictionary", "_dictionary", "words"):
        raw = getattr(word_frequency, attr_name, None)
        if raw is None:
            continue
        try:
            if callable(raw):
                raw = raw()
            if isinstance(raw, dict):
                words = raw.keys()
            else:
                words = raw
            return [str(item).strip() for item in words if str(item).strip()]
        except Exception:
            continue
    return []


def _safe_candidates(engine, word: str) -> list[str]:
    """Handle safe candidates."""
    try:
        raw = engine.candidates(word)
    except Exception:
        raw = None
    out: list[str] = []
    if raw is not None:
        try:
            out.extend(str(item) for item in raw if str(item).strip())
        except Exception:
            pass
    if not out:
        try:
            fallback = str(engine.correction(word) or "").strip()
        except Exception:
            fallback = ""
        if fallback and fallback.lower() != str(word or "").strip().lower():
            out.append(fallback)
    if not out:
        try:
            out.extend(
                get_close_matches(
                    str(word or "").strip().lower(),
                    _dictionary_words(engine),
                    n=8,
                    cutoff=0.5,
                )
            )
        except Exception:
            pass
    deduped: list[str] = []
    seen: set[str] = set()
    for item in out:
        normalized = item.strip()
        if not normalized:
            continue
        folded = normalized.lower()
        if folded in seen:
            continue
        seen.add(folded)
        deduped.append(normalized)
        if len(deduped) >= 8:
            break
    return deduped


def unknown_words(
    text: str,
    *,
    language: str = "en",
    custom_words: list[str] | set[str] | tuple[str, ...] | None = None,
) -> list[dict[str, object]]:
    """Return misspelled words and their positions for the requested language."""
    engine = _spellchecker_for_language(language)
    if engine is None:
        return []
    custom = {str(word).strip().lower() for word in (custom_words or []) if str(word).strip()}
    rows = iter_words(text)
    unique = sorted({word.lower() for word, _start, _end in rows if word.lower() not in custom})
    unknown = set(engine.unknown(unique))
    out: list[dict[str, object]] = []
    for word, start, end in rows:
        folded = word.lower()
        if folded in custom or folded not in unknown:
            continue
        out.append(
            {
                "word": word,
                "start": int(start),
                "end": int(end),
                "suggestions": _safe_candidates(engine, word),
            }
        )
    return out


def suggestions_for_word(
    word: str,
    *,
    language: str = "en",
    custom_words: list[str] | set[str] | tuple[str, ...] | None = None,
) -> list[str]:
    """Return spelling suggestions for a single word in the requested language."""
    engine = _spellchecker_for_language(language)
    probe = str(word or "").strip()
    if engine is None or not probe:
        return []
    folded = probe.lower()
    custom = {str(item).strip().lower() for item in (custom_words or []) if str(item).strip()}
    if folded in custom:
        return []
    return _safe_candidates(engine, probe)
