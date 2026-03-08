from __future__ import annotations

import json
from pathlib import Path


REPO_URL = "https://github.com/ne0gl1tch20/pypad"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _build_entry(plugin_dir: Path, plugin_meta: dict) -> dict[str, str]:
    plugin_id = str(plugin_meta.get("id", "")).strip()
    if not plugin_id:
        raise ValueError(f"Missing plugin id in {plugin_dir / 'plugin.json'}")
    return {
        "id": plugin_id,
        "name": str(plugin_meta.get("name", plugin_id)).strip() or plugin_id,
        "author": str(plugin_meta.get("author", "ne0gl1tch20")).strip() or "ne0gl1tch20",
        "description": str(plugin_meta.get("description", "")).strip(),
        "version": str(plugin_meta.get("version", "1.0.0")).strip() or "1.0.0",
        "repo": REPO_URL,
        "source": f"online_plugins/{plugin_dir.name}",
        "homepage": REPO_URL,
    }


def regenerate_catalog(repo_root: Path) -> int:
    online_plugins_dir = repo_root / "online_plugins"
    catalog_path = online_plugins_dir / "catalog.json"
    entries: list[dict[str, str]] = []

    for plugin_json in sorted(online_plugins_dir.glob("*/plugin.json")):
        try:
            meta = _load_json(plugin_json)
        except Exception as exc:  # noqa: BLE001
            print(f"Skipping {plugin_json}: {exc}")
            continue
        if not isinstance(meta, dict):
            print(f"Skipping {plugin_json}: manifest must be a JSON object")
            continue
        try:
            entries.append(_build_entry(plugin_json.parent, meta))
        except Exception as exc:  # noqa: BLE001
            print(f"Skipping {plugin_json}: {exc}")

    entries.sort(key=lambda row: row["id"])
    catalog = {"plugins": entries}
    catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    return len(entries)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    count = regenerate_catalog(root)
    print(f"Updated online_plugins/catalog.json with {count} plugin entries.")
