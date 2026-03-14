"""Configure the application logging pipeline and helper functions used to resolve, persist, and retrieve loggers.

This module belongs to the top-level Pypad application package. It helps explain how `pypad` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

import logging
import sys
import threading
import json
from pathlib import Path
from datetime import datetime
from collections import deque

LOG_LEVEL_OPTIONS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
DEFAULT_LOG_LEVEL = "INFO"
_CONSOLE_BUFFER_MAX = 12000
_console_lines: deque[str] = deque(maxlen=_CONSOLE_BUFFER_MAX)
_console_lock = threading.Lock()
_console_capture_installed = False


class _NullStream:
    """Minimal file-like sink used when no std streams are available."""

    encoding = "utf-8"

    def write(self, data) -> int:
        """Execute the `write` workflow."""
        return len(str(data or ""))

    def flush(self) -> None:
        """Execute the `flush` workflow."""
        return

    def isatty(self) -> bool:
        """Execute the `isatty` workflow."""
        return False


def _append_console_line(line: str) -> None:
    """Internal helper for `_append_console_line`."""
    text = str(line or "").rstrip("\r\n")
    if not text:
        return
    with _console_lock:
        _console_lines.append(text)


def get_console_log_lines() -> list[str]:
    """Return the value produced by `get_console_log_lines`."""
    with _console_lock:
        return list(_console_lines)


def clear_console_log_lines() -> None:
    """Execute the `clear_console_log_lines` workflow."""
    with _console_lock:
        _console_lines.clear()


class _ConsoleCaptureTee:
    """Class that implements the `_ConsoleCaptureTee` runtime behavior."""
    def __init__(self, stream, *, label: str) -> None:
        """Initialize the `logging_utils` state for this instance."""
        self._stream = stream
        self._label = label
        self._partial = ""
        self._pypad_console_capture_wrapper = True

    def write(self, data) -> int:
        """Execute the `write` workflow."""
        text = str(data or "")
        if not text:
            return 0
        stream = self._stream
        if stream is not None:
            try:
                self._safe_stream_write(stream, text)
            except Exception:
                pass
        self._partial += text
        while True:
            nl_idx = self._partial.find("\n")
            if nl_idx < 0:
                break
            line = self._partial[:nl_idx]
            self._partial = self._partial[nl_idx + 1 :]
            if line.strip():
                _append_console_line(f"[{self._label}] {line.rstrip(chr(13))}")
        return len(text)

    def flush(self) -> None:
        """Execute the `flush` workflow."""
        try:
            stream = self._stream
            if stream is not None:
                stream.flush()
        finally:
            if self._partial.strip():
                _append_console_line(f"[{self._label}] {self._partial.rstrip(chr(13))}")
            self._partial = ""

    def __getattr__(self, name: str):
        """Internal helper for `__getattr__`."""
        stream = self._stream
        if stream is None:
            raise AttributeError(name)
        return getattr(stream, name)

    @staticmethod
    def _safe_stream_write(stream, text: str) -> None:
        """Internal helper for `_safe_stream_write`."""
        try:
            stream.write(text)
            return
        except UnicodeEncodeError:
            encoding = getattr(stream, "encoding", None) or "utf-8"
            repaired = str(text).encode(encoding, errors="backslashreplace").decode(encoding, errors="replace")
            stream.write(repaired)


class _CapturingStreamHandler(logging.StreamHandler):
    """Class that implements the `_CapturingStreamHandler` runtime behavior."""
    def emit(self, record: logging.LogRecord) -> None:
        """Execute the `emit` workflow."""
        try:
            rendered = self.format(record)
        except Exception:
            rendered = ""
        if rendered:
            _append_console_line(rendered)
        try:
            stream = self.stream
            if stream is None:
                return
            msg = str(rendered or "")
            if not msg:
                return
            _ConsoleCaptureTee._safe_stream_write(stream, msg + self.terminator)
            self.flush()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)


class _PypadLogFormatter(logging.Formatter):
    """Class that implements the `_PypadLogFormatter` runtime behavior."""
    def format(self, record: logging.LogRecord) -> str:
        """Execute the `format` workflow."""
        timestamp = datetime.fromtimestamp(record.created)
        time_text = timestamp.strftime("%H:%M:%S.%f")[:-3]
        date_text = f"{timestamp.month}/{timestamp.day}/{timestamp.year}"
        level_text = str(record.levelname or "INFO").capitalize()
        message = record.getMessage()
        name = str(record.name or "").strip()
        if name:
            message = f"[{name}] {message}"
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            if exc_text:
                message = f"{message}\n{exc_text}"
        return f"[{level_text}] [{time_text} {date_text}] {message}"


def normalize_log_level_name(value: object, default: str = DEFAULT_LOG_LEVEL) -> str:
    """Execute the `normalize_log_level_name` workflow."""
    text = str(value or "").strip().upper()
    return text if text in LOG_LEVEL_OPTIONS else str(default).strip().upper()


def get_level_number(value: object, default: str = DEFAULT_LOG_LEVEL) -> int:
    """Return the value produced by `get_level_number`."""
    return int(getattr(logging, normalize_log_level_name(value, default), logging.INFO))


def configure_app_logging(level: object = DEFAULT_LOG_LEVEL) -> str:
    """Execute the `configure_app_logging` workflow."""
    _install_console_capture()
    level_name = normalize_log_level_name(level)
    root_logger = logging.getLogger()
    handler = None
    for existing in root_logger.handlers:
        if getattr(existing, "_pypad_console_handler", False):
            handler = existing
            break
    if handler is None:
        base_stream = sys.__stdout__ or sys.stdout or sys.__stderr__ or sys.stderr or _NullStream()
        handler = _CapturingStreamHandler(base_stream)
        handler._pypad_console_handler = True  # type: ignore[attr-defined]
        handler.setFormatter(_PypadLogFormatter())
        root_logger.addHandler(handler)
    root_logger.setLevel(get_level_number(level_name))
    logging.captureWarnings(True)
    return level_name


def resolve_persisted_log_level(
    settings_path: str | Path | None,
    *,
    default: str = DEFAULT_LOG_LEVEL,
) -> str:
    """Execute the `resolve_persisted_log_level` workflow."""
    path = Path(settings_path) if settings_path else None
    if path is None or not path.exists():
        return normalize_log_level_name(default)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return normalize_log_level_name(default)
    if not isinstance(payload, dict):
        return normalize_log_level_name(default)
    return normalize_log_level_name(payload.get("logging_level", default), default)


def get_logger(name: str) -> logging.Logger:
    """Return the value produced by `get_logger`."""
    return logging.getLogger(name)


def _install_console_capture() -> None:
    """Internal helper for `_install_console_capture`."""
    global _console_capture_installed
    if _console_capture_installed:
        return
    if sys.stdout is None:
        sys.stdout = _NullStream()
    if sys.stderr is None:
        sys.stderr = _NullStream()
    if not getattr(sys.stdout, "_pypad_console_capture_wrapper", False):
        sys.stdout = _ConsoleCaptureTee(sys.stdout, label="stdout")
    if not getattr(sys.stderr, "_pypad_console_capture_wrapper", False):
        sys.stderr = _ConsoleCaptureTee(sys.stderr, label="stderr")
    _console_capture_installed = True
