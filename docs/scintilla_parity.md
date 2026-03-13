# Scintilla compat contract

`scintilla_compat` is the canonical Scintilla surface for this app.

There are two checks:

- Repo coverage: every `SCI_*`, `SCN_*`, `SC_*`, and `INDIC_*` symbol referenced by the repo is defined by the compat engine.
- Compat contract baseline: the current compat symbol set and app-exclusive extensions are captured in a checked-in baseline so API growth is explicit.

Commands:

```powershell
python scripts/audit_scintilla_compat.py
python scripts/capture_scintilla_compat_contract.py
```

Files:

- Contract baseline: [`docs/scintilla_compat_contract_baseline.json`](/c:/Users/user/Downloads/py/RawAPPS/test/notepadclone/docs/scintilla_compat_contract_baseline.json)
- Optional native reference baseline: [`docs/scintilla_native_qsci_baseline.json`](/c:/Users/user/Downloads/py/RawAPPS/test/notepadclone/docs/scintilla_native_qsci_baseline.json)

Expected behavior:

- `audit_scintilla_compat.py` reports whether repo usage is fully covered by compat.
- `capture_scintilla_compat_contract.py` writes the current compat contract baseline.
- `tests/test_scintilla_compat_audit.py` validates the saved compat contract baseline when present.

Native `PySide6.Qsci` is optional reference material only. It is not the source of truth for this app.
