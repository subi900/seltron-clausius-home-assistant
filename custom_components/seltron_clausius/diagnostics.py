from __future__ import annotations

from typing import Any

REDACTED = "**REDACTED**"
_SENSITIVE_EXACT = {
    "id",
    "email",
    "username",
    "password",
    "serialnumber",
    "serial",
    "mac",
    "macaddress",
    "address",
}


def _is_sensitive_key(key: object) -> bool:
    normalized = str(key).replace("_", "").replace("-", "").lower()
    return (
        normalized in _SENSITIVE_EXACT
        or normalized.endswith("id")
        or "token" in normalized
        or "secret" in normalized
        or "credential" in normalized
    )


def redact_payload(value: Any) -> Any:
    """Return a deep diagnostic copy without tokens or private identifiers."""
    if isinstance(value, dict):
        return {
            key: REDACTED if _is_sensitive_key(key) else redact_payload(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_payload(item) for item in value)
    return value
