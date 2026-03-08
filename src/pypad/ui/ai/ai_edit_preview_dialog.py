from PySide6.QtWidgets import QDialog

from ._plugin_bridge import export_runtime_symbols

try:
    export_runtime_symbols(globals(), "ai_edit_preview_dialog")
except ImportError:
    class AIEditPreviewDialog(QDialog):  # type: ignore[override]
        def __init__(self, parent=None, *_, **__) -> None:
            super().__init__(parent)
            self.setWindowTitle("AI Preview Unavailable")

    class AIRewritePromptDialog(QDialog):  # type: ignore[override]
        def __init__(self, parent=None, *_, **__) -> None:
            super().__init__(parent)
            self.setWindowTitle("AI Rewrite Unavailable")

    __all__ = ["AIEditPreviewDialog", "AIRewritePromptDialog"]
