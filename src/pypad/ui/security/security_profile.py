"""Security-profile definitions and resolution helpers for trust-sensitive behavior."""

from __future__ import annotations

from dataclasses import asdict, dataclass


PROFILE_SCOPED_SETTING_KEYS = {
    "security_profile_custom_overrides",
    "file_trust_store",
    "file_trust_prompt_on_external_open",
    "file_trust_persist_session_only_default",
    "trust_known_workspace_files",
    "untrusted_note_read_only",
    "untrusted_note_block_ai",
    "untrusted_note_block_plugins",
    "untrusted_note_block_export",
    "untrusted_note_require_save_as",
    "safe_save_atomic_replace",
    "safe_save_backup_on_overwrite",
    "safe_save_warn_script_extensions",
    "safe_save_block_untrusted_overwrite",
    "plugin_runtime_policy",
    "update_channel_policy",
    "update_require_signed_metadata",
    "ai_redaction_profile_default",
    "ai_send_redact_emails",
    "ai_send_redact_paths",
    "ai_send_redact_tokens",
    "ai_key_storage_mode",
}


@dataclass(frozen=True)
class SecurityProfile:
    profile_id: str
    label: str
    description: str
    allow_custom_overrides: bool
    plugin_policy: str
    ai_policy: str
    update_policy: str
    file_trust_policy: str
    automation_policy: str
    save_policy: str
    persist_trust_decisions: bool
    allow_persistent_trust: bool
    require_signed_updates: bool
    redact_ai_prompts: bool
    allow_custom_update_feed: bool
    allow_unsigned_plugins: bool
    allow_edit_untrusted_after_prompt: bool


@dataclass(frozen=True)
class ResolvedSecurityPolicy:
    profile_id: str
    plugin_policy: str
    ai_policy: str
    update_policy: str
    file_trust_policy: str
    automation_policy: str
    save_policy: str
    persist_trust_decisions: bool
    allow_persistent_trust: bool
    require_signed_updates: bool
    redact_ai_prompts: bool
    allow_custom_update_feed: bool
    allow_unsigned_plugins: bool
    allow_edit_untrusted_after_prompt: bool


BUILTIN_SECURITY_PROFILES: dict[str, SecurityProfile] = {
    "beginner": SecurityProfile(
        profile_id="beginner",
        label="Beginner",
        description="Strong default protections. External files open read-only until trusted.",
        allow_custom_overrides=False,
        plugin_policy="built_in_only",
        ai_policy="redacted_only",
        update_policy="official_only",
        file_trust_policy="prompt_before_edit",
        automation_policy="macros_only",
        save_policy="safe_strict",
        persist_trust_decisions=False,
        allow_persistent_trust=False,
        require_signed_updates=True,
        redact_ai_prompts=True,
        allow_custom_update_feed=False,
        allow_unsigned_plugins=False,
        allow_edit_untrusted_after_prompt=True,
    ),
    "balanced": SecurityProfile(
        profile_id="balanced",
        label="Balanced",
        description="Secure defaults with explicit trust prompts for external notes and plugins.",
        allow_custom_overrides=False,
        plugin_policy="signed_only",
        ai_policy="redacted_only",
        update_policy="official_only",
        file_trust_policy="prompt_before_edit",
        automation_policy="restricted",
        save_policy="safe_default",
        persist_trust_decisions=True,
        allow_persistent_trust=True,
        require_signed_updates=True,
        redact_ai_prompts=True,
        allow_custom_update_feed=False,
        allow_unsigned_plugins=False,
        allow_edit_untrusted_after_prompt=True,
    ),
    "power_user": SecurityProfile(
        profile_id="power_user",
        label="Power User",
        description="Keeps strong integrity checks, but allows advanced plugin and update workflows.",
        allow_custom_overrides=False,
        plugin_policy="unsigned_local_allowed",
        ai_policy="full_with_warning",
        update_policy="custom_feed_allowed",
        file_trust_policy="prompt_before_edit",
        automation_policy="advanced",
        save_policy="power_flexible",
        persist_trust_decisions=True,
        allow_persistent_trust=True,
        require_signed_updates=True,
        redact_ai_prompts=True,
        allow_custom_update_feed=True,
        allow_unsigned_plugins=True,
        allow_edit_untrusted_after_prompt=True,
    ),
    "custom": SecurityProfile(
        profile_id="custom",
        label="Custom",
        description="Custom policy based on Balanced defaults with editable overrides.",
        allow_custom_overrides=True,
        plugin_policy="signed_only",
        ai_policy="redacted_only",
        update_policy="official_only",
        file_trust_policy="prompt_before_edit",
        automation_policy="restricted",
        save_policy="safe_default",
        persist_trust_decisions=True,
        allow_persistent_trust=True,
        require_signed_updates=True,
        redact_ai_prompts=True,
        allow_custom_update_feed=False,
        allow_unsigned_plugins=False,
        allow_edit_untrusted_after_prompt=True,
    ),
}


def coerce_security_profile_overrides(raw: object) -> dict[str, object]:
    """Return a sanitized mapping of custom profile overrides."""
    if not isinstance(raw, dict):
        return {}
    template = asdict(BUILTIN_SECURITY_PROFILES["custom"])
    allowed_keys = set(template) - {"profile_id", "label", "description", "allow_custom_overrides"}
    cleaned: dict[str, object] = {}
    for key, value in raw.items():
        name = str(key or "").strip()
        if name in allowed_keys:
            cleaned[name] = value
    return cleaned


def get_profile_state_store(settings: dict) -> dict[str, dict[str, object]]:
    """Return the profile-scoped security state store."""
    raw = settings.get("security_profile_states", {})
    if not isinstance(raw, dict):
        return {}
    cleaned: dict[str, dict[str, object]] = {}
    for key, value in raw.items():
        profile_id = str(key or "").strip().lower()
        if profile_id not in BUILTIN_SECURITY_PROFILES or not isinstance(value, dict):
            continue
        cleaned[profile_id] = {str(k): v for k, v in value.items() if str(k) in PROFILE_SCOPED_SETTING_KEYS}
    return cleaned


def get_active_profile_state(settings: dict) -> dict[str, object]:
    """Return profile-scoped settings for the active profile."""
    profile_id = str(settings.get("security_profile_id", "balanced") or "balanced").strip().lower()
    return dict(get_profile_state_store(settings).get(profile_id, {}))


def store_active_profile_state(settings: dict, state: dict[str, object]) -> None:
    """Persist one profile's scoped security settings back into the shared settings payload."""
    profile_id = str(settings.get("security_profile_id", "balanced") or "balanced").strip().lower()
    store = get_profile_state_store(settings)
    store[profile_id] = {str(k): v for k, v in dict(state or {}).items() if str(k) in PROFILE_SCOPED_SETTING_KEYS}
    settings["security_profile_states"] = store


def profile_setting(settings: dict, key: str, default: object = None) -> object:
    """Return a profile-scoped setting with fallback to the legacy top-level key."""
    state = get_active_profile_state(settings)
    if key in state:
        return state[key]
    return settings.get(key, default)


def resolve_security_policy(settings: dict) -> ResolvedSecurityPolicy:
    """Resolve built-in plus optional custom overrides into one runtime policy."""
    profile_id = str(settings.get("security_profile_id", "balanced") or "balanced").strip().lower()
    if profile_id not in BUILTIN_SECURITY_PROFILES:
        profile_id = "balanced"
    base_profile = BUILTIN_SECURITY_PROFILES["balanced"] if profile_id == "custom" else BUILTIN_SECURITY_PROFILES[profile_id]
    data = asdict(base_profile)
    if profile_id == "custom":
        for key, value in coerce_security_profile_overrides(
            profile_setting(settings, "security_profile_custom_overrides", {})
        ).items():
            data[key] = value
    data["profile_id"] = profile_id
    return ResolvedSecurityPolicy(**{k: data[k] for k in ResolvedSecurityPolicy.__annotations__})
