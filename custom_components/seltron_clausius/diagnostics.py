from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_EXPIRES_AT,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)
from .labels import CONF_LABELS

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


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return useful controller status without account or installation identifiers."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    return async_redact_data(
        {
            "config_entry": {
                "data": dict(entry.data),
                "options": dict(entry.options),
            },
            "runtime": asdict(coordinator.data),
        },
        {
            CONF_ACCESS_TOKEN,
            CONF_REFRESH_TOKEN,
            CONF_EXPIRES_AT,
            CONF_LABELS,
            "subscription_id",
            "resource_group_id",
            "gateway_id",
            "controller_id",
        },
    )
