"""Audit the repository's Scintilla compatibility surface and print a JSON summary."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypad.ui.editor.scintilla_compat.audit import build_audit_report


def main() -> int:
    """Build an audit report for the repo and emit a machine-readable summary."""

    report = build_audit_report(ROOT)
    payload = {
        "repo_complete": report.repo_complete,
        "native_complete": report.native_complete,
        "compat_symbol_count": len(report.compat_symbols),
        "repo_symbol_count": len(report.repo_symbols),
        "native_symbol_count": len(report.native_symbols),
        "repo_missing": list(report.repo_missing),
        "native_missing": list(report.native_missing),
        "app_exclusive_symbols": list(report.app_exclusive_symbols),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if report.repo_complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
