"""Create or reuse the Qt application object, configure logging, and construct the main window used by the desktop app.

This module belongs to the top-level Pypad application package. It helps explain how `pypad` is structured and where this file fits into the runtime workflow.
"""

import sys
import traceback
from typing import Optional
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from .app_settings import get_settings_file_path
from .logging_utils import configure_app_logging, get_logger, resolve_persisted_log_level
from .ui.main_window import Notepad

LOGGER = get_logger(__name__)

def main(existing_app: Optional[QApplication] = None) -> Notepad:
    # Use existing QApplication if passed (from run.py), otherwise create one
    """Create the main window, attach top-level exception handling, and return it."""
    owns_app = existing_app is None
    app = existing_app or QApplication(sys.argv)
    configure_app_logging(resolve_persisted_log_level(get_settings_file_path(), default="INFO"))
    app.setApplicationName("Pypad")
    LOGGER.info("App main() starting (owns_app=%s)", owns_app)

    window = Notepad()
    LOGGER.info("Main window instance created")

    def _global_exception_hook(exc_type, exc_value, exc_tb) -> None:
        """Process uncaught global exceptions."""
        error_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb)).strip()
        LOGGER.exception("Unhandled exception routed to global hook", exc_info=(exc_type, exc_value, exc_tb))
        window.log_event("Error", error_text)
        save_crash = getattr(window, "save_crash_traceback", None)
        if callable(save_crash):
            save_crash(error_text)
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _global_exception_hook

    if owns_app:
        window.show()
        LOGGER.info("Window shown by app.main() (standalone mode)")
        # Enforce lock screen (if enabled) once the window is visible
        QTimer.singleShot(0, window.enforce_privacy_lock)

    return window  # return the main window for splash.finish()
