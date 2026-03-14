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
    """Class that implements the `ScintillaCompatAuditReport` runtime behavior."""
    compat_symbols: frozenset[str]
    repo_symbols: frozenset[str]
    repo_missing: tuple[str, ...]
    app_exclusive_symbols: tuple[str, ...]
    native_symbols: frozenset[str]
    native_missing: tuple[str, ...]

    @property
    def repo_complete(self) -> bool:
        """Execute the `repo_complete` workflow."""
        return not self.repo_missing

    @property
    def native_complete(self) -> bool:
        """Execute the `native_complete` workflow."""
        return bool(self.native_symbols) and not self.native_missing


@dataclass(frozen=True)
class NativeQsciBaseline:
    """Class that implements the `NativeQsciBaseline` runtime behavior."""
    generated_at: str
    symbol_count: int
    symbols: tuple[str, ...]


@dataclass(frozen=True)
class ScintillaCompatContractBaseline:
    """Class that implements the `ScintillaCompatContractBaseline` runtime behavior."""
    generated_at: str
    compat_symbol_count: int
    compat_symbols: tuple[str, ...]
    app_exclusive_symbols: tuple[str, ...]


def _repo_root() -> Path:
    """Internal helper for `_repo_root`."""
    return Path(__file__).resolve().parents[5]


def _iter_python_files(paths: Iterable[Path]) -> Iterable[Path]:
    """Internal helper for `_iter_python_files`."""
    for root in paths:
        if not root.exists():
            continue
        yield from root.rglob("*.py")


def _extract_symbols(text: str) -> frozenset[str]:
    """Internal helper for `_extract_symbols`."""
    return frozenset(_SYMBOL_PATTERN.findall(text))


def load_compat_symbols() -> frozenset[str]:
    """Load data required by `load_compat_symbols`."""
    editor_path = Path(__file__).resolve().parent / "editor.py"
    return _extract_symbols(editor_path.read_text(encoding="utf-8"))


def load_repo_symbols(root: Path | None = None) -> frozenset[str]:
    """Load data required by `load_repo_symbols`."""
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
    """Load data required by `load_app_exclusive_symbols`."""
    editor_path = Path(__file__).resolve().parent / "editor.py"
    text = editor_path.read_text(encoding="utf-8")
    names = sorted({name for name, _value in _COMPAT_CUSTOM_ID_PATTERN.findall(text)})
    return tuple(names)


def load_native_qsci_symbols() -> frozenset[str]:
    """Load data required by `load_native_qsci_symbols`."""
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
    """Build and return the value produced by `build_audit_report`."""
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
    """Execute the `native_baseline_path` workflow."""
    root = root or _repo_root()
    return root / "docs" / "scintilla_native_qsci_baseline.json"


def contract_baseline_path(root: Path | None = None) -> Path:
    """Execute the `contract_baseline_path` workflow."""
    root = root or _repo_root()
    return root / "docs" / "scintilla_compat_contract_baseline.json"


def save_native_baseline(root: Path | None = None) -> Path:
    """Save data handled by `save_native_baseline`."""
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
    """Load data required by `load_native_baseline`."""
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
    """Save data handled by `save_contract_baseline`."""
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
    """Load data required by `load_contract_baseline`."""
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
