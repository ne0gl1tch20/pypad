"""Audit Scintilla compatibility behavior and expose diagnostic helpers for parity tracking.

This module belongs to the Scintilla compatibility layer used when native QScintilla is unavailable. It helps explain how `pypad.ui.editor.scintilla_compat` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable


_SYMBOL_PATTERN = re.compile(r"\b(?:SCI|SCN|SC|INDIC)_[A-Z0-9_]+\b")
_COMPAT_CUSTOM_ID_PATTERN = re.compile(
    r"^\s*(SCI_[A-Z0-9_]+)\s*=\s*(31\d{3})\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class ScintillaCompatAuditReport:
    """Represent the scintilla compat audit report."""
    compat_symbols: frozenset[str]
    repo_symbols: frozenset[str]
    repo_missing: tuple[str, ...]
    app_exclusive_symbols: tuple[str, ...]
    native_symbols: frozenset[str]
    native_missing: tuple[str, ...]

    @property
    def repo_complete(self) -> bool:
        """Repo complete."""
        return not self.repo_missing

    @property
    def native_complete(self) -> bool:
        """Native complete."""
        return bool(self.native_symbols) and not self.native_missing


@dataclass(frozen=True)
class NativeQsciBaseline:
    """Represent the native qsci baseline."""
    generated_at: str
    symbol_count: int
    symbols: tuple[str, ...]


@dataclass(frozen=True)
class ScintillaCompatContractBaseline:
    """Represent the scintilla compat contract baseline."""
    generated_at: str
    compat_symbol_count: int
    compat_symbols: tuple[str, ...]
    app_exclusive_symbols: tuple[str, ...]


def _repo_root() -> Path:
    """Repo root."""
    return Path(__file__).resolve().parents[5]


def _iter_python_files(paths: Iterable[Path]) -> Iterable[Path]:
    """Iter python files."""
    for root in paths:
        if not root.exists():
            continue
        yield from root.rglob("*.py")


def _extract_symbols(text: str) -> frozenset[str]:
    """Extract symbols."""
    return frozenset(_SYMBOL_PATTERN.findall(text))


def load_compat_symbols() -> frozenset[str]:
    """Load the Scintilla compatibility symbol list from its baseline file."""
    editor_path = Path(__file__).resolve().parent / "editor.py"
    return _extract_symbols(editor_path.read_text(encoding="utf-8"))


def load_repo_symbols(root: Path | None = None) -> frozenset[str]:
    """Load the repository symbol list used by the audit tool."""
    root = root or _repo_root()
    found: set[str] = set()
    for path in _iter_python_files((root / "src", root / "tests")):
        if path.name in {"metadata.py", "audit.py"} and path.parent.name == "scintilla_compat":
            continue
        try:
            found.update(_extract_symbols(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return frozenset(found)


def load_app_exclusive_symbols() -> tuple[str, ...]:
    """Load the symbol list that exists only in the application compatibility layer."""
    editor_path = Path(__file__).resolve().parent / "editor.py"
    text = editor_path.read_text(encoding="utf-8")
    names = sorted({name for name, _value in _COMPAT_CUSTOM_ID_PATTERN.findall(text)})
    return tuple(names)


def load_native_qsci_symbols() -> frozenset[str]:
    """Load the native QScintilla symbol list used for comparison."""
    try:
        from PySide6.Qsci import QsciScintilla  # type: ignore
    except Exception:
        return frozenset()
    return frozenset(
        name
        for name in dir(QsciScintilla)
        if name.startswith(("SCI_", "SCN_", "SC_", "INDIC_"))
    )


def build_audit_report(root: Path | None = None) -> ScintillaCompatAuditReport:
    """Build audit report."""
    compat_symbols = load_compat_symbols()
    repo_symbols = load_repo_symbols(root)
    native_symbols = load_native_qsci_symbols()
    repo_missing = tuple(sorted(repo_symbols - compat_symbols))
    native_missing = tuple(sorted(native_symbols - compat_symbols))
    return ScintillaCompatAuditReport(
        compat_symbols=compat_symbols,
        repo_symbols=repo_symbols,
        repo_missing=repo_missing,
        app_exclusive_symbols=load_app_exclusive_symbols(),
        native_symbols=native_symbols,
        native_missing=native_missing,
    )


def native_baseline_path(root: Path | None = None) -> Path:
    """Native baseline path."""
    root = root or _repo_root()
    return root / "docs" / "scintilla_native_qsci_baseline.json"


def contract_baseline_path(root: Path | None = None) -> Path:
    """Contract baseline path."""
    root = root or _repo_root()
    return root / "docs" / "scintilla_compat_contract_baseline.json"


def save_native_baseline(root: Path | None = None) -> Path:
    """Save the native QScintilla symbol baseline to disk."""
    from datetime import datetime, UTC

    root = root or _repo_root()
    symbols = tuple(sorted(load_native_qsci_symbols()))
    if not symbols:
        raise RuntimeError("PySide6.Qsci is not available in this environment.")
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "symbol_count": len(symbols),
        "symbols": list(symbols),
    }
    path = native_baseline_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_native_baseline(root: Path | None = None) -> NativeQsciBaseline | None:
    """Load the saved native QScintilla symbol baseline from disk."""
    path = native_baseline_path(root)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    symbols = tuple(str(item) for item in payload.get("symbols", []))
    return NativeQsciBaseline(
        generated_at=str(payload.get("generated_at", "")),
        symbol_count=int(payload.get("symbol_count", len(symbols))),
        symbols=symbols,
    )


def save_contract_baseline(root: Path | None = None) -> Path:
    """Save the compatibility contract baseline to disk."""
    from datetime import UTC, datetime

    root = root or _repo_root()
    compat_symbols = tuple(sorted(load_compat_symbols()))
    app_exclusive_symbols = load_app_exclusive_symbols()
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "compat_symbol_count": len(compat_symbols),
        "compat_symbols": list(compat_symbols),
        "app_exclusive_symbols": list(app_exclusive_symbols),
    }
    path = contract_baseline_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_contract_baseline(root: Path | None = None) -> ScintillaCompatContractBaseline | None:
    """Load the saved compatibility contract baseline from disk."""
    path = contract_baseline_path(root)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    compat_symbols = tuple(str(item) for item in payload.get("compat_symbols", []))
    app_exclusive_symbols = tuple(str(item) for item in payload.get("app_exclusive_symbols", []))
    return ScintillaCompatContractBaseline(
        generated_at=str(payload.get("generated_at", "")),
        compat_symbol_count=int(payload.get("compat_symbol_count", len(compat_symbols))),
        compat_symbols=compat_symbols,
        app_exclusive_symbols=app_exclusive_symbols,
    )
