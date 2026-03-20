"""Run Windows Hello verification in a separate process and report a JSON result."""

from __future__ import annotations

import asyncio
import json
import sys

try:
    from winrt.windows.security.credentials.ui import UserConsentVerifier, UserConsentVerificationResult
except Exception as exc:  # noqa: BLE001
    UserConsentVerifier = None  # type: ignore[assignment]
    UserConsentVerificationResult = None  # type: ignore[assignment]
    _IMPORT_ERROR = str(exc)
else:
    _IMPORT_ERROR = ""


async def _verify_async() -> tuple[bool, str]:
    """Perform Windows Hello verification and return a result tuple."""
    if UserConsentVerifier is None or UserConsentVerificationResult is None:
        return False, f"Windows Hello verification is unavailable because the WinRT dependency is not installed: {_IMPORT_ERROR}"
    try:
        availability = await UserConsentVerifier.check_availability_async()
    except Exception as exc:  # noqa: BLE001
        return False, f"Windows Hello availability check failed: {exc}"
    if str(getattr(availability, "name", "") or "") != "AVAILABLE":
        return False, f"Windows Hello is not available on this device ({getattr(availability, 'name', 'UNKNOWN')})."
    try:
        result = await UserConsentVerifier.request_verification_async("Verify your identity to change Developer Mode")
    except Exception as exc:  # noqa: BLE001
        return False, f"Windows Hello verification failed to start: {exc}"
    if result == UserConsentVerificationResult.VERIFIED:
        return True, ""
    return False, f"Windows Hello verification did not succeed ({getattr(result, 'name', 'UNKNOWN')})."


def main() -> int:
    """Run verification and print a JSON payload for the parent process."""
    try:
        verified, message = asyncio.run(_verify_async())
    except Exception as exc:  # noqa: BLE001
        verified, message = False, f"Windows Hello verification failed: {exc}"
    sys.stdout.write(json.dumps({"verified": bool(verified), "message": str(message or "")}))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
