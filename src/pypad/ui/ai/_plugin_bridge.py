from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _runtime_module_path(module_name: str) -> Path:
    root = Path(__file__).resolve().parents[4]
    return (
        root
        / "online_plugins"
        / "pypad_ai_assistant"
        / "pypad_ai_runtime"
        / f"{module_name}.py"
    )


def load_runtime_module(module_name: str) -> ModuleType:
    full_name = f"pypad.plugin_ai_runtime.{module_name}"
    existing = sys.modules.get(full_name)
    if existing is not None:
        return existing
    mod_path = _runtime_module_path(module_name)
    if not mod_path.exists():
        raise ImportError(f"AI runtime module not found: {mod_path}")
    spec = importlib.util.spec_from_file_location(full_name, mod_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to create module spec for: {mod_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


def export_runtime_symbols(target_globals: dict, module_name: str) -> None:
    module = load_runtime_module(module_name)
    names = getattr(module, "__all__", None)
    if not isinstance(names, list):
        names = [name for name in vars(module).keys() if not name.startswith("_")]
    for name in names:
        target_globals[name] = getattr(module, name)
    target_globals["__all__"] = list(names)
    target_globals["__doc__"] = getattr(module, "__doc__", "")
