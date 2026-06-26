"""Coordinate AI requests, prompt assembly, response handling, and UI integration for AI features.

This module belongs to the AI-assisted editing and collaboration UI layer. It helps explain how `pypad.ui.ai` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

import json
import os
import re
import sys
import socket
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
)

from pypad.ui.ai.ai_edit_preview_dialog import AIEditPreviewDialog, AIRewritePromptDialog
from pypad.ai_app_knowledge import resolve_ai_app_knowledge
from pypad.logging_utils import get_logger
from pypad.ui.security.security_profile import profile_setting, resolve_security_policy
from pypad.ui.theme.asset_paths import resolve_asset_path

MISSING_API_KEY_MESSAGE = (
    "I don't have an API key! Do it in Settings > Preferences > AI and Updates > Gemini API Key! "
    "To add your own API Key, visit https://aistudio.google.com/app/api-keys"
)

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
WINDOWS_PATH_RE = re.compile(r"(?<!\w)(?:[A-Za-z]:\\|\\\\)[^\s\"'<>|?*]+")
POSIX_PATH_RE = re.compile(r"(?<![\w:])/(?:[^/\s]+/)+[^/\s]+")
ASSIGNMENT_SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|token|secret|password|passwd)\b\s*[:=]\s*([^\s,;]+)"
)
BEARER_TOKEN_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-~+/=]{8,}\b")
JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_\-]+?\.[A-Za-z0-9_\-]+?\.[A-Za-z0-9_\-]+?\b")

_LOGGER = get_logger(__name__)


def _replace_posix_paths(text: str) -> tuple[str, int]:
    """Redact POSIX-like paths while preserving internal `pypad://...` deep links."""
    replaced: list[str] = []
    last = 0
    count = 0
    for match in POSIX_PATH_RE.finditer(text):
        start, end = match.span()
        scheme_start = max(0, start - 8)
        if text[scheme_start:start].lower().endswith("pypad:/"):
            continue
        replaced.append(text[last:start])
        replaced.append("[REDACTED_PATH]")
        last = end
        count += 1
    if not count:
        return text, 0
    replaced.append(text[last:])
    return "".join(replaced), count


def sanitize_prompt_text(prompt: str, settings: dict) -> tuple[str, list[str]]:
    """Apply configurable redaction rules to a prompt before it is sent to the model."""
    redacted = prompt
    changes: list[str] = []
    if bool(profile_setting(settings, "ai_send_redact_emails", True)):
        updated, count = EMAIL_RE.subn("[REDACTED_EMAIL]", redacted)
        if count:
            redacted = updated
            changes.append(f"emails({count})")
    if bool(profile_setting(settings, "ai_send_redact_paths", True)):
        updated, count_win = WINDOWS_PATH_RE.subn("[REDACTED_PATH]", redacted)
        updated, count_posix = _replace_posix_paths(updated)
        total = count_win + count_posix
        if total:
            redacted = updated
            changes.append(f"paths({total})")
    if bool(profile_setting(settings, "ai_send_redact_tokens", True)):
        updated, count_assign = ASSIGNMENT_SECRET_RE.subn(r"\1=[REDACTED_TOKEN]", redacted)
        updated, count_bearer = BEARER_TOKEN_RE.subn("Bearer [REDACTED_TOKEN]", updated)
        updated, count_jwt = JWT_RE.subn("[REDACTED_TOKEN]", updated)
        total = count_assign + count_bearer + count_jwt
        if total:
            redacted = updated
            changes.append(f"tokens({total})")
    return redacted, changes


class _AIWorker(QObject):
    """Background worker that performs one non-streaming AI request on a QThread."""
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, prompt: str, api_key: str, model: str) -> None:
        """Create the background AI worker used for non-streaming requests."""
        super().__init__()
        self.prompt = prompt
        self.api_key = api_key
        self.model = model

    def run(self) -> None:
        """Execute the request and emit either the final text or a failure message."""
        try:
            result = _generate_sync(self.prompt, self.api_key, self.model)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.exception("AI worker failed model=%s", self.model)
            self.failed.emit(str(exc))
            return
        self.finished.emit(result)


class _AIStreamWorker(QObject):
    """Background worker that emits streaming AI output chunks until completion or cancel."""
    chunk = Signal(str)
    finished = Signal(str)
    cancelled = Signal(str)
    failed = Signal(str)

    def __init__(self, prompt: str, api_key: str, model: str) -> None:
        """Create the background AI worker used for streaming responses."""
        super().__init__()
        self.prompt = prompt
        self.api_key = api_key
        self.model = model
        self._cancel_requested = False

    def cancel(self) -> None:
        """Mark the active stream for cooperative cancellation."""
        _LOGGER.debug("AI stream worker cancel requested model=%s prompt_chars=%d", self.model, len(self.prompt))
        self._cancel_requested = True

    def run(self) -> None:
        """Drive the streaming generator and forward chunks through Qt signals."""
        _LOGGER.debug("AI stream worker run start model=%s prompt_chars=%d", self.model, len(self.prompt))
        try:
            parts: list[str] = []
            for piece in _generate_stream(self.prompt, self.api_key, self.model):
                if self._cancel_requested:
                    _LOGGER.debug("AI stream worker run cancelled-before-emit chunks=%d chars=%d", len(parts), len("".join(parts)))
                    self.cancelled.emit("".join(parts).strip())
                    return
                if not piece:
                    continue
                parts.append(piece)
                _LOGGER.debug("AI stream worker emit chunk chars=%d total_chunks=%d", len(piece), len(parts))
                self.chunk.emit(piece)
                if self._cancel_requested:
                    _LOGGER.debug("AI stream worker run cancelled-after-emit chunks=%d chars=%d", len(parts), len("".join(parts)))
                    self.cancelled.emit("".join(parts).strip())
                    return
            final_text = "".join(parts).strip()
            _LOGGER.debug("AI stream worker finished chunks=%d chars=%d", len(parts), len(final_text))
            self.finished.emit(final_text)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.exception("AI stream worker failed model=%s", self.model)
            self.failed.emit(str(exc))


def _generate_sync(prompt: str, api_key: str, model: str) -> str:
    """Generate a full response using the preferred SDK with a compatibility fallback."""
    if not api_key:
        raise RuntimeError(MISSING_API_KEY_MESSAGE)
    if not model.strip():
        raise RuntimeError("AI model is not configured. Set it in Settings > AI & Updates.")

    # Preferred SDK path (`google-genai`).
    try:
        from google import genai  # type: ignore

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model.strip(),
            contents=prompt,
        )
        text = getattr(response, "text", None)
        if text:
            return str(text)
    except Exception:
        pass

    # Compatibility fallback (`google-generativeai`).
    try:
        import google.generativeai as legacy_genai  # type: ignore

        legacy_genai.configure(api_key=api_key)
        legacy_model = legacy_genai.GenerativeModel(model_name=model.strip())
        response = legacy_model.generate_content(prompt)
        text = getattr(response, "text", None)
        if text:
            return str(text)
    except Exception:
        pass

    raise RuntimeError(
        "AI request failed. Check your connection and try again. It is possible that the rate limit has been exceeded or the model is unavailable. Please try again later."
    )


def _split_for_live_ui(text: str) -> Iterator[str]:
    """Break plain text into small chunks so fallback streaming still feels incremental."""
    words = text.split()
    if not words:
        return
    chunk: list[str] = []
    size = 0
    for word in words:
        add_size = len(word) + (1 if chunk else 0)
        if size + add_size > 24 and chunk:
            yield " ".join(chunk) + " "
            chunk = [word]
            size = len(word)
            continue
        chunk.append(word)
        size += add_size
    if chunk:
        yield " ".join(chunk)


def _generate_stream(prompt: str, api_key: str, model: str) -> Iterator[str]:
    """Yield streamed chunks, or simulate streaming when only sync generation succeeds."""
    if not api_key:
        raise RuntimeError(MISSING_API_KEY_MESSAGE)
    if not model.strip():
        raise RuntimeError("AI model is not configured. Set it in Settings > AI & Updates.")

    try:
        from google import genai  # type: ignore

        client = genai.Client(api_key=api_key)
        stream = client.models.generate_content_stream(
            model=model.strip(),
            contents=prompt,
        )
        yielded = False
        for chunk in stream:
            text = str(getattr(chunk, "text", "") or "")
            if text:
                yielded = True
                yield text
        if yielded:
            return
    except Exception:
        pass

    text = _generate_sync(prompt, api_key, model)
    for piece in _split_for_live_ui(text):
        yield piece


class AIResultDialog(QDialog):
    """Modal dialog for inspecting, copying, or inserting generated AI output."""
    def __init__(self, parent, title: str, text: str) -> None:
        """Build the AI result dialog used to review generated output."""
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(760, 520)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Result", self))
        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        self.output.setPlainText(text)
        layout.addWidget(self.output)

        row = QHBoxLayout()
        self.copy_btn = QPushButton("Copy", self)
        self.insert_btn = QPushButton("Insert", self)
        self.replace_btn = QPushButton("Replace Selection", self)
        row.addWidget(self.copy_btn)
        row.addWidget(self.insert_btn)
        row.addWidget(self.replace_btn)
        layout.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, Qt.Horizontal, self)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.copy_btn.clicked.connect(self._copy_text)
        self.insert_btn.clicked.connect(self._insert_text)
        self.replace_btn.clicked.connect(self._replace_selection)

    def _copy_text(self) -> None:
        """Copy the generated output to the system clipboard."""
        QApplication.clipboard().setText(self.output.toPlainText())

    def _insert_text(self) -> None:
        """Insert the generated output at the current editor cursor."""
        parent = self.parent()
        tab = parent.active_tab() if parent else None
        if tab is None:
            return
        tab.text_edit.insert_text(self.output.toPlainText())

    def _replace_selection(self) -> None:
        """Replace the current editor selection with the generated output."""
        parent = self.parent()
        tab = parent.active_tab() if parent else None
        if tab is None:
            return
        tab.text_edit.replace_selection(self.output.toPlainText())


class AIRedactionPreviewDialog(QDialog):
    """Preview prompt redactions so the user can confirm what will be sent to AI."""
    def __init__(self, parent, action_title: str, changes: list[str], original: str, redacted: str) -> None:
        """Build the redaction preview dialog used before sensitive text is removed."""
        super().__init__(parent)
        self.setWindowTitle("AI Prompt Redaction Preview")
        self.resize(920, 620)
        layout = QVBoxLayout(self)
        summary = QLabel(
            f"{action_title}: redactions applied ({', '.join(changes)}). The redacted prompt will be sent.",
            self,
        )
        layout.addWidget(summary)
        panes = QHBoxLayout()
        left = QTextEdit(self)
        right = QTextEdit(self)
        left.setReadOnly(True)
        right.setReadOnly(True)
        left.setPlainText(original)
        right.setPlainText(redacted)
        panes.addWidget(left, 1)
        panes.addWidget(right, 1)
        layout.addLayout(panes, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        ok_btn = buttons.button(QDialogButtonBox.Ok)
        if ok_btn is not None:
            ok_btn.setText("Send Redacted Prompt")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class AIDeveloperPreviewDialog(QDialog):
    """Preview the exact assembled AI payload for developer mode before send."""
    def __init__(self, parent, payload: dict[str, object]) -> None:
        """Build the developer preview dialog for a pending AI request."""
        super().__init__(parent)
        self.setWindowTitle("AI Developer Send Preview")
        self.resize(980, 700)
        self._payload = dict(payload)

        layout = QVBoxLayout(self)
        summary = QLabel(self._summary_text(), self)
        summary.setWordWrap(True)
        layout.addWidget(summary)

        tabs = QTabWidget(self)
        for title, key in (("Input", "raw_prompt"), ("Assembled", "assembled_prompt"), ("Sent", "sent_prompt")):
            viewer = QTextEdit(self)
            viewer.setReadOnly(True)
            viewer.setPlainText(str(self._payload.get(key, "") or ""))
            tabs.addTab(viewer, title)
        layout.addWidget(tabs, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        ok_btn = buttons.button(QDialogButtonBox.Ok)
        if ok_btn is not None:
            ok_btn.setText("Send")
        copy_btn = QPushButton("Copy Sent", self)
        open_btn = QPushButton("Open Inspector", self)
        buttons.addButton(copy_btn, QDialogButtonBox.ActionRole)
        buttons.addButton(open_btn, QDialogButtonBox.ActionRole)
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(str(self._payload.get("sent_prompt", "") or "")))
        open_btn.clicked.connect(self._open_inspector)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _summary_text(self) -> str:
        """Format a one-line summary for the preview header."""
        changes = ", ".join(str(x) for x in list(self._payload.get("redaction_changes", []) or [])) or "none"
        return (
            f"Action: {self._payload.get('action_title', '')} | "
            f"Model: {self._payload.get('model', '')} | "
            f"Key source: {self._payload.get('api_key_source', '')} | "
            f"Redactions: {changes} | "
            f"Chars: {self._payload.get('sent_chars', 0)}"
        )

    def _open_inspector(self) -> None:
        """Route to the main developer hub when available."""
        parent = self.parent()
        if parent is not None and hasattr(parent, "open_developer_hub"):
            parent.open_developer_hub("AI")


class AIController:
    """Coordinate AI prompt assembly, request execution, and UI result handling."""
    def __init__(self, window) -> None:
        """Bind the controller to the main window and initialize request-scoped caches."""
        self.window = window
        self._threads: list[QThread] = []
        self._active_stream_worker: _AIStreamWorker | None = None
        self._active_stream_thread: QThread | None = None
        self._app_metadata_block = self._build_app_metadata_block()
        self._ai_request_counter = 0
        self._cached_knowledge_block = ""
        self._cached_knowledge_key: tuple[object, ...] | None = None
        self._connectivity_cache_ok = False
        self._connectivity_cache_checked_at = 0.0
        self._last_prompt_payload: dict[str, object] | None = None
        self._recent_prompt_payloads: list[dict[str, object]] = []

    def _log_ai(self, message: str) -> None:
        """Write verbose AI diagnostics only when the related setting is enabled."""
        if not bool(self.window.settings.get("ai_verbose_logging", False)):
            return
        logger = getattr(self.window, "log_event", None)
        if callable(logger):
            logger("Info", f"[AI] {message}")

    def _build_app_metadata_block(self) -> str:
        """Build a compact metadata block describing the current app instance."""
        app_name = str(QApplication.applicationName() or "Pypad").strip() or "Pypad"
        version = "v?.?.?"
        try:
            version_file = resolve_asset_path("version.txt")
            if version_file is not None:
                version = version_file.read_text(encoding="utf-8").strip() or version
        except Exception:
            pass
        if getattr(os, "name", "") == "nt" and getattr(sys, "frozen", False):
            build = "windows-frozen"
        elif getattr(sys, "frozen", False):
            build = "frozen"
        else:
            build = "source"
        return (
            "[APP_METADATA]\n"
            f"app_name={app_name}\n"
            f"app_version={version}\n"
            f"app_build={build}\n"
            "[/APP_METADATA]"
        )

    def _build_app_knowledge_block(self) -> str:
        """Build and cache the optional product-knowledge appendix attached to prompts."""
        mode = str(self.window.settings.get("ai_knowledge_mode", "compact") or "compact").strip().lower()
        include_appendix = bool(self.window.settings.get("ai_include_ui_action_appendix", False))
        if mode == "full":
            include_appendix = True
        cache_key = (
            mode,
            include_appendix,
            int(self.window.settings.get("ai_user_knowledge_max_chars", 1800) or 1800),
            str(self.window.settings.get("ai_app_knowledge_override", "") or ""),
        )
        if cache_key == self._cached_knowledge_key:
            return self._cached_knowledge_block
        knowledge = resolve_ai_app_knowledge(
            self.window.settings.get("ai_app_knowledge_override", ""),
            include_ui_appendix=include_appendix,
            user_knowledge_char_limit=int(self.window.settings.get("ai_user_knowledge_max_chars", 1800) or 1800),
        )
        if not knowledge:
            self._cached_knowledge_key = cache_key
            self._cached_knowledge_block = ""
            return ""
        block = (
            "[PYPAD_KNOWLEDGE]\n"
            f"{knowledge}\n"
            "[/PYPAD_KNOWLEDGE]"
        )
        self._cached_knowledge_key = cache_key
        self._cached_knowledge_block = block
        return block

    def _build_advanced_personality_block(self) -> str:
        """Return the optional advanced personality block configured by the user."""
        personality = str(self.window.settings.get("ai_personality_advanced", "") or "").strip()
        if not personality:
            return ""
        return (
            "[PYPAD_AI_PERSONALITY_ADVANCED]\n"
            f"{personality}\n"
            "[/PYPAD_AI_PERSONALITY_ADVANCED]"
        )

    def _build_runtime_context_block(self) -> str:
        """Describe the active file, workspace, and selection so prompts can be contextual."""
        tab = self.window.active_tab() if hasattr(self.window, "active_tab") else None
        file_name = "Untitled"
        is_markdown = False
        has_selection = False
        selection_preview = ""
        if tab is not None:
            file_name = str(getattr(tab, "current_file", "") or "Untitled")
            is_markdown = bool(getattr(tab, "markdown_mode_enabled", False))
            try:
                has_selection = bool(tab.text_edit.has_selection())
                if has_selection:
                    limit = max(80, int(self.window.settings.get("ai_selection_preview_chars", 240) or 240))
                    selection_preview = str(tab.text_edit.selected_text() or "")[:limit]
            except Exception:
                has_selection = False
                selection_preview = ""
        workspace_root = str(self.window.settings.get("workspace_root", "") or "").strip()
        return (
            "[APP_RUNTIME_CONTEXT]\n"
            f"active_file={file_name}\n"
            f"workspace_root={workspace_root or '(none)'}\n"
            f"markdown_mode={'true' if is_markdown else 'false'}\n"
            f"has_selection={'true' if has_selection else 'false'}\n"
            f"selection_preview={selection_preview}\n"
            "[/APP_RUNTIME_CONTEXT]"
        )

    def _resolve_api_key_with_source(self) -> tuple[str, str]:
        """Resolve the API key together with the source used for diagnostics."""
        resolved = resolve_security_policy(self.window.settings)
        default_storage_mode = "env_only" if resolved.profile_id in {"beginner", "balanced"} else "settings"
        storage_mode = str(profile_setting(self.window.settings, "ai_key_storage_mode", default_storage_mode) or default_storage_mode).strip().lower()
        configured = str(self.window.settings.get("gemini_api_key", "") or "").strip()
        if storage_mode != "env_only" and configured:
            return configured, "settings"
        env_key = str(os.getenv("GEMINI_API_KEY", "")).strip()
        if env_key:
            return env_key, "environment"
        if configured:
            # Recover from contradictory persisted state where a key was saved
            # in settings but the storage mode remained `env_only`.
            return configured, "settings_fallback_after_env_only_conflict"
        return "", "missing"

    def _api_key(self) -> str:
        """Resolve the effective API key string used for actual AI calls."""
        key, _source = self._resolve_api_key_with_source()
        return key

    def last_prompt_payload(self) -> dict[str, object] | None:
        """Return the most recent AI payload snapshot."""
        return dict(self._last_prompt_payload) if isinstance(self._last_prompt_payload, dict) else None

    def recent_prompt_payloads(self) -> list[dict[str, object]]:
        """Return recent AI payload snapshots."""
        return [dict(item) for item in self._recent_prompt_payloads]

    def _set_last_prompt_payload(self, payload: dict[str, object]) -> None:
        """Persist a bounded in-memory payload history for developer inspection."""
        snapshot = dict(payload)
        self._last_prompt_payload = snapshot
        self._recent_prompt_payloads.append(snapshot)
        if len(self._recent_prompt_payloads) > 20:
            self._recent_prompt_payloads = self._recent_prompt_payloads[-20:]

    def _model(self) -> str:
        """Return the configured model name with a stable default."""
        return str(self.window.settings.get("ai_model", "gemini-3-flash-preview") or "gemini-3-flash-preview")

    def _ai_private_mode_enabled(self) -> bool:
        """Return whether AI private mode is enabled in the current window settings."""
        return bool(self.window.settings.get("ai_private_mode", False))

    def _guard_ai_private_mode(self, title: str) -> bool:
        """Block AI actions when private mode is active and explain why to the user."""
        if not self._ai_private_mode_enabled():
            return False
        QMessageBox.information(
            self.window,
            title,
            "AI private mode is enabled. Disable it in Settings or the AI menu to run AI actions.",
        )
        return True

    def _guard_untrusted_tab_ai(self, title: str) -> bool:
        """Block AI actions for untrusted notes when policy requires it."""
        tab = self.window.active_tab() if hasattr(self.window, "active_tab") else None
        if tab is None:
            return False
        if not bool(profile_setting(self.window.settings, "untrusted_note_block_ai", True)):
            return False
        if str(getattr(tab, "trust_state", "") or "") != "untrusted":
            return False
        QMessageBox.information(
            self.window,
            title,
            "AI actions are blocked for untrusted notes. Trust the note first in File > More > Security.",
        )
        return True

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate token usage for request-size hints and lightweight metrics."""
        return max(1, int(len(text) / 4)) if text else 0

    def _record_ai_metrics(self, *, action: str, prompt: str, response: str, model: str) -> None:
        """Persist lightweight usage metrics and action history for completed AI requests."""
        tokens = self._estimate_tokens(prompt) + self._estimate_tokens(response)
        rate = float(self.window.settings.get("ai_estimated_cost_per_1k_tokens", 0.0005) or 0.0005)
        est_cost = (tokens / 1000.0) * rate
        self._log_ai(
            f"metrics action={action!r} model={model!r} tokens={tokens} est_cost=${est_cost:.6f}"
        )

        if hasattr(self.window, "record_ai_usage"):
            self.window.record_ai_usage(tokens=tokens, estimated_cost=est_cost)

        history = self.window.settings.get("ai_action_history", [])
        if not isinstance(history, list):
            history = []
        history.append(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "action": action,
                "model": model,
                "prompt_chars": len(prompt),
                "response_chars": len(response),
                "prompt_preview": prompt[:160],
                "response_preview": response[:200],
            }
        )
        self.window.settings["ai_action_history"] = history[-300:]
        if hasattr(self.window, "save_settings_to_disk"):
            self.window.save_settings_to_disk()

    def _build_prompt_payload(
        self,
        prompt: str,
        action_title: str,
        *,
        streaming: bool,
        correlation_id: str | None = None,
    ) -> dict[str, object] | None:
        """Build a developer-inspectable snapshot of the prompt assembly process."""
        candidate = prompt.strip()
        if not candidate:
            self._log_ai(f"prepare prompt skipped (empty) action={action_title!r}")
            return None
        self._log_ai(f"prepare prompt action={action_title!r} chars={len(candidate)}")
        app_name = str(QApplication.applicationName() or "Pypad").strip() or "Pypad"
        if self.window.settings.get("ai_last_prompt_app_name") != app_name:
            self.window.settings["ai_last_prompt_app_name"] = app_name
        blocks = [
            self._app_metadata_block,
            self._build_app_knowledge_block(),
            self._build_advanced_personality_block(),
            self._build_runtime_context_block(),
            candidate,
        ]
        assembled = "\n\n".join(part for part in blocks if str(part).strip())
        self._log_ai(
            "prompt assembly "
            f"knowledge_mode={self.window.settings.get('ai_knowledge_mode', 'compact')!r} "
            f"appendix={bool(self.window.settings.get('ai_include_ui_action_appendix', False))} "
            f"user_knowledge_limit={int(self.window.settings.get('ai_user_knowledge_max_chars', 1800) or 1800)} "
            f"selection_preview_limit={int(self.window.settings.get('ai_selection_preview_chars', 240) or 240)} "
            f"assembled_chars={len(assembled)}"
        )
        redacted, changes = sanitize_prompt_text(assembled, self.window.settings)
        api_key, key_source = self._resolve_api_key_with_source()
        payload: dict[str, object] = {
            "timestamp_iso": datetime.now().isoformat(timespec="seconds"),
            "action_title": action_title,
            "raw_prompt": prompt,
            "assembled_prompt": assembled,
            "sent_prompt": redacted,
            "redaction_changes": list(changes),
            "redaction_preview_enabled": bool(self.window.settings.get("ai_preview_redacted_prompt", True)),
            "developer_mode_enabled": bool(self.window.settings.get("developer_mode_enabled", False)),
            "model": self._model(),
            "api_key_source": key_source,
            "api_key_present": bool(api_key),
            "streaming": bool(streaming),
            "sent_chars": len(redacted),
            "correlation_id": correlation_id or "",
            "status": "prepared",
        }
        return payload

    def _prepare_payload_for_dispatch(
        self,
        prompt: str,
        action_title: str,
        *,
        streaming: bool,
        correlation_id: str | None = None,
    ) -> dict[str, object] | None:
        """Prepare a full payload and run the appropriate send preview before dispatch."""
        payload = self._build_prompt_payload(prompt, action_title, streaming=streaming, correlation_id=correlation_id)
        if payload is None:
            return None
        self._set_last_prompt_payload(payload)
        changes = list(payload.get("redaction_changes", []) or [])
        if bool(self.window.settings.get("developer_mode_enabled", False)):
            dialog = AIDeveloperPreviewDialog(self.window, payload)
            if dialog.exec() != QDialog.Accepted:
                self._log_ai(f"developer preview canceled action={action_title!r}")
                self.window.show_status_message("AI request canceled.", 3000)
                payload["status"] = "canceled"
                self._set_last_prompt_payload(payload)
                return None
            self._log_ai(f"developer preview accepted action={action_title!r}")
        elif changes and bool(self.window.settings.get("ai_preview_redacted_prompt", True)):
            dialog = AIRedactionPreviewDialog(
                self.window,
                action_title,
                changes,
                str(payload.get("assembled_prompt", "") or ""),
                str(payload.get("sent_prompt", "") or ""),
            )
            if dialog.exec() != QDialog.Accepted:
                self._log_ai(f"redaction preview canceled action={action_title!r}")
                self.window.show_status_message("AI request canceled by redaction preview.", 3000)
                payload["status"] = "canceled"
                self._set_last_prompt_payload(payload)
                return None
            self._log_ai(f"redaction preview accepted action={action_title!r}")
        payload["status"] = "dispatched"
        self._set_last_prompt_payload(payload)
        return payload

    def _prepare_prompt_for_send(self, prompt: str, action_title: str) -> str | None:
        """Assemble metadata/context blocks and run redaction checks before sending."""
        payload = self._prepare_payload_for_dispatch(prompt, action_title, streaming=False)
        if payload is None:
            return None
        return str(payload.get("sent_prompt", "") or "")

    @staticmethod
    def _probe_internet_connection(timeout_sec: float = 0.25) -> bool:
        """Perform a quick socket probe used to fail fast when the machine is offline."""
        try:
            sock = socket.create_connection(("1.1.1.1", 53), timeout=timeout_sec)
            sock.close()
            return True
        except OSError:
            return False

    def _has_internet_connection(self, timeout_sec: float = 0.25, cache_ttl_sec: float = 5.0) -> bool:
        """Reuse recent connectivity checks so repeated AI actions do not probe every time."""
        now = datetime.now().timestamp()
        if self._connectivity_cache_ok and (now - self._connectivity_cache_checked_at) <= cache_ttl_sec:
            return True
        ok = self._probe_internet_connection(timeout_sec=timeout_sec)
        self._connectivity_cache_ok = ok
        self._connectivity_cache_checked_at = now
        return ok

    def _start_stream_generation(
        self,
        prompt: str,
        action_name: str,
        on_chunk: Callable[[str], None],
        on_done: Callable[[str], None],
        on_error: Callable[[str], None],
        on_cancel: Callable[[str], None] | None = None,
        *,
        debug_correlation_id: str | None = None,
    ) -> bool:
        """Run a streaming AI request and marshal callbacks back onto the UI thread."""
        self._ai_request_counter += 1
        request_id = self._ai_request_counter
        if not self._has_internet_connection():
            self._log_ai(f"stream start blocked (offline) action={action_name!r} id={request_id}")
            on_error("You're offline! Check your connection and try again.")
            return False
        payload = self._prepare_payload_for_dispatch(prompt, action_name, streaming=True, correlation_id=debug_correlation_id)
        if payload is None:
            self._log_ai(f"stream start canceled (prepare failed) action={action_name!r} id={request_id}")
            return False
        prepared_prompt = str(payload.get("sent_prompt", "") or "")
        api_key = self._api_key()
        model = self._model()
        self._log_ai(
            f"stream start action={action_name!r} id={request_id} model={model!r} prompt_chars={len(prepared_prompt)}"
        )
        _LOGGER.debug(
            "AIController stream start action=%r id=%d cid=%r model=%r prompt_chars=%d on_cancel=%s",
            action_name,
            request_id,
            debug_correlation_id,
            model,
            len(prepared_prompt),
            on_cancel is not None,
        )

        thread = QThread(self.window)
        worker = _AIStreamWorker(prepared_prompt, api_key, model)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)

        def _run_ui(action: Callable[[], None]) -> None:
            # Stream worker signals are connected to Python callables; without an explicit
            # receiver object Qt may invoke them on the worker thread. Marshal to UI thread.
            """Schedule a callback to run on the UI thread."""
            QTimer.singleShot(0, self.window, action)

        def _dispatch_chunk(piece: str) -> None:
            """Forward a streamed text chunk to the caller on the UI thread."""
            def _apply() -> None:
                """Invoke the chunk callback on the UI thread."""
                _LOGGER.debug(
                    "AIController stream callback on_chunk action=%r id=%d chars=%d",
                    action_name,
                    request_id,
                    len(piece or ""),
                )
                if debug_correlation_id:
                    _LOGGER.debug("AIController stream callback on_chunk cid=%r", debug_correlation_id)
                on_chunk(piece)

            _run_ui(_apply)

        def _dispatch_done(text: str) -> None:
            """Forward the completed stream result to the caller on the UI thread."""
            def _apply() -> None:
                """Invoke the completion callback on the UI thread."""
                _LOGGER.debug(
                    "AIController stream callback on_done action=%r id=%d cid=%r chars=%d",
                    action_name,
                    request_id,
                    debug_correlation_id,
                    len(text or ""),
                )
                on_done(text)

            _run_ui(_apply)

        def _dispatch_error(message: str) -> None:
            """Forward a stream error to the caller on the UI thread."""
            def _apply() -> None:
                """Invoke the error callback on the UI thread."""
                _LOGGER.debug(
                    "AIController stream callback on_error action=%r id=%d cid=%r message_len=%d",
                    action_name,
                    request_id,
                    debug_correlation_id,
                    len(message or ""),
                )
                on_error(message)

            _run_ui(_apply)

        worker.chunk.connect(_dispatch_chunk)
        worker.chunk.connect(
            lambda piece: _run_ui(
                lambda piece=piece: self._log_ai(
                    f"stream chunk action={action_name!r} id={request_id} chars={len(piece)}"
                )
            )
        )
        worker.finished.connect(
            lambda text: _run_ui(
                lambda text=text: self._record_ai_metrics(action=action_name, prompt=prepared_prompt, response=text, model=model)
            )
        )
        worker.finished.connect(
            lambda text: _run_ui(
                lambda text=text: self._set_last_prompt_payload(
                    {
                        **(self.last_prompt_payload() or {}),
                        "status": "success",
                        "response_chars": len(text or ""),
                    }
                )
            )
        )
        worker.finished.connect(
            lambda text: _run_ui(
                lambda text=text: self._log_ai(
                    f"stream finished action={action_name!r} id={request_id} chars={len(text)}"
                )
            )
        )
        worker.finished.connect(_dispatch_done)
        worker.failed.connect(
            lambda message: _run_ui(
                lambda message=message: self._log_ai(
                    f"stream failed action={action_name!r} id={request_id} error={message!r}"
                )
            )
        )
        worker.failed.connect(
            lambda message: _run_ui(
                lambda message=message: self._set_last_prompt_payload(
                    {
                        **(self.last_prompt_payload() or {}),
                        "status": "error",
                        "error": message,
                    }
                )
            )
        )
        worker.failed.connect(_dispatch_error)
        if on_cancel is not None:
            def _dispatch_cancel(text: str) -> None:
                """Forward a cancellation result to the caller on the UI thread."""
                def _apply() -> None:
                    """Invoke the cancellation callback on the UI thread."""
                    _LOGGER.debug(
                        "AIController stream callback on_cancel action=%r id=%d cid=%r chars=%d",
                        action_name,
                        request_id,
                        debug_correlation_id,
                        len(text or ""),
                    )
                    on_cancel(text)

                _run_ui(_apply)

            worker.cancelled.connect(
                lambda text: _run_ui(
                    lambda text=text: self._log_ai(
                        f"stream cancelled action={action_name!r} id={request_id} chars={len(text)}"
                    )
                )
            )
            worker.cancelled.connect(_dispatch_cancel)
        worker.finished.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(lambda: self._cleanup_thread(thread))
        self._threads.append(thread)
        self._active_stream_worker = worker
        self._active_stream_thread = thread
        self.window.show_status_message(f"AI generating ({model})...", 0)
        _LOGGER.debug("AIController stream thread start action=%r id=%d cid=%r", action_name, request_id, debug_correlation_id)
        thread.start()
        return True

    def _insert_generated_text(self, text: str) -> bool:
        """Insert generated text into the active tab, adding spacing when needed."""
        tab = self.window.active_tab()
        if tab is None:
            return False
        if tab.text_edit.get_text().strip():
            tab.text_edit.insert_text("\n\n")
        tab.text_edit.insert_text(text)
        return True

    def _start_generation(
        self,
        prompt: str,
        result_title: str,
        *,
        action_name: str = "Generate Text",
        auto_insert: bool = False,
        on_result: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        """Run a one-shot AI request and route completion to a dialog or callback."""
        self._ai_request_counter += 1
        request_id = self._ai_request_counter
        if not self._has_internet_connection():
            self._log_ai(f"start blocked (offline) action={action_name!r} id={request_id}")
            QMessageBox.information(
                self.window,
                action_name,
                "You're offline! Check your connection and try again.",
            )
            return
        payload = self._prepare_payload_for_dispatch(prompt, action_name, streaming=False)
        if payload is None:
            self._log_ai(f"start canceled (prepare failed) action={action_name!r} id={request_id}")
            return
        prepared_prompt = str(payload.get("sent_prompt", "") or "")
        api_key = self._api_key()
        model = self._model()
        self._log_ai(
            f"start action={action_name!r} id={request_id} model={model!r} prompt_chars={len(prepared_prompt)}"
        )

        thread = QThread(self.window)
        worker = _AIWorker(prepared_prompt, api_key, model)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(
            lambda text: self._record_ai_metrics(action=action_name, prompt=prepared_prompt, response=text, model=model)
        )
        worker.finished.connect(
            lambda text: self._log_ai(
                f"finished action={action_name!r} id={request_id} chars={len(text)}"
            )
        )
        worker.finished.connect(
            lambda text: self._set_last_prompt_payload(
                {
                    **(self.last_prompt_payload() or {}),
                    "status": "success",
                    "response_chars": len(text or ""),
                }
            )
        )
        worker.finished.connect(lambda text: self._on_result(thread, result_title, text, auto_insert, on_result=on_result))
        if on_error is None:
            worker.failed.connect(
                lambda message: self._log_ai(
                    f"failed action={action_name!r} id={request_id} error={message!r}"
                )
            )
            worker.failed.connect(
                lambda message: self._set_last_prompt_payload(
                    {
                        **(self.last_prompt_payload() or {}),
                        "status": "error",
                        "error": message,
                    }
                )
            )
            worker.failed.connect(lambda message: self._on_error(thread, message, result_title, model))
        else:
            worker.failed.connect(
                lambda message: self._log_ai(
                    f"failed action={action_name!r} id={request_id} error={message!r}"
                )
            )
            worker.failed.connect(
                lambda message: self._set_last_prompt_payload(
                    {
                        **(self.last_prompt_payload() or {}),
                        "status": "error",
                        "error": message,
                    }
                )
            )
            worker.failed.connect(on_error)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(lambda: self._cleanup_thread(thread))
        self._threads.append(thread)
        self.window.show_status_message(f"AI generating ({model})...", 0)
        thread.start()

    def _cleanup_thread(self, thread: QThread) -> None:
        """Remove completed worker threads from controller state and reset status UI."""
        if thread in self._threads:
            self._threads.remove(thread)
        if thread is self._active_stream_thread:
            self._active_stream_thread = None
            self._active_stream_worker = None
        thread.deleteLater()
        self._log_ai("generation thread cleaned up")
        self.window.show_status_message("AI generation finished.", 3000)

    def _on_result(
        self,
        _thread: QThread,
        title: str,
        text: str,
        auto_insert: bool,
        on_result: Callable[[str], None] | None = None,
    ) -> None:
        """Process the result."""
        self._log_ai(f"result delivered title={title!r} chars={len(text)} auto_insert={auto_insert}")
        if on_result is not None:
            on_result(text)
            return
        if auto_insert and self._insert_generated_text(text):
            self.window.show_status_message("Generated text inserted into current tab.", 3000)
        dialog = AIResultDialog(self.window, title, text)
        dialog.exec()

    def _on_error(self, _thread: QThread, message: str, action_title: str, model: str) -> None:
        """Convert worker failures into a detailed user-facing error dialog."""
        self._log_ai(f"error action={action_title!r} model={model!r} message={message!r}")
        self._show_error_with_details(
            title="Error Generating Text",
            summary=f"Error generating text for '{action_title}'.",
            details=f"Model: {model}\n\n{message}",
        )

    def _show_error_with_details(self, title: str, summary: str, details: str) -> None:
        """Display a critical message box with expandable technical details."""
        box = QMessageBox(self.window)
        box.setWindowTitle(title)
        box.setIcon(QMessageBox.Critical)
        box.setText(summary)
        box.setInformativeText("Open 'Show Details...' for technical information.")
        box.setDetailedText(details)
        box.setStandardButtons(QMessageBox.Ok)
        box.exec()

    def ask_ai(self) -> None:
        """Open the main AI entry point, preferring the chat dock when available."""
        if self._guard_ai_private_mode("Ask AI"):
            return
        if self._guard_untrusted_tab_ai("Ask AI"):
            return
        if hasattr(self.window, "toggle_ai_chat_panel"):
            self.window.toggle_ai_chat_panel(True)
            return
        prompt, ok = QInputDialog.getMultiLineText(self.window, "Ask AI", "Prompt:")
        if not ok or not prompt.strip():
            return
        self._start_generation(prompt, "AI Response", action_name="Ask AI")

    def explain_selection(self) -> None:
        """Ask the model to explain the current text selection."""
        if self._guard_ai_private_mode("Explain Selection"):
            return
        if self._guard_untrusted_tab_ai("Explain Selection"):
            return
        tab = self.window.active_tab()
        if tab is None:
            return
        selected = tab.text_edit.selected_text().strip()
        if not selected:
            QMessageBox.information(self.window, "Explain Selection", "Select text first.")
            return
        prompt = f"Explain this text: {selected}"
        self._start_generation(prompt, "AI Explanation", action_name="Explain Selection")

    def generate_to_tab(self) -> None:
        """Prompt for free-form generation and insert the result into the current tab."""
        if self._guard_ai_private_mode("Generate Text"):
            return
        if self._guard_untrusted_tab_ai("Generate Text"):
            return
        tab = self.window.active_tab()
        if tab is None:
            QMessageBox.information(self.window, "Generate Text", "Open a tab first.")
            return
        prompt, ok = QInputDialog.getMultiLineText(self.window, "Generate Text", "Prompt:")
        if not ok or not prompt.strip():
            return
        self._start_generation(prompt, "Generated Text", action_name="Generate To Tab", auto_insert=True)

    def rewrite_selection(self, mode: str) -> None:
        """Stream an AI rewrite for the current selection, with preview/approval support."""
        if self._guard_ai_private_mode("AI Rewrite"):
            return
        if self._guard_untrusted_tab_ai("AI Rewrite"):
            return
        tab = self.window.active_tab()
        if tab is None:
            return
        selected = tab.text_edit.selected_text().strip()
        if not selected:
            QMessageBox.information(self.window, "AI Rewrite", "Select text first.")
            return
        prompts = {
            "shorten": "Rewrite the text to be concise while preserving meaning.",
            "formal": "Rewrite the text in a formal professional tone.",
            "fix_grammar": "Fix grammar and punctuation while preserving tone.",
            "summarize": "Summarize this text into a concise version.",
        }
        dialog = AIRewritePromptDialog(self.window, selected[:800], prompts)
        try:
            dialog.mode_combo.setCurrentText(mode)
        except Exception:
            pass
        if dialog.exec() != QDialog.Accepted:
            return
        instruction = dialog.instruction() or prompts.get(mode, "Rewrite the text.")
        prompt = f"{instruction}\n\nText:\n{selected}"

        progress = QProgressDialog("AI rewrite in progress...", "Cancel", 0, 0, self.window)
        progress.setWindowTitle("AI Rewrite")
        progress.setWindowModality(Qt.NonModal)
        progress.setCancelButtonText("Cancel")
        progress.setMinimumDuration(0)
        progress.show()
        progress.canceled.connect(self.cancel_active_chat_request)

        def _run_ui(action: Callable[[], None]) -> None:
            """Run UI."""
            QTimer.singleShot(0, self.window, action)

        def on_rewrite_result(result: str) -> None:
            """Process the rewrite result."""
            progress.close()
            progress.deleteLater()
            requires_approval = bool(self.window.settings.get("ai_rewrite_require_approval", True))
            if requires_approval:
                preview = AIEditPreviewDialog(self.window, selected, result, title=f"AI Rewrite Preview ({mode})")
                if preview.exec() != QDialog.Accepted:
                    return
                final_text = preview.final_text
            else:
                final_text = result
            QApplication.clipboard().setText(final_text)
            tab.text_edit.replace_selection(final_text)
            self.window.show_status_message("AI rewrite applied (copied to clipboard).", 3000)

        def on_rewrite_error(message: str) -> None:
            """Process the rewrite error."""
            def _apply() -> None:
                """Close progress UI and report the rewrite failure."""
                progress.close()
                progress.deleteLater()
                model = self._model()
                self._on_error(self._active_stream_thread, message, f"AI Rewrite ({mode})", model)

            _run_ui(_apply)

        chunks: list[str] = []

        def on_chunk(piece: str) -> None:
            """Process an incoming streamed chunk."""
            if piece:
                chunks.append(piece)

        def on_cancel(partial: str) -> None:
            """Process cancellation."""
            def _apply() -> None:
                """Close progress UI after the rewrite is canceled."""
                progress.close()
                progress.deleteLater()
                self.window.show_status_message("AI rewrite canceled.", 3000)

            _run_ui(_apply)

        def on_done(text: str) -> None:
            """Finalize the stream after completion."""
            if not text and chunks:
                text = "".join(chunks).strip()
            _run_ui(lambda: on_rewrite_result(text))

        self._start_stream_generation(
            prompt,
            action_name=f"Rewrite Selection ({mode})",
            on_chunk=on_chunk,
            on_done=on_done,
            on_error=on_rewrite_error,
            on_cancel=on_cancel,
        )

    def ask_about_context(self) -> None:
        """Ask a question about the active file using its current contents as context."""
        if self._guard_ai_private_mode("Ask About File"):
            return
        if self._guard_untrusted_tab_ai("Ask About File"):
            return
        tab = self.window.active_tab()
        if tab is None:
            QMessageBox.information(self.window, "Ask About File", "Open a tab first.")
            return
        question, ok = QInputDialog.getMultiLineText(self.window, "Ask About File", "Question:")
        if not ok or not question.strip():
            return
        file_name = tab.current_file or "Untitled"
        content = tab.text_edit.get_text()
        context = content[:20000]
        prompt = (
            f"You are helping with the current file.\n"
            f"File: {file_name}\n\n"
            f"Question:\n{question.strip()}\n\n"
            f"File contents (possibly truncated):\n{context}"
        )
        self._start_generation(prompt, "AI File Context Answer", action_name="Ask About File")

    def ask_ai_chat(
        self,
        prompt: str,
        on_chunk: Callable[[str], None],
        on_done: Callable[[str], None],
        on_error: Callable[[str], None],
        on_cancel: Callable[[str], None] | None = None,
        *,
        debug_correlation_id: str | None = None,
    ) -> bool:
        """Submit a chat-style AI request whose output is consumed incrementally by the caller."""
        if self._guard_ai_private_mode("AI Chat"):
            return False
        if self._guard_untrusted_tab_ai("AI Chat"):
            return False
        _LOGGER.debug(
            "AIController.ask_ai_chat prompt_chars=%d on_cancel=%s cid=%r",
            len(prompt or ""),
            on_cancel is not None,
            debug_correlation_id,
        )
        return self._start_stream_generation(
            prompt,
            "AI Chat",
            on_chunk,
            on_done,
            on_error,
            on_cancel=on_cancel,
            debug_correlation_id=debug_correlation_id,
        )

    def cancel_active_chat_request(self) -> bool:
        """Request cancellation of the active streaming chat job, if one exists."""
        if self._active_stream_worker is None:
            _LOGGER.debug("AIController.cancel_active_chat_request no active stream")
            return False
        self._log_ai("cancel requested for active stream")
        _LOGGER.debug("AIController.cancel_active_chat_request dispatching cancel to active worker")
        self._active_stream_worker.cancel()
        self.window.show_status_message("AI generation cancel requested.", 2000)
        return True

