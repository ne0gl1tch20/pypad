"""Mark this directory as a Python package and describe the role of the package in the larger application.

This module belongs to the note privacy and security UI layer. It helps explain how `pypad.ui.security.__init__` is structured and where this file fits into the runtime workflow.
"""

"""Security helpers for note privacy, trust, profiles, and related workflows."""

from .note_trust import SESSION_TRUSTED, TRUSTED, UNTRUSTED
from .security_profile import (
    BUILTIN_SECURITY_PROFILES,
    PROFILE_SCOPED_SETTING_KEYS,
    ResolvedSecurityPolicy,
    SecurityProfile,
    get_active_profile_state,
    get_profile_state_store,
    profile_setting,
    resolve_security_policy,
    store_active_profile_state,
)

__all__ = [
    "BUILTIN_SECURITY_PROFILES",
    "PROFILE_SCOPED_SETTING_KEYS",
    "ResolvedSecurityPolicy",
    "SecurityProfile",
    "SESSION_TRUSTED",
    "TRUSTED",
    "UNTRUSTED",
    "get_active_profile_state",
    "get_profile_state_store",
    "profile_setting",
    "resolve_security_policy",
    "store_active_profile_state",
]
