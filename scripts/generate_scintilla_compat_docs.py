from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypad.ui.editor.scintilla_compat.audit import build_audit_report
from pypad.ui.editor.scintilla_compat.metadata import load_command_metadata


def main() -> int:
    report = build_audit_report(ROOT)
    metadata = load_command_metadata()
    json_path = ROOT / "docs" / "scintilla_compat_reference.json"
    md_path = ROOT / "docs" / "scintilla_compat_reference.md"
    json_payload = {
        "repo_complete": report.repo_complete,
        "compat_symbol_count": len(report.compat_symbols),
        "app_exclusive_symbols": list(report.app_exclusive_symbols),
        "commands": {name: item.to_dict() for name, item in metadata.items()},
    }
    json_path.write_text(json.dumps(json_payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Scintilla compat reference",
        "",
        f"- Repo coverage complete: `{str(report.repo_complete).lower()}`",
        f"- Compat symbols: `{len(report.compat_symbols)}`",
        f"- App-exclusive symbols: `{len(report.app_exclusive_symbols)}`",
        "",
        "| Symbol | Category | Status | Args | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name in sorted(metadata):
        item = metadata[name]
        args = ", ".join(item.args)
        notes = item.notes.replace("|", "\\|")
        lines.append(f"| `{item.symbol}` | `{item.category}` | `{item.status}` | `{args}` | {notes} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json_path)
    print(md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
