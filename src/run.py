"""Launch the desktop application, prepare runtime paths, and manage startup diagnostics."""

import argparse
import atexit
import faulthandler
import os
import sys
import threading
import traceback
from pathlib import Path
from time import perf_counter
from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QPixmap, QPainter, QFontDatabase, QFont
from PySide6.QtCore import QObject, QEvent, Qt, QTimer, qInstallMessageHandler, QtMsgType

# Keep a process-wide reference to the top-level window so it is not garbage-collected
# after startup code exits. Some Qt windows can disappear unexpectedly if no strong
# Python reference remains.
_MAIN_WINDOW = None


class _DiagnosticsSplashScreen(QSplashScreen):
    """Splash screen that can arm hidden startup diagnostics via repeated input."""

    def __init__(self, pixmap: QPixmap, flags) -> None:
        super().__init__(pixmap, flags)
        self._trigger_count = 0
        self._trigger_target = 7
        self._last_trigger_at = 0.0
        self._trigger_window_sec = 2.5
        self._armed = False

    def _register_trigger(self) -> None:
        """Track repeated splash interactions and arm diagnostics when the threshold is met."""
        now = perf_counter()
        if now - self._last_trigger_at > self._trigger_window_sec:
            self._trigger_count = 0
        self._last_trigger_at = now
        self._trigger_count += 1
        remaining = max(0, self._trigger_target - self._trigger_count)
        _startup_log(
            f"[Startup] Splash diagnostics trigger progress count={self._trigger_count}/{self._trigger_target}"
        )
        if self._trigger_count >= self._trigger_target:
            self._arm_diagnostics()
            return
        self.showMessage(
            f"Advanced diagnostics: {remaining} more",
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
            Qt.GlobalColor.white,
        )

    def _arm_diagnostics(self) -> None:
        """Persist the splash startup-recovery request onto the application instance."""
        if self._armed:
            return
        self._armed = True
        app = QApplication.instance()
        if app is not None:
            app.setProperty("startup_open_recovery_dialog", True)
        _startup_log("[Startup] Splash diagnostics trigger armed; startup recovery dialog will open after startup.")
        self.showMessage(
            "Startup recovery armed",
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
            Qt.GlobalColor.white,
        )

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """Treat repeated clicks on the splash screen as the hidden diagnostics gesture."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._register_trigger()
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        """Allow keyboard mashing as an accessibility-friendly alternative to clicking."""
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_D):
            self._register_trigger()
        super().keyPressEvent(event)


def _configure_startup_runtime_env() -> None:
    # Read any existing Chromium/WebEngine flags so startup keeps user- or
    # environment-provided options intact.
    # Reduce Chromium/WebEngine stderr noise from benign GPU/direct-composition diagnostics.
    """Configure environment variables needed before Qt startup."""
    flags = str(os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "") or "").strip()
    # These flags suppress verbose Chromium logging that is not actionable for normal users.
    desired_parts = ["--disable-logging", "--log-level=3"]
    merged: list[str] = []
    if flags:
        # Preserve the original flag string first so additional options are appended.
        merged.append(flags)
    for part in desired_parts:
        # Only add missing flags so repeated startup does not duplicate arguments.
        if part not in flags:
            merged.append(part)
    # Write the merged flag set back into the environment before Qt imports use it.
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(merged).strip()


_configure_startup_runtime_env()

def _bootstrap_import_paths() -> None:
    """Support both development and PyInstaller onedir layouts.

    Dev layout:
      <repo>/src/run.py

    PyInstaller onedir layout (as installed by Inno):
      run.exe
      _internal/
    """
    # Search a small set of known runtime locations and prepend any that exist.
    # This keeps imports working for both source checkouts and frozen builds.
    candidates: list[Path] = []

    # Development: add the src directory containing "pypad".
    dev_src = Path(__file__).resolve().parent
    candidates.append(dev_src)

    if getattr(sys, "frozen", False):
        # In frozen builds, imports are resolved relative to the generated executable.
        exe_dir = Path(sys.executable).resolve().parent
        # PyInstaller onedir Python runtime + collected modules.
        candidates.append(exe_dir / "_internal")
        # Optional nested layout some builds produce.
        candidates.append(exe_dir / "_internal" / "src")

        # Onefile extraction root (if used), still safe to include.
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            candidates.append(Path(meipass))
            candidates.append(Path(meipass) / "src")

    for path in candidates:
        if path.exists():
            text = str(path)
            if text not in sys.path:
                # Insert near the front so bundled/local application code wins over
                # unrelated site-packages with the same module names.
                sys.path.insert(0, text)


_bootstrap_import_paths()
from pypad.app_settings import get_crash_logs_file_path, get_portable_mode_state, get_settings_file_path
from pypad.logging_utils import configure_app_logging, get_logger, resolve_persisted_log_level
from pypad.ui.theme.asset_paths import resolve_asset_path

configure_app_logging(resolve_persisted_log_level(get_settings_file_path(), default="INFO"))
LOGGER = get_logger(__name__)
PORTABLE_MODE_STATE = get_portable_mode_state()


def _load_app_main():
    from pypad.app import main

    return main


def _build_shell_open_command() -> str:
    # The shell command differs between frozen and source runs. Explorer passes the
    # clicked file path in place of %1.
    """Build the shell command used by Explorer to open files with Pypad."""
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        return f'"{exe}" "%1"'
    python_exe = Path(sys.executable).resolve()
    script = Path(__file__).resolve()
    return f'"{python_exe}" "{script}" "%1"'


def _register_windows_shell_menu() -> None:
    """Register the Windows Explorer context-menu entry for Pypad."""
    if os.name != "nt":
        raise RuntimeError("Windows shell integration is only supported on Windows.")
    import winreg

    # Create a per-user Explorer context-menu entry instead of requiring admin rights.
    label = "Open with Pypad"
    icon_target = Path(sys.executable).resolve()
    command = _build_shell_open_command()
    key_path = r"Software\Classes\*\shell\Open with Pypad"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, label)
        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, str(icon_target))
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path + r"\command") as cmd:
        winreg.SetValueEx(cmd, "", 0, winreg.REG_SZ, command)


def _delete_registry_tree(root, subkey: str) -> None:
    """Recursively delete a Windows registry tree."""
    import winreg

    # Recursively delete child keys first because Windows registry keys must be empty
    # before their parent can be removed.
    with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
        while True:
            try:
                child_name = winreg.EnumKey(key, 0)
            except OSError:
                break
            _delete_registry_tree(root, subkey + "\\" + child_name)
    winreg.DeleteKey(root, subkey)


def _unregister_windows_shell_menu() -> None:
    """Remove the Windows Explorer context-menu entry for Pypad."""
    if os.name != "nt":
        raise RuntimeError("Windows shell integration is only supported on Windows.")
    import winreg

    key_path = r"Software\Classes\*\shell\Open with Pypad"
    try:
        _delete_registry_tree(winreg.HKEY_CURRENT_USER, key_path)
    except FileNotFoundError:
        pass


def _save_startup_traceback(traceback_text: str) -> None:
    """Append startup crash details to the persistent crash log."""
    try:
        # Append instead of overwrite so repeated startup failures preserve history.
        path = get_crash_logs_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("[Startup Crash]\n")
            handle.write(traceback_text.rstrip("\n"))
            handle.write("\n\n")
    except Exception:
        # Startup logging must never create a secondary crash path.
        pass


def _startup_log(message: str) -> None:
    # Small wrapper used for startup-focused messages so the call sites stay concise.
    """Write a startup-focused message to the application logger."""
    LOGGER.debug(message)


def _is_benign_qt_noise(message: str) -> bool:
    """Return whether one Qt log line is known-benign startup/runtime noise."""
    text = str(message or "").strip()
    if not text:
        return False
    if text.startswith("OpenType support missing for ") and ", script " in text:
        return True
    benign_prefixes = (
        "QWindowsWindow::setGeometry: Unable to set geometry",
        "This plugin does not support propagateSizeHints()",
        "Unknown property ",
        "QPainter::begin: Paint device returned engine == 0, type: ",
        "QPainter::setRenderHint: Painter must be active to set rendering hints",
        "QPixmap::scaled: Pixmap is a null pixmap",
    )
    benign_substrings = (
        "does not have a window handle",
        "Cannot set parent, new parent is in a different thread",
        "QBasicTimer::start: QBasicTimer can only be used with threads started with QThread",
        "QSocketNotifier: Can only be used with threads started with QThread",
    )
    return text.startswith(benign_prefixes) or any(token in text for token in benign_substrings)


if PORTABLE_MODE_STATE.enabled and PORTABLE_MODE_STATE.root is not None:
    _startup_log(f"[Startup] Portable mode enabled using local storage at: {PORTABLE_MODE_STATE.root}")


def _install_startup_exception_hooks() -> None:
    # Route uncaught exceptions into the crash log before Python performs its normal
    # exception handling.
    """Install startup exception hooks."""
    def _handle_exception(exc_type, exc_value, exc_tb) -> None:
        """Log an uncaught exception raised on the main thread."""
        error_text = "".join(
            traceback.format_exception(exc_type, exc_value, exc_tb)
        ).strip()
        _save_startup_traceback(error_text)
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    # Thread exceptions are handled separately in modern Python, so install the same
    # persistence logic for worker threads.
    def _handle_thread_exception(args: threading.ExceptHookArgs) -> None:
        """Log an uncaught exception raised on a background thread."""
        error_text = "".join(
            traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)
        ).strip()
        _save_startup_traceback(error_text)
        if args.thread is not None:
            sys.__excepthook__(args.exc_type, args.exc_value, args.exc_traceback)

    sys.excepthook = _handle_exception
    threading.excepthook = _handle_thread_exception

    # Capture Qt warnings/critical/fatal messages.
    def _qt_message_handler(mode, context, message) -> None:
        # Qt can pass either enum values or compatibility shims depending on bindings,
        # so normalize the mode into a readable label first.
        """Capture Qt log messages and persist warnings or worse during startup."""
        text = str(message or "").strip()
        if _is_benign_qt_noise(text):
            return
        if isinstance(mode, QtMsgType):
            mode_name = mode.name
        else:
            mode_name = str(mode)
        should_persist = False
        try:
            # Persist only warning-or-worse Qt messages. Debug/info traffic can be noisy.
            warning_modes = {
                QtMsgType.QtWarningMsg,
                QtMsgType.QtCriticalMsg,
                QtMsgType.QtFatalMsg,
            }
            should_persist = mode in warning_modes
        except Exception:
            # Fall back to a string-based check if enum comparison behaves unexpectedly.
            normalized = str(mode_name).lower()
            should_persist = any(token in normalized for token in ("warning", "critical", "fatal"))
        location = ""
        if context is not None:
            parts = []
            if context.file:
                parts.append(context.file)
            if context.line:
                parts.append(str(context.line))
            if context.function:
                parts.append(context.function)
            if parts:
                location = " (" + ":".join(parts) + ")"
        rendered = f"[Qt:{mode_name}]{location} {text}"
        if should_persist:
            _save_startup_traceback(rendered)
        else:
            LOGGER.debug(rendered)
    qInstallMessageHandler(_qt_message_handler)

    # Capture low-level crashes (segfaults, aborts) to the same log.
    try:
        path = get_crash_logs_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            faulthandler.enable(file=handle, all_threads=True)
    except Exception:
        pass

if __name__ == "__main__":
    # Parse only application-owned flags here and leave unknown arguments for Qt.
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--register-shell-menu",
        action="store_true",
        help="Register 'Open with Pypad' in File Explorer context menu (current user).",
    )
    parser.add_argument(
        "--unregister-shell-menu",
        action="store_true",
        help="Remove 'Open with Pypad' from File Explorer context menu (current user).",
    )
    parsed_args, qt_args = parser.parse_known_args(sys.argv[1:])
    LOGGER.debug("Parsed startup args: parsed=%s qt=%s", parsed_args, qt_args)

    # These maintenance commands are mutually exclusive and exit immediately after
    # changing the Explorer integration state.
    if parsed_args.register_shell_menu and parsed_args.unregister_shell_menu:
        print("Choose either --register-shell-menu or --unregister-shell-menu, not both.")
        sys.exit(2)
    if parsed_args.register_shell_menu:
        try:
            _register_windows_shell_menu()
            print("Registered: 'Open with Pypad' in File Explorer context menu.")
        except Exception as exc:
            print(f"Failed to register shell menu: {exc}")
            sys.exit(1)
        sys.exit(0)
    if parsed_args.unregister_shell_menu:
        try:
            _unregister_windows_shell_menu()
            print("Removed: 'Open with Pypad' from File Explorer context menu.")
        except Exception as exc:
            print(f"Failed to unregister shell menu: {exc}")
            sys.exit(1)
        sys.exit(0)

    # Ensure menu actions are allowed to render icons on platforms/styles that
    # otherwise suppress them globally.
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)

    # Install crash and warning hooks before any substantial GUI work begins.
    _install_startup_exception_hooks()
    LOGGER.debug("Startup exception hooks installed")
    # Emit a final shutdown breadcrumb even for normal exits.
    atexit.register(lambda: _startup_log("Process exiting (atexit)."))
    # Track total startup duration for diagnostics.
    startup_started_at = perf_counter()
    # Use a mutable cell so nested functions can ensure startup completion is reported once.
    startup_reported = [False]
    # Pass Qt-only arguments to QApplication while keeping argv[0] as the process name.
    app = QApplication([sys.argv[0], *qt_args])
    LOGGER.debug("QApplication created")
    # Closing the main window should terminate the app process.
    app.setQuitOnLastWindowClosed(True)

    splash_started_at = perf_counter()
    # Load splash image
    splash_asset = resolve_asset_path("splash.png")
    splash_path = str(splash_asset) if splash_asset is not None else ""
    if splash_asset is None:
        LOGGER.warning("Splash image asset not found: splash.png")
    pixmap = QPixmap(splash_path)
    LOGGER.debug("Loaded splash pixmap from %s", splash_path)
    pixmap = pixmap.scaled(
        600,
        400,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    LOGGER.debug("Splash image prepared in %dms", int((perf_counter() - splash_started_at) * 1000))

    # Load version text
    version_asset = resolve_asset_path("version.txt")
    version_file = str(version_asset) if version_asset is not None else ""
    try:
        with open(version_file, "r", encoding="utf-8") as f:
            version = f.read().strip()
    except FileNotFoundError:
        version = "v?.?.?"  # fallback
        LOGGER.warning("Version file not found: %s", version_file)
    LOGGER.info("Pypad app version: %s", version)
    _startup_log("Waiting for main_window to start...")

    font_started_at = perf_counter()
    # Load custom font
    font_asset = resolve_asset_path("splash.ttf")
    font_path = str(font_asset) if font_asset is not None else ""
    if font_asset is None:
        LOGGER.warning("Splash font asset not found: splash.ttf")
    font_id = QFontDatabase.addApplicationFont(font_path)
    LOGGER.debug("Splash font load attempted from %s (font_id=%s)", font_path, font_id)

    if font_id == -1:
        print(f"Warning: Failed to load font at {font_path}, using default font.")
        font = QFont("Arial", 14)  # fallback
    else:
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            font = QFont(families[0], 14)
        else:
            print(
                f"Warning: No font families found in {font_path}, using default font."
            )
            font = QFont("Arial", 14)  # fallback
    LOGGER.debug("Splash font resolved in %dms", int((perf_counter() - font_started_at) * 1000))

    # Draw version text on splash
    painter = QPainter(pixmap)
    painter.setFont(font)
    painter.setPen(Qt.GlobalColor.white)
    margin = 20
    # Stamp the resolved application version onto the splash image itself.
    painter.drawText(margin, pixmap.height() - margin, f"App Version: {version}")
    painter.end()

    # Show splash
    splash = _DiagnosticsSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
    splash.show()
    splash.raise_()
    splash.activateWindow()

    def mark_app_started(window) -> None:
        # Centralize startup completion so timing and splash teardown happen once no
        # matter which code path marks the app as ready.
        """Record startup completion and update startup state."""
        if startup_reported[0]:
            return
        startup_reported[0] = True
        _startup_log("[Startup] App marked started; main window is ready for gated reveal.")
        elapsed_ms = int((perf_counter() - startup_started_at) * 1000)
        elapsed_sec = elapsed_ms / 1000.0
        _startup_log(f"Took {elapsed_ms}ms (or {elapsed_sec:.2f} seconds) to initialize!")
        # Expose a simple readiness flag for other startup coordination code.
        app.setProperty("app_started", True)

    # Store the callback on the application object so downstream startup code can call
    # it without importing this module directly.
    app.setProperty("startup_ready_callback", mark_app_started)

    # Start main window after short delay
    def start_main():
        """Start the main window and enter the Qt event loop."""
        LOGGER.debug("Launching main window bootstrap")
        try:
            # Reuse the existing QApplication instead of letting the app module create
            # a second instance.
            window = _load_app_main()(existing_app=app)
        except Exception:
            trace_text = traceback.format_exc()
            _save_startup_traceback(trace_text)
            LOGGER.exception("Main window bootstrap failed")
            app.quit()
            return
        if window is None:
            LOGGER.warning("main() returned None; quitting app")
            app.quit()
            return
        # Keep a strong reference so Qt doesn't destroy the window.
        global _MAIN_WINDOW
        _MAIN_WINDOW = window
        
        # Diagnostics for unexpected exits (connect before showing in case startup quits immediately)
        def _log_quit(reason: str) -> None:
            """Record an application-quit breadcrumb for startup diagnostics."""
            _startup_log(f"App quitting ({reason})")

        app.aboutToQuit.connect(lambda: _log_quit("aboutToQuit"))
        app.lastWindowClosed.connect(lambda: _log_quit("lastWindowClosed"))

        # Make sure app exits cleanly when main window closes
        window.destroyed.connect(lambda: _log_quit("main window destroyed"))
        window.destroyed.connect(app.quit)

        def _show_and_activate_main_window() -> None:
            # Separate showing from construction so startup code can delay visibility
            # until internal initialization is complete.
            """Show the main window, finish deferred startup work, and request focus."""
            _startup_log("[Startup] Showing main window...")
            _startup_log(
                "[StartupTrace] gated_reveal "
                f"allow_show={bool(getattr(window, '_startup_allow_show', False))} "
                f"hold={bool(getattr(window, '_startup_hold_main_window_visible', False))} "
                f"visible={window.isVisible()} "
                f"state={window.windowState()}"
            )
            window._startup_allow_show = True
            window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)
            window.setWindowOpacity(1.0)
            if window.isMinimized():
                window.showNormal()
            else:
                window.show()
            window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized)
            _startup_log(
                f"[Startup] Main window shown: visible={window.isVisible()} minimized={window.isMinimized()}"
            )
            if getattr(window, "_layout_restore_pending_after_show", False):
                _startup_log("[Startup] Applying deferred layout restore...")
                window._layout_restore_pending_after_show = False
                try:
                    if hasattr(window, "_restore_layout_from_settings"):
                        window._restore_layout_from_settings()
                except Exception as exc:
                    _startup_log(f"Warning: deferred layout restore failed: {exc}")
            mark_app_started(window)
            if bool(app.property("startup_open_recovery_dialog")):
                _startup_log("[Startup] Opening armed startup recovery dialog.")
                window.hide()
                QTimer.singleShot(0, lambda: window.open_startup_recovery_dialog(force=True))
                return
            # Defer native activation calls; they can be fragile during first show on some setups.
            def _activate_main_window() -> None:
                """Raise and activate the main window after startup completes."""
                try:
                    if not window.isVisible():
                        window.show()
                    _startup_log("[Startup] Activating main window...")
                    window.raise_()
                    window.activateWindow()
                except Exception as exc:
                    _startup_log(f"Warning: failed to raise/activate main window: {exc}")
            QTimer.singleShot(0, _activate_main_window)
            QTimer.singleShot(0, window.enforce_privacy_lock)

            def _close_splash_after_reveal() -> None:
                """Dismiss the splash only after the main window has had time to activate."""
                if not splash.isVisible():
                    return
                previous_quit_on_last = app.quitOnLastWindowClosed()
                app.setQuitOnLastWindowClosed(False)
                try:
                    _startup_log("[Startup] Closing splash after main window reveal.")
                    splash.hide()
                    splash.close()
                finally:
                    QTimer.singleShot(
                        250,
                        lambda prev=previous_quit_on_last: app.setQuitOnLastWindowClosed(prev),
                    )

            QTimer.singleShot(250, _close_splash_after_reveal)

        def _check_window_visibility() -> None:
            # Record a delayed visibility snapshot because some startup failures only
            # appear after the first event-loop turns.
            """Log a delayed snapshot of the main-window visibility state."""
            try:
                visible = window.isVisible()
                minimized = window.isMinimized()
                _startup_log(
                    f"[Startup] Window state: visible={visible} minimized={minimized} "
                    f"active={window.isActiveWindow()}"
                )
                if not visible:
                    _startup_log("Warning: main window not visible after startup.")
            except Exception as exc:
                _startup_log(f"Warning: failed to read window state: {exc}")

        def _show_when_startup_ready() -> None:
            # Poll lightweight readiness flags instead of blocking the event loop.
            """Wait for startup readiness signals, then reveal the main window."""
            max_wait_ms = 15000
            poll_ms = 50
            waited = {"ms": 0}

            def _poll() -> None:
                """Poll startup readiness without blocking the Qt event loop."""
                try:
                    # The window is considered ready when either the app has already
                    # reported startup completion or the window's own startup sequence
                    # finished and it is no longer requesting hidden startup.
                    ready = (
                        bool(app.property("app_started"))
                        or bool(getattr(window, "_startup_sequence_done", False))
                    ) and not bool(getattr(window, "_startup_hold_main_window_visible", False))
                    LOGGER.debug(
                        "Startup visibility poll ready=%s app_started=%s sequence_done=%s hold=%s waited_ms=%s",
                        ready,
                        bool(app.property("app_started")),
                        bool(getattr(window, "_startup_sequence_done", False)),
                        bool(getattr(window, "_startup_hold_main_window_visible", False)),
                        waited["ms"],
                    )
                except Exception:
                    # If readiness probing itself fails, fail open and show the window.
                    ready = True
                if ready or waited["ms"] >= max_wait_ms:
                    if not ready:
                        _startup_log("Warning: startup ready flag timeout; showing window anyway.")
                    try:
                        _show_and_activate_main_window()
                    except Exception as exc:
                        _startup_log(f"Warning: failed to show main window: {exc}")
                    QTimer.singleShot(1500, _check_window_visibility)
                    return
                waited["ms"] += poll_ms
                # Schedule the next poll asynchronously so Qt can continue processing.
                QTimer.singleShot(poll_ms, _poll)

            _poll()

        _show_when_startup_ready()

    class _QuitEventFilter(QObject):
        """Event filter that records Qt quit events during startup."""
        def eventFilter(self, obj, event):  # type: ignore[override]
            # Log raw Qt quit events as an extra breadcrumb for diagnosing unexpected exits.
            """Log application quit events before Qt continues normal event processing."""
            if event.type() == QEvent.Type.Quit:
                _startup_log("Quit event received by QApplication.")
            return False

    # Keep the filter instance alive for the lifetime of the application.
    _quit_filter = _QuitEventFilter(app)
    app.installEventFilter(_quit_filter)

    # Kick main-window construction onto the event loop so the splash screen can paint first.
    QTimer.singleShot(0, start_main)

    # Enter the Qt event loop and return its exit code to the operating system.
    exit_code = app.exec()
    _startup_log(f"Qt event loop exited with code {exit_code}")
    sys.exit(exit_code)
