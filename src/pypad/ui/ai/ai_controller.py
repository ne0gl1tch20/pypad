from ._plugin_bridge import export_runtime_symbols

try:
    export_runtime_symbols(globals(), "ai_controller")
except ImportError:
    class AIController:  # type: ignore[override]
        def __init__(self, _window) -> None:
            raise RuntimeError(
                "AI runtime unavailable. Enable 'pypad_ai_assistant' from Plugin Manager."
            )

    def sanitize_prompt_text(text: str, _settings=None) -> str:
        return str(text or "")

    def _generate_sync(*_args, **_kwargs):
        raise RuntimeError(
            "AI runtime unavailable. Enable 'pypad_ai_assistant' from Plugin Manager."
        )

    __all__ = ["AIController", "sanitize_prompt_text", "_generate_sync"]
