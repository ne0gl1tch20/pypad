"""Summarize plugin health in plain language for manager-style desktop dialogs.

This helper module keeps list-detail summaries concise and readable so plugin
management surfaces can explain risk and state without forcing users to parse
raw diagnostics output.
"""

from __future__ import annotations


def summarize_plugin_health(records) -> str:
    """Return a short health summary for the current discovered plugins."""

    total = len(records)
    loaded = sum(1 for rec in records if getattr(rec, "instance", None) is not None)
    blocked = sum(1 for rec in records if getattr(rec, "security_issues", None))
    incompatible = sum(1 for rec in records if getattr(rec, "compatibility_issues", None))
    quarantined = sum(1 for rec in records if bool(getattr(rec, "quarantined", False)))
    failing = sum(1 for rec in records if int(getattr(rec, "failure_count", 0) or 0) > 0)
    return (
        f"{total} plugin(s) | Loaded {loaded} | Blocked {blocked} | "
        f"Incompatible {incompatible} | Quarantined {quarantined} | Failing {failing}"
    )
