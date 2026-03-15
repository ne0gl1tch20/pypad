import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypad.ui.security.security_profile import profile_setting, resolve_security_policy, store_active_profile_state


class SecurityProfileTests(unittest.TestCase):
    def test_beginner_profile_resolves_strict_defaults(self) -> None:
        policy = resolve_security_policy({"security_profile_id": "beginner"})
        self.assertEqual(policy.plugin_policy, "built_in_only")
        self.assertTrue(policy.require_signed_updates)
        self.assertFalse(policy.allow_unsigned_plugins)

    def test_custom_profile_uses_balanced_fallback(self) -> None:
        policy = resolve_security_policy(
            {
                "security_profile_id": "custom",
                "security_profile_custom_overrides": {"plugin_policy": "unsigned_local_allowed"},
            }
        )
        self.assertEqual(policy.plugin_policy, "unsigned_local_allowed")
        self.assertEqual(policy.update_policy, "official_only")

    def test_invalid_profile_falls_back_to_balanced(self) -> None:
        policy = resolve_security_policy({"security_profile_id": "nope"})
        self.assertEqual(policy.profile_id, "balanced")

    def test_custom_profile_uses_profile_scoped_override_store(self) -> None:
        settings = {"security_profile_id": "custom"}
        store_active_profile_state(settings, {"security_profile_custom_overrides": {"plugin_policy": "unsigned_local_allowed"}})
        policy = resolve_security_policy(settings)
        self.assertEqual(policy.plugin_policy, "unsigned_local_allowed")

    def test_profile_scoped_setting_is_isolated_per_profile(self) -> None:
        settings = {"security_profile_id": "beginner"}
        store_active_profile_state(settings, {"ai_key_storage_mode": "env_only"})
        settings["security_profile_id"] = "power_user"
        store_active_profile_state(settings, {"ai_key_storage_mode": "settings"})
        settings["security_profile_id"] = "beginner"
        self.assertEqual(profile_setting(settings, "ai_key_storage_mode", "settings"), "env_only")
        settings["security_profile_id"] = "power_user"
        self.assertEqual(profile_setting(settings, "ai_key_storage_mode", "env_only"), "settings")


if __name__ == "__main__":
    unittest.main()
