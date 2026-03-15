"""Provide spellchecking helpers and state used by the text editor experience.

This module belongs to the editor widget and text-manipulation UI layer. It helps explain how `pypad.ui.editor`
is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

import re
from difflib import get_close_matches
from functools import lru_cache
from importlib import resources
from pathlib import Path

from pypad.app_settings.paths import get_spellcheck_dictionaries_dir_path
from pypad.ui.theme.asset_paths import resolve_asset_path

try:
    from hunspell import Hunspell
except Exception:  # noqa: BLE001
    Hunspell = None

try:
    from symspellpy import SymSpell, Verbosity
except Exception:  # noqa: BLE001
    SymSpell = None
    Verbosity = None


WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z'_-]{1,}\b")
SUPPORTED_SYMSPELL_LANGUAGES = {"en", "en-us"}
LANGUAGE_ALIASES = {
    "english": "en",
    "en": "en",
    "en-us": "en",
    "en_gb": "en-GB",
    "en-gb": "en-GB",
    "spanish": "es",
    "es": "es",
    "german": "de",
    "de": "de",
    "french": "fr",
    "fr": "fr",
    "italian": "it",
    "it": "it",
    "portuguese": "pt",
    "pt": "pt",
    "pt-br": "pt",
    "pt-pt": "pt-PT",
    "russian": "ru",
    "ru": "ru",
    "arabic": "ar",
    "ar": "ar",
    "japanese": "ja",
    "ja": "ja",
    "korean": "ko",
    "ko": "ko",
    "hindi": "hi",
    "hi": "hi",
    "chinese": "zh-cn",
    "simplified chinese": "zh-cn",
    "zh": "zh-cn",
    "zh-cn": "zh-cn",
}


class _SymSpellEngine:
    """Adapter around symspellpy matching the editor's spellcheck interface."""

    def __init__(self, language: str = "en") -> None:
        if SymSpell is None or Verbosity is None:
            raise RuntimeError("symspellpy is unavailable")
        normalized = str(language or "en").strip().lower() or "en"
        if normalized not in SUPPORTED_SYMSPELL_LANGUAGES:
            raise RuntimeError(f"symspellpy accelerator is unsupported for {normalized}")
        self.language = normalized
        self._symspell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
        dictionary_path = self._dictionary_path_for_language("en")
        if dictionary_path is None or not self._symspell.load_dictionary(str(dictionary_path), 0, 1):
            raise RuntimeError("Unable to load symspellpy English dictionary")
        self._dictionary_words = {str(word).strip().lower() for word in self._symspell.words.keys() if str(word).strip()}

    @staticmethod
    def _dictionary_path_for_language(language: str):
        try:
            path = resources.files("symspellpy").joinpath(f"frequency_dictionary_{language}_82_765.txt")
            if path.is_file():
                return path
        except Exception:
            return None
        return None

    @property
    def word_frequency(self):
        return type("_WordFrequency", (), {"dictionary": self._dictionary_words})()

    def unknown(self, words) -> set[str]:
        out: set[str] = set()
        for raw in words:
            word = str(raw or "").strip().lower()
            if word and word not in self._dictionary_words:
                out.add(word)
        return out

    def candidates(self, word: str):
        probe = str(word or "").strip()
        if not probe:
            return []
        suggestions = self._symspell.lookup(
            probe,
            Verbosity.CLOSEST,
            max_edit_distance=2,
            include_unknown=False,
            transfer_casing=False,
        )
        return [item.term for item in suggestions if str(getattr(item, "term", "")).strip()]

    def correction(self, word: str):
        suggestions = self.candidates(word)
        return suggestions[0] if suggestions else ""


class _HunspellEngine:
    """Adapter around chunspell's Hunspell object."""

    def __init__(self, language: str = "en") -> None:
        if Hunspell is None:
            raise RuntimeError("chunspell is unavailable")
        self.language = _normalize_language(language)
        dictionary_dir = _find_hunspell_data_dir(self.language)
        self._dictionary_words = _load_dictionary_wordlist(self.language, dictionary_dir)
        kwargs = {"system_encoding": "UTF-8"}
        if dictionary_dir is None and self.language == "en":
            self._engine = Hunspell(**kwargs)
        elif dictionary_dir is not None:
            self._engine = Hunspell(self.language, hunspell_data_dir=str(dictionary_dir), **kwargs)
        else:
            raise RuntimeError(f"No Hunspell dictionary found for {self.language}")

    @property
    def word_frequency(self):
        return type("_WordFrequency", (), {"dictionary": self._dictionary_words})()

    def unknown(self, words) -> set[str]:
        out: set[str] = set()
        for raw in words:
            word = str(raw or "").strip().lower()
            if word and not self._safe_spell(word):
                out.add(word)
        return out

    def candidates(self, word: str):
        probe = str(word or "").strip()
        if not probe:
            return []
        try:
            raw = self._engine.suggest(probe)
        except Exception:
            raw = []
        return [str(item).strip() for item in raw if str(item).strip()]

    def correction(self, word: str):
        suggestions = self.candidates(word)
        return suggestions[0] if suggestions else ""

    def _safe_spell(self, word: str) -> bool:
        try:
            return bool(self._engine.spell(word))
        except Exception:
            return False


def _normalize_language(language: str) -> str:
    """Normalize a user-provided language to the canonical bundled dictionary name."""
    normalized = str(language or "en").strip().lower().replace("_", "-") or "en"
    if normalized in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[normalized]
    return normalized


def _candidate_dictionary_dirs() -> list[Path]:
    """Return directories that may contain Hunspell dictionaries."""
    out: list[Path] = []
    configured = get_spellcheck_dictionaries_dir_path()
    out.append(configured)
    bundled = resolve_asset_path("dictionaries")
    if bundled is not None and bundled not in out:
        out.append(bundled)
    return out


def _find_hunspell_data_dir(language: str) -> Path | None:
    """Locate the directory containing `.aff` and `.dic` files for a Hunspell language."""
    normalized = _normalize_language(language)
    for directory in _candidate_dictionary_dirs():
        direct_aff = directory / f"{normalized}.aff"
        direct_dic = directory / f"{normalized}.dic"
        if direct_aff.exists() and direct_dic.exists():
            return directory
        for variant in _dictionary_name_candidates(normalized):
            nested = directory / variant
            aff = nested / "index.aff"
            dic = nested / "index.dic"
            if aff.exists() and dic.exists():
                return nested
    return None


def _load_dictionary_wordlist(language: str, directory: Path | None) -> list[str]:
    """Load base dictionary words from a Hunspell `.dic` file for fallback matching."""
    if directory is None:
        return []
    path = _dictionary_file_path(language, directory, "dic")
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            rows = [line.strip() for line in handle]
    except OSError:
        return []
    if rows and rows[0].isdigit():
        rows = rows[1:]
    out: list[str] = []
    for row in rows:
        head = row.split("/", 1)[0].strip()
        if head:
            out.append(head)
    return out


def _dictionary_name_candidates(language: str) -> list[str]:
    """Return likely directory names for bundled dictionary packs."""
    normalized = _normalize_language(language)
    out = [normalized]
    if "_" in normalized:
        out.append(normalized.replace("_", "-"))
    if "-" in normalized:
        out.append(normalized.replace("-", "_"))
    base = normalized.split("-", 1)[0].split("_", 1)[0]
    if base not in out:
        out.append(base)
    seen: set[str] = set()
    deduped: list[str] = []
    for item in out:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _dictionary_file_path(language: str, directory: Path, extension: str) -> Path:
    """Resolve the concrete dictionary file path inside a matched dictionary directory."""
    normalized = _normalize_language(language)
    direct = directory / f"{normalized}.{extension}"
    if direct.exists():
        return direct
    index_path = directory / f"index.{extension}"
    if index_path.exists():
        return index_path
    return direct


@lru_cache(maxsize=4)
def _english_spell_engine():
    """Build the English spell engine, preferring symspellpy for speed."""
    try:
        return _SymSpellEngine(language="en")
    except Exception:
        pass
    try:
        return _HunspellEngine(language="en")
    except Exception:
        return None


@lru_cache(maxsize=8)
def _spellchecker_for_language(language: str):
    """Spellchecker for language."""
    normalized = _normalize_language(language)
    if normalized == "en":
        return _english_spell_engine()
    try:
        return _HunspellEngine(language=normalized)
    except Exception:
        return _english_spell_engine()


def spellcheck_available() -> bool:
    """Spellcheck available."""
    return SymSpell is not None or Hunspell is not None


def iter_words(text: str) -> list[tuple[str, int, int]]:
    """Iter words."""
    rows: list[tuple[str, int, int]] = []
    for match in WORD_RE.finditer(str(text or "")):
        rows.append((match.group(0), match.start(), match.end()))
    return rows


def word_span_at(text: str, index: int) -> tuple[str, int, int] | None:
    """Word span at."""
    probe = str(text or "")
    cursor = max(0, min(len(probe), int(index)))
    for word, start, end in iter_words(probe):
        if start <= cursor <= end:
            return word, start, end
    return None


def _dictionary_words(engine) -> list[str]:
    """Dictionary words."""
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


def _apply_word_case(template: str, suggestion: str) -> str:
    """Apply the input word's capitalization pattern to a suggestion."""
    probe = str(template or "").strip()
    candidate = str(suggestion or "").strip()
    if not probe or not candidate:
        return candidate
    if probe.isupper():
        return candidate.upper()
    if probe.islower():
        return candidate.lower()
    if len(probe) > 1 and probe[:1].isupper() and probe[1:].islower():
        return candidate[:1].upper() + candidate[1:].lower()
    return candidate


def _safe_candidates(engine, word: str) -> list[str]:
    """Safe candidates."""
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
        normalized = _apply_word_case(word, item.strip())
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
