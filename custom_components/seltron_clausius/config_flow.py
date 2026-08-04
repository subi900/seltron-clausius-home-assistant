from __future__ import annotations

import hashlib

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AuthenticationError, SeltronApi, async_password_login
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_EXPIRES_AT,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)
from .labels import CONF_LABELS, normalize_labels

CONF_EMAIL = "email"
CONF_PASSWORD = "password"


class SeltronConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure SeltronHome without retaining account credentials."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        return SeltronOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            email = str(user_input[CONF_EMAIL]).strip().casefold()
            password = str(user_input[CONF_PASSWORD])
            session = async_get_clientsession(self.hass)
            try:
                tokens = await async_password_login(session, email, password)
                installations = await SeltronApi(
                    session, access_token=tokens.access_token
                ).async_discover_installations()
                if not installations:
                    errors["base"] = "no_installation"
                else:
                    # Stable duplicate protection without storing the email address.
                    unique_id = hashlib.sha256(email.encode("utf-8")).hexdigest()
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="SeltronHome Clausius",
                        data={
                            CONF_ACCESS_TOKEN: tokens.access_token,
                            CONF_REFRESH_TOKEN: tokens.refresh_token,
                            CONF_EXPIRES_AT: tokens.expires_at,
                        },
                    )
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except (aiohttp.ClientError, TimeoutError, RuntimeError, ValueError, KeyError):
                errors["base"] = "cannot_connect"
            finally:
                password = ""

        schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )


class SeltronOptionsFlow(config_entries.OptionsFlow):
    """Configure local display labels for currently discovered stable channels."""

    def __init__(self, config_entry) -> None:
        # HA 2026 exposes ``config_entry`` as a read-only base property.
        self._seltron_entry = config_entry

    def _label_fields(self) -> list[tuple[str, str]]:
        coordinator = self.hass.data[DOMAIN][self._seltron_entry.entry_id]
        status = coordinator.data.status
        fields: list[tuple[str, str]] = []
        seen_temperatures: set[str] = set()
        for item in status.temperatures:
            if item.code not in seen_temperatures:
                fields.append((f"temperature:{item.code}", item.name))
                seen_temperatures.add(item.code)
        fields.extend((f"relay:{item.code}", item.name) for item in status.relays)
        fields.extend((f"circuit:{item.code}", item.name) for item in status.circuits)
        return fields

    async def async_step_init(self, user_input=None) -> FlowResult:
        fields = self._label_fields()
        allowed = {key for key, _fallback in fields}
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                if not set(user_input).issubset(allowed):
                    raise ValueError("Unknown label channel")
                return self.async_create_entry(
                    title="", data={CONF_LABELS: normalize_labels(user_input)}
                )
            except ValueError:
                errors["base"] = "invalid_label"

        existing = self._seltron_entry.options.get(CONF_LABELS, {})
        schema = vol.Schema(
            {
                vol.Optional(
                    key,
                    default=existing.get(key, "") if isinstance(existing, dict) else "",
                    description={"suggested_value": fallback},
                ): str
                for key, fallback in fields
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
