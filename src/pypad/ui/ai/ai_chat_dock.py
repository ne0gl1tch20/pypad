from PySide6.QtWidgets import QDockWidget

from ._plugin_bridge import export_runtime_symbols

try:
    export_runtime_symbols(globals(), "ai_chat_dock")
except ImportError:
    class AIChatDock(QDockWidget):  # type: ignore[override]
        def __init__(self, parent, _ai_controller) -> None:
            super().__init__("AI Chat", parent)
            self.hide()

        def focus_prompt(self) -> None:
            return

        def send_prompt(self, *_, **__) -> None:
            raise RuntimeError(
                "AI runtime unavailable. Enable 'pypad_ai_assistant' from Plugin Manager."
            )

    __all__ = ["AIChatDock"]
