"""Normalize raw settings values into the concrete Python types expected by the rest of the application.

This module belongs to the application settings layer that resolves defaults, storage paths, and preference migrations. It helps explain how `pypad.app_settings` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from .defaults import build_default_settings
from .notepadpp_prefs import coerce_notepadpp_prefs
from .scintilla_profile import ScintillaProfile
from pypad.ui.security.security_profile import (
    BUILTIN_SECURITY_PROFILES,
    PROFILE_SCOPED_SETTING_KEYS,
    coerce_security_profile_overrides,
)

def coerce_bool(value, default: bool = False) -> bool:
    """Coerce bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off", ""}:
            return False
    return default


def coerce_str(value, default: str = "") -> str:
    """Coerce a value into a string with a fallback."""
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def normalize_ui_visibility_settings(settings: dict) -> dict:
    """Normalize UI visibility settings."""
    settings["show_markdown_toolbar"] = coerce_bool(
        settings.get("show_markdown_toolbar", False),
        default=False,
    )
    settings["markdown_math_preview_enabled"] = coerce_bool(
        settings.get("markdown_math_preview_enabled", False),
        default=False,
    )
    settings["show_find_panel"] = coerce_bool(
        settings.get("show_find_panel", False),
        default=False,
    )
    return settings


def _coerce_enum(value: object, allowed: set[str], default: str) -> str:
    """Coerce enum."""
    text = str(value or "").strip().lower()
    return text if text in allowed else default


def _coerce_int_clamped(value: object, default: int, min_value: int, max_value: int) -> int:
    """Coerce int clamped."""
    try:
        num = int(value)  # type: ignore[arg-type]
    except Exception:
        num = default
    return max(min_value, min(max_value, num))


def _coerce_hex(value: object, default: str) -> str:
    """Coerce hex."""
    text = str(value or "").strip()
    if not text:
        return default
    if not text.startswith("#"):
        text = f"#{text}"
    if len(text) not in (4, 7):
        return default
    if not all(ch in "0123456789abcdefABCDEF" for ch in text[1:]):
        return default
    return text


def _coerce_logging_level(value: object, default: str = "INFO") -> str:
    """Coerce logging level."""
    allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    text = str(value or "").strip().upper()
    return text if text in allowed else default


def _coerce_float_clamped(value: object, default: float, min_value: float, max_value: float) -> float:
    """Coerce float clamped."""
    try:
        num = float(value)  # type: ignore[arg-type]
    except Exception:
        num = default
    return max(min_value, min(max_value, num))


def _coerce_cmd_list(value: object, default: list[str]) -> list[str]:
    """Coerce cmd list."""
    if isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
        cleaned = [item for item in items if item]
        return cleaned or list(default)
    if isinstance(value, (list, tuple)):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned or list(default)
    return list(default)


def _coerce_str_list(value: object) -> list[str]:
    """Coerce str list."""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _coerce_str_dict(value: object) -> dict[str, str]:
    """Coerce a flat string dictionary."""
    if not isinstance(value, dict):
        return {}
    return {str(k).strip(): str(v).strip() for k, v in value.items() if str(k).strip()}


def _sanitize_update_feed_url(value: object, default: str) -> str:
    """Sanitize update feed url."""
    raw = str(value or "").strip() or default
    if "neogl1tch20server" in raw or raw.endswith("/updates/notepad.xml"):
        raw = default
    try:
        parts = urlsplit(raw)
    except Exception:
        return default
    if not parts.scheme or not parts.netloc:
        return default
    return raw


def migrate_settings(settings: dict) -> dict:
    """Migrate settings."""
    current = dict(settings)
    defaults = build_default_settings(default_style="Windows", font_family="Segoe UI", font_size=11)
    schema = _coerce_int_clamped(current.get("settings_schema_version", 1), 1, 1, 999)
    if schema >= 2:
        current["local_history_persist_enabled"] = coerce_bool(current.get("local_history_persist_enabled", True), True)
        current["crash_snapshot_enabled"] = coerce_bool(current.get("crash_snapshot_enabled", True), True)
        current["page_layout_view_enabled"] = coerce_bool(current.get("page_layout_view_enabled", False), False)
        current["page_layout_margin_left_mm"] = _coerce_int_clamped(current.get("page_layout_margin_left_mm", 18), 18, 5, 80)
        current["page_layout_margin_top_mm"] = _coerce_int_clamped(current.get("page_layout_margin_top_mm", 18), 18, 5, 80)
        current["page_layout_margin_right_mm"] = _coerce_int_clamped(current.get("page_layout_margin_right_mm", 18), 18, 5, 80)
        current["page_layout_margin_bottom_mm"] = _coerce_int_clamped(current.get("page_layout_margin_bottom_mm", 18), 18, 5, 80)
        current["page_layout_header_text"] = str(current.get("page_layout_header_text", "") or "")
        current["page_layout_footer_text"] = str(current.get("page_layout_footer_text", "") or "")
        current["page_layout_show_ruler"] = coerce_bool(current.get("page_layout_show_ruler", True), True)
        current["page_layout_show_page_breaks"] = coerce_bool(current.get("page_layout_show_page_breaks", True), True)
        current["track_changes_enabled"] = coerce_bool(current.get("track_changes_enabled", False), False)
        current["large_file_fast_open_enabled"] = coerce_bool(current.get("large_file_fast_open_enabled", True), True)
        current["large_file_fast_open_kb"] = _coerce_int_clamped(current.get("large_file_fast_open_kb", 8192), 8192, 1024, 102400)
        current["large_file_preview_head_lines"] = _coerce_int_clamped(current.get("large_file_preview_head_lines", 2000), 2000, 200, 50000)
        current["large_file_preview_tail_lines"] = _coerce_int_clamped(current.get("large_file_preview_tail_lines", 250), 250, 50, 10000)
        current["collab_presence_timeout_sec"] = _coerce_int_clamped(current.get("collab_presence_timeout_sec", 120), 120, 20, 3600)
        current["ai_workspace_qa_max_files"] = _coerce_int_clamped(current.get("ai_workspace_qa_max_files", 10), 10, 1, 40)
        current["ai_workspace_qa_max_lines_per_file"] = _coerce_int_clamped(
            current.get("ai_workspace_qa_max_lines_per_file", 60), 60, 10, 200
        )
        current["ai_app_knowledge_override"] = str(current.get("ai_app_knowledge_override", "") or "")
        current["ai_personality_advanced"] = str(current.get("ai_personality_advanced", "") or "")
        current["lsp_definition_enabled"] = coerce_bool(current.get("lsp_definition_enabled", True), True)
        current["lsp_definition_initialize_timeout_sec"] = _coerce_float_clamped(
            current.get("lsp_definition_initialize_timeout_sec", 5.0),
            5.0,
            0.5,
            30.0,
        )
        current["lsp_definition_request_timeout_sec"] = _coerce_float_clamped(
            current.get("lsp_definition_request_timeout_sec", 3.0),
            3.0,
            0.5,
            30.0,
        )
        current["lsp_definition_retries"] = _coerce_int_clamped(current.get("lsp_definition_retries", 2), 2, 0, 5)
        current["lsp_definition_verbose_logging"] = coerce_bool(current.get("lsp_definition_verbose_logging", False), False)
        current["lsp_python_servers"] = _coerce_cmd_list(
            current.get("lsp_python_servers"),
            list(defaults.get("lsp_python_servers", [])),
        )
        current["lsp_javascript_servers"] = _coerce_cmd_list(
            current.get("lsp_javascript_servers"),
            list(defaults.get("lsp_javascript_servers", [])),
        )
        current["lsp_typescript_servers"] = _coerce_cmd_list(
            current.get("lsp_typescript_servers"),
            list(defaults.get("lsp_typescript_servers", [])),
        )
        current["save_debug_logs_to_appdata"] = coerce_bool(current.get("save_debug_logs_to_appdata", False), False)
        current["logging_level"] = _coerce_logging_level(current.get("logging_level", "INFO"))
        current["developer_mode_enabled"] = coerce_bool(current.get("developer_mode_enabled", False), False)
        current["gamification_enabled"] = coerce_bool(current.get("gamification_enabled", True), True)
        current["session_review_enabled"] = coerce_bool(current.get("session_review_enabled", False), False)
        custom_events = current.get("gamification_custom_events", [])
        current["gamification_custom_events"] = custom_events if isinstance(custom_events, list) else []
        gamification_state = current.get("gamification_state", {})
        current["gamification_state"] = gamification_state if isinstance(gamification_state, dict) else {}
        current["onboarding_enabled"] = coerce_bool(current.get("onboarding_enabled", True), True)
        current["onboarding_contextual_tips_enabled"] = coerce_bool(
            current.get("onboarding_contextual_tips_enabled", True),
            True,
        )
        current["onboarding_next_unlock_prompts_enabled"] = coerce_bool(
            current.get("onboarding_next_unlock_prompts_enabled", True),
            True,
        )
        onboarding_state = current.get("onboarding_state", {})
        current["onboarding_state"] = onboarding_state if isinstance(onboarding_state, dict) else {}
        current["backup_output_dir"] = str(current.get("backup_output_dir", "") or "").strip()
        current["update_feed_url"] = _sanitize_update_feed_url(current.get("update_feed_url"), defaults.get("update_feed_url", ""))
        current["fast_startup_mode"] = coerce_bool(current.get("fast_startup_mode", True), True)
        current["plugin_max_failures_before_disable"] = _coerce_int_clamped(
            current.get("plugin_max_failures_before_disable", 3),
            3,
            1,
            20,
        )
        current["status_show_selection_stats"] = coerce_bool(current.get("status_show_selection_stats", True), True)
        current["ai_knowledge_mode"] = _coerce_enum(current.get("ai_knowledge_mode"), {"compact", "full"}, "compact")
        current["ai_include_ui_action_appendix"] = coerce_bool(current.get("ai_include_ui_action_appendix", False), False)
        current["ai_user_knowledge_max_chars"] = _coerce_int_clamped(
            current.get("ai_user_knowledge_max_chars", 1800),
            1800,
            200,
            12000,
        )
        current["ai_selection_preview_chars"] = _coerce_int_clamped(
            current.get("ai_selection_preview_chars", 240),
            240,
            80,
            5000,
        )
        current["spellcheck_enabled"] = coerce_bool(current.get("spellcheck_enabled", True), True)
        current["spellcheck_language"] = str(current.get("spellcheck_language", "en") or "en").strip().lower() or "en"
        raw_dict = current.get("spellcheck_user_dictionary", [])
        if isinstance(raw_dict, str):
            current["spellcheck_user_dictionary"] = sorted({part.strip().lower() for part in raw_dict.split(",") if part.strip()})
        elif isinstance(raw_dict, list):
            current["spellcheck_user_dictionary"] = sorted({str(part).strip().lower() for part in raw_dict if str(part).strip()})
        else:
            current["spellcheck_user_dictionary"] = []
        current["writing_tools_use_language_tool"] = coerce_bool(current.get("writing_tools_use_language_tool", True), True)
        current["writing_tools_detect_repeated_words"] = coerce_bool(current.get("writing_tools_detect_repeated_words", True), True)
        current["writing_tools_detect_spacing"] = coerce_bool(current.get("writing_tools_detect_spacing", True), True)
        current["writing_tools_detect_capitalization"] = coerce_bool(current.get("writing_tools_detect_capitalization", True), True)
        current["writing_tools_detect_weak_phrases"] = coerce_bool(current.get("writing_tools_detect_weak_phrases", True), True)
        current["writing_tools_paraphrase_reduce_passive"] = coerce_bool(
            current.get("writing_tools_paraphrase_reduce_passive", True), True
        )
        current["writing_tools_humanizer_break_long_sentences"] = coerce_bool(
            current.get("writing_tools_humanizer_break_long_sentences", True), True
        )
        current["writing_tools_ai_detector_sensitivity"] = _coerce_float_clamped(
            current.get("writing_tools_ai_detector_sensitivity", 1.0), 1.0, 0.5, 1.5
        )
        current["writing_tools_ai_sentence_threshold"] = _coerce_int_clamped(
            current.get("writing_tools_ai_sentence_threshold", 24), 24, 8, 60
        )
        current["writing_tools_ai_unique_ratio_threshold"] = _coerce_float_clamped(
            current.get("writing_tools_ai_unique_ratio_threshold", 0.42), 0.42, 0.1, 0.9
        )
        current["writing_tools_package_download_cache"] = (
            dict(current.get("writing_tools_package_download_cache", {}))
            if isinstance(current.get("writing_tools_package_download_cache", {}), dict)
            else {}
        )
        current["writing_tools_runtime_download_cache"] = (
            dict(current.get("writing_tools_runtime_download_cache", {}))
            if isinstance(current.get("writing_tools_runtime_download_cache", {}), dict)
            else {}
        )
        current["tool_state"] = dict(current.get("tool_state", {})) if isinstance(current.get("tool_state", {}), dict) else {}
        current["tool_help_dismissed"] = {
            str(k).strip(): coerce_bool(v, False)
            for k, v in dict(current.get("tool_help_dismissed", {})).items()
            if str(k).strip()
        } if isinstance(current.get("tool_help_dismissed", {}), dict) else {}
        current["world_clock_zones"] = _coerce_str_list(current.get("world_clock_zones")) or ["UTC"]
        current["task_lists"] = dict(current.get("task_lists", {})) if isinstance(current.get("task_lists", {}), dict) else {}
        current["currency_rates_cache"] = dict(current.get("currency_rates_cache", {})) if isinstance(current.get("currency_rates_cache", {}), dict) else {}
        current["currency_rates_last_sync"] = str(current.get("currency_rates_last_sync", "") or "").strip()
        current["currency_rates_source"] = str(current.get("currency_rates_source", "bundled") or "bundled").strip().lower() or "bundled"
        current["reader_mode_defaults"] = _coerce_str_dict(current.get("reader_mode_defaults"))
        closed_tab_history = current.get("closed_tab_history", [])
        current["closed_tab_history"] = closed_tab_history if isinstance(closed_tab_history, list) else []
        normalize_ui_visibility_settings(current)
        ScintillaProfile.from_settings(current).apply_to_settings(current)
        return coerce_notepadpp_prefs(current)

    for key, value in defaults.items():
        current.setdefault(key, value)

    current["show_main_toolbar"] = coerce_bool(current.get("show_main_toolbar", True), True)
    current["show_markdown_toolbar"] = coerce_bool(current.get("show_markdown_toolbar", False), False)
    current["show_find_panel"] = coerce_bool(current.get("show_find_panel", False), False)
    current["ui_density"] = _coerce_enum(current.get("ui_density"), {"compact", "comfortable"}, "comfortable")
    current["icon_size_px"] = _coerce_int_clamped(current.get("icon_size_px", 18), 18, 16, 24)
    current["toolbar_label_mode"] = _coerce_enum(
        current.get("toolbar_label_mode"),
        {"icons_only", "text_only", "icons_text"},
        "icons_only",
    )

    current["tab_width"] = _coerce_int_clamped(current.get("tab_width", 4), 4, 2, 8)
    current["insert_spaces"] = coerce_bool(current.get("insert_spaces", True), True)
    current["auto_indent"] = coerce_bool(current.get("auto_indent", True), True)
    current["trim_trailing_whitespace_on_save"] = coerce_bool(
        current.get("trim_trailing_whitespace_on_save", False), False
    )
    current["caret_width_px"] = _coerce_int_clamped(current.get("caret_width_px", 1), 1, 1, 4)
    current["highlight_current_line"] = coerce_bool(current.get("highlight_current_line", True), True)

    current["tab_close_button_mode"] = _coerce_enum(current.get("tab_close_button_mode"), {"always", "hover"}, "always")
    current["tab_elide_mode"] = _coerce_enum(current.get("tab_elide_mode"), {"right", "middle", "none"}, "right")
    current["tab_min_width_px"] = _coerce_int_clamped(current.get("tab_min_width_px", 120), 120, 80, 220)
    current["tab_max_width_px"] = _coerce_int_clamped(current.get("tab_max_width_px", 240), 240, 120, 420)
    current["tab_double_click_action"] = _coerce_enum(
        current.get("tab_double_click_action"),
        {"new_tab", "rename", "none"},
        "new_tab",
    )

    current["workspace_show_hidden_files"] = coerce_bool(current.get("workspace_show_hidden_files", False), False)
    current["workspace_follow_symlinks"] = coerce_bool(current.get("workspace_follow_symlinks", False), False)
    current["workspace_max_scan_files"] = _coerce_int_clamped(
        current.get("workspace_max_scan_files", 25000), 25000, 1000, 200000
    )
    raw_profiles = current.get("workspace_profiles", {})
    cleaned_profiles: dict[str, dict[str, object]] = {}
    if isinstance(raw_profiles, dict):
        for key, value in raw_profiles.items():
            name = str(key).strip()
            if not name or not isinstance(value, dict):
                continue
            root = str(value.get("root", "") or "").strip()
            if not root:
                continue
            cleaned_profiles[name] = {
                "root": root,
                "restore_session": coerce_bool(value.get("restore_session", True), True),
            }
    current["workspace_profiles"] = cleaned_profiles
    current["workspace_startup_picker_enabled"] = coerce_bool(
        current.get("workspace_startup_picker_enabled", False),
        False,
    )
    current["workspace_startup_last_profile"] = str(current.get("workspace_startup_last_profile", "") or "").strip()
    profile_id = str(current.get("security_profile_id", "balanced") or "balanced").strip().lower()
    current["security_profile_id"] = profile_id if profile_id in BUILTIN_SECURITY_PROFILES else "balanced"
    current["security_profile_custom_overrides"] = coerce_security_profile_overrides(
        current.get("security_profile_custom_overrides", {})
    )
    current["security_profile_first_run_acknowledged"] = coerce_bool(
        current.get("security_profile_first_run_acknowledged", False),
        False,
    )
    raw_profile_states = current.get("security_profile_states", {})
    cleaned_profile_states: dict[str, dict[str, object]] = {}
    if isinstance(raw_profile_states, dict):
        for key, value in raw_profile_states.items():
            profile_name = str(key or "").strip().lower()
            if profile_name not in BUILTIN_SECURITY_PROFILES or not isinstance(value, dict):
                continue
            profile_state: dict[str, object] = {}
            for state_key, state_value in value.items():
                name = str(state_key or "").strip()
                if name in PROFILE_SCOPED_SETTING_KEYS:
                    profile_state[name] = state_value
            if "security_profile_custom_overrides" in profile_state:
                profile_state["security_profile_custom_overrides"] = coerce_security_profile_overrides(
                    profile_state.get("security_profile_custom_overrides", {})
                )
            cleaned_profile_states[profile_name] = profile_state
    current["security_profile_states"] = cleaned_profile_states
    current["file_trust_prompt_on_external_open"] = coerce_bool(
        current.get("file_trust_prompt_on_external_open", True),
        True,
    )
    current["file_trust_persist_session_only_default"] = coerce_bool(
        current.get("file_trust_persist_session_only_default", True),
        True,
    )
    current["trust_known_workspace_files"] = coerce_bool(current.get("trust_known_workspace_files", True), True)
    trust_store = current.get("file_trust_store", {})
    if isinstance(trust_store, dict):
        cleaned_trust_store: dict[str, dict[str, object]] = {}
        for key, value in trust_store.items():
            if not isinstance(value, dict):
                continue
            path = str(key or "").strip()
            if not path:
                continue
            cleaned_trust_store[path] = {
                "state": str(value.get("state", "") or ""),
                "source": str(value.get("source", "") or ""),
                "persisted_at": str(value.get("persisted_at", "") or ""),
                "profile_id": str(value.get("profile_id", "") or ""),
                "last_seen_mtime_ns": value.get("last_seen_mtime_ns"),
                "last_seen_size": value.get("last_seen_size"),
            }
        current["file_trust_store"] = cleaned_trust_store
    else:
        current["file_trust_store"] = {}

    current["search_default_match_case"] = coerce_bool(current.get("search_default_match_case", False), False)
    current["search_default_whole_word"] = coerce_bool(current.get("search_default_whole_word", False), False)
    current["search_default_regex"] = coerce_bool(current.get("search_default_regex", False), False)
    current["search_highlight_color"] = _coerce_hex(current.get("search_highlight_color", "#4a90e2"), "#4a90e2")
    current["search_max_highlights"] = _coerce_int_clamped(current.get("search_max_highlights", 2000), 2000, 100, 10000)

    current["shortcut_profile"] = _coerce_enum(current.get("shortcut_profile"), {"default", "vscode"}, "vscode")
    current["shortcut_conflict_policy"] = _coerce_enum(
        current.get("shortcut_conflict_policy"),
        {"warn", "block", "allow"},
        "warn",
    )
    current["shortcut_show_unassigned"] = coerce_bool(current.get("shortcut_show_unassigned", True), True)
    raw_map = current.get("shortcut_map", {})
    cleaned_map: dict[str, str | list[str]] = {}
    if isinstance(raw_map, dict):
        for key, value in raw_map.items():
            if not isinstance(key, str) or not key.strip():
                continue
            if isinstance(value, str):
                cleaned_map[key] = value.strip()
            elif isinstance(value, list):
                seqs = [str(v).strip() for v in value if str(v).strip()]
                cleaned_map[key] = seqs
    current["shortcut_map"] = cleaned_map
    trusted_hashes = current.get("trusted_plugin_hashes", {})
    if isinstance(trusted_hashes, dict):
        current["trusted_plugin_hashes"] = {
            str(k): str(v).strip().lower() for k, v in trusted_hashes.items() if str(k).strip() and str(v).strip()
        }
    else:
        current["trusted_plugin_hashes"] = {}
    raw_quarantine = current.get("quarantined_plugins", [])
    if isinstance(raw_quarantine, list):
        current["quarantined_plugins"] = sorted({str(x).strip() for x in raw_quarantine if str(x).strip()})
    else:
        current["quarantined_plugins"] = []
    current["plugin_startup_safe_mode"] = coerce_bool(current.get("plugin_startup_safe_mode", False), False)
    current["defer_plugin_load_on_startup"] = coerce_bool(current.get("defer_plugin_load_on_startup", True), True)
    current["plugin_startup_defer_ms"] = _coerce_int_clamped(
        current.get("plugin_startup_defer_ms", 1200),
        1200,
        0,
        15000,
    )
    current["fast_startup_mode"] = coerce_bool(current.get("fast_startup_mode", True), True)
    current["plugin_max_failures_before_disable"] = _coerce_int_clamped(
        current.get("plugin_max_failures_before_disable", 3),
        3,
        1,
        20,
    )
    current["plugin_allow_unsafe_ui_bridge"] = coerce_bool(current.get("plugin_allow_unsafe_ui_bridge", False), False)
    current["plugin_runtime_policy"] = _coerce_enum(
        current.get("plugin_runtime_policy"),
        {"built_in_only", "signed_only", "unsigned_local_allowed"},
        "signed_only",
    )
    current["plugin_online_catalog_url"] = str(
        current.get(
            "plugin_online_catalog_url",
            "https://raw.githubusercontent.com/ne0gl1tch20/pypad/main/online_plugins/catalog.json",
        )
        or ""
    )
    current["status_show_position"] = coerce_bool(current.get("status_show_position", True), True)
    current["status_show_zoom"] = coerce_bool(current.get("status_show_zoom", True), True)
    current["status_show_eol"] = coerce_bool(current.get("status_show_eol", True), True)
    current["status_show_encoding"] = coerce_bool(current.get("status_show_encoding", True), True)
    current["status_show_syntax"] = coerce_bool(current.get("status_show_syntax", True), True)
    current["status_show_breadcrumb"] = coerce_bool(current.get("status_show_breadcrumb", True), True)
    current["status_show_ruler"] = coerce_bool(current.get("status_show_ruler", True), True)
    current["status_show_selection_stats"] = coerce_bool(current.get("status_show_selection_stats", True), True)
    current["status_show_ai_usage"] = coerce_bool(current.get("status_show_ai_usage", True), True)
    current["status_show_autosave"] = coerce_bool(current.get("status_show_autosave", True), True)
    current["status_show_gamification"] = coerce_bool(current.get("status_show_gamification", False), False)
    current["status_show_momentum"] = coerce_bool(current.get("status_show_momentum", False), False)
    current["tool_state"] = dict(current.get("tool_state", {})) if isinstance(current.get("tool_state", {}), dict) else {}
    current["tool_help_dismissed"] = {
        str(k).strip(): coerce_bool(v, False)
        for k, v in dict(current.get("tool_help_dismissed", {})).items()
        if str(k).strip()
    } if isinstance(current.get("tool_help_dismissed", {}), dict) else {}
    current["world_clock_zones"] = _coerce_str_list(current.get("world_clock_zones")) or ["UTC"]
    current["task_lists"] = dict(current.get("task_lists", {})) if isinstance(current.get("task_lists", {}), dict) else {}
    current["currency_rates_cache"] = dict(current.get("currency_rates_cache", {})) if isinstance(current.get("currency_rates_cache", {}), dict) else {}
    current["currency_rates_last_sync"] = str(current.get("currency_rates_last_sync", "") or "").strip()
    current["currency_rates_source"] = str(current.get("currency_rates_source", "bundled") or "bundled").strip().lower() or "bundled"
    current["reader_mode_defaults"] = _coerce_str_dict(current.get("reader_mode_defaults"))
    current["accessibility_preset"] = coerce_str(current.get("accessibility_preset", "none"), "none").strip().lower() or "none"
    current["accessibility_reduce_motion"] = coerce_bool(current.get("accessibility_reduce_motion", False), False)
    current["accessibility_cursor_blink"] = coerce_bool(current.get("accessibility_cursor_blink", True), True)
    current["accessibility_cursor_blink_rate_ms"] = _coerce_int_clamped(
        current.get("accessibility_cursor_blink_rate_ms", 1000),
        1000,
        200,
        2500,
    )

    current["ai_redaction_profile_default"] = _coerce_enum(
        current.get("ai_redaction_profile_default"),
        {"strict", "standard", "off"},
        "strict",
    )
    current["ai_send_redact_emails"] = coerce_bool(current.get("ai_send_redact_emails", True), True)
    current["ai_send_redact_paths"] = coerce_bool(current.get("ai_send_redact_paths", True), True)
    current["ai_send_redact_tokens"] = coerce_bool(current.get("ai_send_redact_tokens", True), True)
    current["ai_app_knowledge_override"] = str(current.get("ai_app_knowledge_override", "") or "")
    current["ai_personality_advanced"] = str(current.get("ai_personality_advanced", "") or "")
    current["ai_knowledge_mode"] = _coerce_enum(current.get("ai_knowledge_mode"), {"compact", "full"}, "compact")
    current["ai_include_ui_action_appendix"] = coerce_bool(current.get("ai_include_ui_action_appendix", False), False)
    current["ai_user_knowledge_max_chars"] = _coerce_int_clamped(
        current.get("ai_user_knowledge_max_chars", 1800),
        1800,
        200,
        12000,
    )
    current["ai_selection_preview_chars"] = _coerce_int_clamped(
        current.get("ai_selection_preview_chars", 240),
        240,
        80,
        5000,
    )
    current["spellcheck_enabled"] = coerce_bool(current.get("spellcheck_enabled", True), True)
    current["spellcheck_language"] = str(current.get("spellcheck_language", "en") or "en").strip().lower() or "en"
    raw_dict = current.get("spellcheck_user_dictionary", [])
    if isinstance(raw_dict, str):
        current["spellcheck_user_dictionary"] = sorted({part.strip().lower() for part in raw_dict.split(",") if part.strip()})
    elif isinstance(raw_dict, list):
        current["spellcheck_user_dictionary"] = sorted({str(part).strip().lower() for part in raw_dict if str(part).strip()})
    else:
        current["spellcheck_user_dictionary"] = []
    current["writing_tools_use_language_tool"] = coerce_bool(current.get("writing_tools_use_language_tool", True), True)
    current["writing_tools_detect_repeated_words"] = coerce_bool(current.get("writing_tools_detect_repeated_words", True), True)
    current["writing_tools_detect_spacing"] = coerce_bool(current.get("writing_tools_detect_spacing", True), True)
    current["writing_tools_detect_capitalization"] = coerce_bool(current.get("writing_tools_detect_capitalization", True), True)
    current["writing_tools_detect_weak_phrases"] = coerce_bool(current.get("writing_tools_detect_weak_phrases", True), True)
    current["writing_tools_paraphrase_reduce_passive"] = coerce_bool(
        current.get("writing_tools_paraphrase_reduce_passive", True), True
    )
    current["writing_tools_humanizer_break_long_sentences"] = coerce_bool(
        current.get("writing_tools_humanizer_break_long_sentences", True), True
    )
    current["writing_tools_ai_detector_sensitivity"] = _coerce_float_clamped(
        current.get("writing_tools_ai_detector_sensitivity", 1.0), 1.0, 0.5, 1.5
    )
    current["writing_tools_ai_sentence_threshold"] = _coerce_int_clamped(
        current.get("writing_tools_ai_sentence_threshold", 24), 24, 8, 60
    )
    current["writing_tools_ai_unique_ratio_threshold"] = _coerce_float_clamped(
        current.get("writing_tools_ai_unique_ratio_threshold", 0.42), 0.42, 0.1, 0.9
    )
    current["writing_tools_package_download_cache"] = (
        dict(current.get("writing_tools_package_download_cache", {}))
        if isinstance(current.get("writing_tools_package_download_cache", {}), dict)
        else {}
    )
    current["writing_tools_runtime_download_cache"] = (
        dict(current.get("writing_tools_runtime_download_cache", {}))
        if isinstance(current.get("writing_tools_runtime_download_cache", {}), dict)
        else {}
    )
    closed_tab_history = current.get("closed_tab_history", [])
    current["closed_tab_history"] = closed_tab_history if isinstance(closed_tab_history, list) else []
    current["lsp_definition_enabled"] = coerce_bool(current.get("lsp_definition_enabled", True), True)
    current["lsp_definition_initialize_timeout_sec"] = _coerce_float_clamped(
        current.get("lsp_definition_initialize_timeout_sec", 5.0),
        5.0,
        0.5,
        30.0,
    )
    current["lsp_definition_request_timeout_sec"] = _coerce_float_clamped(
        current.get("lsp_definition_request_timeout_sec", 3.0),
        3.0,
        0.5,
        30.0,
    )
    current["lsp_definition_retries"] = _coerce_int_clamped(current.get("lsp_definition_retries", 2), 2, 0, 5)
    current["lsp_definition_verbose_logging"] = coerce_bool(current.get("lsp_definition_verbose_logging", False), False)
    current["lsp_python_servers"] = _coerce_cmd_list(
        current.get("lsp_python_servers"),
        list(defaults.get("lsp_python_servers", [])),
    )
    current["lsp_javascript_servers"] = _coerce_cmd_list(
        current.get("lsp_javascript_servers"),
        list(defaults.get("lsp_javascript_servers", [])),
    )
    current["lsp_typescript_servers"] = _coerce_cmd_list(
        current.get("lsp_typescript_servers"),
        list(defaults.get("lsp_typescript_servers", [])),
    )
    current["ai_preview_redacted_prompt"] = coerce_bool(current.get("ai_preview_redacted_prompt", True), True)
    current["ai_key_storage_mode"] = _coerce_enum(current.get("ai_key_storage_mode"), {"settings", "env_only"}, "env_only")
    current["update_feed_url"] = _sanitize_update_feed_url(current.get("update_feed_url"), defaults.get("update_feed_url", ""))
    current["update_channel_policy"] = _coerce_enum(
        current.get("update_channel_policy"),
        {"official_only", "custom_feed_allowed"},
        "official_only",
    )
    current["update_require_signed_metadata"] = coerce_bool(current.get("update_require_signed_metadata", True), True)
    current["update_signing_key"] = str(current.get("update_signing_key", "") or "").strip()
    current["untrusted_note_read_only"] = coerce_bool(current.get("untrusted_note_read_only", True), True)
    current["untrusted_note_block_ai"] = coerce_bool(current.get("untrusted_note_block_ai", True), True)
    current["untrusted_note_block_plugins"] = coerce_bool(current.get("untrusted_note_block_plugins", True), True)
    current["untrusted_note_block_export"] = coerce_bool(current.get("untrusted_note_block_export", True), True)
    current["untrusted_note_require_save_as"] = coerce_bool(current.get("untrusted_note_require_save_as", True), True)
    current["safe_save_atomic_replace"] = coerce_bool(current.get("safe_save_atomic_replace", True), True)
    current["safe_save_backup_on_overwrite"] = coerce_bool(current.get("safe_save_backup_on_overwrite", True), True)
    current["safe_save_warn_script_extensions"] = coerce_bool(current.get("safe_save_warn_script_extensions", True), True)
    current["safe_save_block_untrusted_overwrite"] = coerce_bool(
        current.get("safe_save_block_untrusted_overwrite", True),
        True,
    )

    current["recovery_mode"] = _coerce_enum(
        current.get("recovery_mode"),
        {"ask", "auto_restore", "auto_discard"},
        "ask",
    )
    current["recovery_discard_after_days"] = _coerce_int_clamped(
        current.get("recovery_discard_after_days", 14),
        14,
        1,
        90,
    )
    current["local_history_persist_enabled"] = coerce_bool(current.get("local_history_persist_enabled", True), True)
    current["crash_snapshot_enabled"] = coerce_bool(current.get("crash_snapshot_enabled", True), True)
    current["page_layout_view_enabled"] = coerce_bool(current.get("page_layout_view_enabled", False), False)
    current["page_layout_margin_left_mm"] = _coerce_int_clamped(current.get("page_layout_margin_left_mm", 18), 18, 5, 80)
    current["page_layout_margin_top_mm"] = _coerce_int_clamped(current.get("page_layout_margin_top_mm", 18), 18, 5, 80)
    current["page_layout_margin_right_mm"] = _coerce_int_clamped(current.get("page_layout_margin_right_mm", 18), 18, 5, 80)
    current["page_layout_margin_bottom_mm"] = _coerce_int_clamped(current.get("page_layout_margin_bottom_mm", 18), 18, 5, 80)
    current["page_layout_header_text"] = str(current.get("page_layout_header_text", "") or "")
    current["page_layout_footer_text"] = str(current.get("page_layout_footer_text", "") or "")
    current["page_layout_show_ruler"] = coerce_bool(current.get("page_layout_show_ruler", True), True)
    current["page_layout_show_page_breaks"] = coerce_bool(current.get("page_layout_show_page_breaks", True), True)
    current["track_changes_enabled"] = coerce_bool(current.get("track_changes_enabled", False), False)
    current["large_file_fast_open_enabled"] = coerce_bool(current.get("large_file_fast_open_enabled", True), True)
    current["large_file_fast_open_kb"] = _coerce_int_clamped(current.get("large_file_fast_open_kb", 8192), 8192, 1024, 102400)
    current["large_file_preview_head_lines"] = _coerce_int_clamped(current.get("large_file_preview_head_lines", 2000), 2000, 200, 50000)
    current["large_file_preview_tail_lines"] = _coerce_int_clamped(current.get("large_file_preview_tail_lines", 250), 250, 50, 10000)
    current["collab_presence_timeout_sec"] = _coerce_int_clamped(current.get("collab_presence_timeout_sec", 120), 120, 20, 3600)
    current["ai_workspace_qa_max_files"] = _coerce_int_clamped(current.get("ai_workspace_qa_max_files", 10), 10, 1, 40)
    current["ai_workspace_qa_max_lines_per_file"] = _coerce_int_clamped(
        current.get("ai_workspace_qa_max_lines_per_file", 60), 60, 10, 200
    )
    current["debug_telemetry_enabled"] = coerce_bool(current.get("debug_telemetry_enabled", False), False)
    current["save_debug_logs_to_appdata"] = coerce_bool(current.get("save_debug_logs_to_appdata", False), False)
    current["logging_level"] = _coerce_logging_level(current.get("logging_level", "INFO"))
    current["developer_mode_enabled"] = coerce_bool(current.get("developer_mode_enabled", False), False)
    current["gamification_enabled"] = coerce_bool(current.get("gamification_enabled", True), True)
    current["session_review_enabled"] = coerce_bool(current.get("session_review_enabled", False), False)
    custom_events = current.get("gamification_custom_events", [])
    current["gamification_custom_events"] = custom_events if isinstance(custom_events, list) else []
    gamification_state = current.get("gamification_state", {})
    current["gamification_state"] = gamification_state if isinstance(gamification_state, dict) else {}
    current["onboarding_enabled"] = coerce_bool(current.get("onboarding_enabled", True), True)
    current["onboarding_contextual_tips_enabled"] = coerce_bool(
        current.get("onboarding_contextual_tips_enabled", True),
        True,
    )
    current["onboarding_next_unlock_prompts_enabled"] = coerce_bool(
        current.get("onboarding_next_unlock_prompts_enabled", True),
        True,
    )
    onboarding_state = current.get("onboarding_state", {})
    current["onboarding_state"] = onboarding_state if isinstance(onboarding_state, dict) else {}
    current["backup_output_dir"] = str(current.get("backup_output_dir", "") or "").strip()
    current["settings_schema_version"] = 3

    normalize_ui_visibility_settings(current)
    ScintillaProfile.from_settings(current).apply_to_settings(current)
    return coerce_notepadpp_prefs(current)
