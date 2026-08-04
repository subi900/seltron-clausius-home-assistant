from __future__ import annotations

import logging
from datetime import datetime

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AuthenticationError, TokenSet
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_EXPIRES_AT,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    UPDATE_INTERVAL,
)
from .runtime import RuntimeData, SeltronRuntime

_LOGGER = logging.getLogger(__name__)


class SeltronCoordinator(DataUpdateCoordinator[RuntimeData]):
    """Coordinate conservative, read-only Seltron cloud updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.user_function_until: dict[tuple[str, str], datetime] = {}

        async def persist_tokens(tokens: TokenSet) -> None:
            # One ConfigEntry update persists the complete rotated token set atomically.
            hass.config_entries.async_update_entry(
                entry,
                data={
                    **entry.data,
                    CONF_ACCESS_TOKEN: tokens.access_token,
                    CONF_REFRESH_TOKEN: tokens.refresh_token,
                    CONF_EXPIRES_AT: tokens.expires_at,
                },
            )

        self.runtime = SeltronRuntime(
            async_get_clientsession(hass),
            TokenSet(
                entry.data[CONF_ACCESS_TOKEN],
                entry.data[CONF_REFRESH_TOKEN],
                float(entry.data[CONF_EXPIRES_AT]),
            ),
            persist_tokens=persist_tokens,
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> RuntimeData:
        try:
            return await self.runtime.async_update()
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed("Seltron authentication expired") from err
        except (aiohttp.ClientError, TimeoutError, RuntimeError, ValueError) as err:
            raise UpdateFailed("Could not update Seltron read-only status") from err

    async def async_set_operation_mode(self, circuit_code: str, mode: str) -> None:
        """Write one confirmed mode and publish only its verified reread state."""
        try:
            data = await self.runtime.async_set_operation_mode(circuit_code, mode)
        except AuthenticationError as err:
            raise HomeAssistantError("Seltron authentication expired") from err
        except (aiohttp.ClientError, TimeoutError, RuntimeError, ValueError) as err:
            raise HomeAssistantError("Seltron operation-mode change was not confirmed") from err
        self.async_set_updated_data(data)

    async def async_set_setpoint(
        self, circuit_code: str, key: str, value: float
    ) -> None:
        """Write one confirmed setpoint and publish only its verified reread state."""
        try:
            data = await self.runtime.async_set_setpoint(circuit_code, key, value)
        except AuthenticationError as err:
            raise HomeAssistantError("Seltron authentication expired") from err
        except (aiohttp.ClientError, TimeoutError, RuntimeError, ValueError) as err:
            raise HomeAssistantError("Seltron setpoint change was not confirmed") from err
        self.async_set_updated_data(data)

    async def async_set_user_function(
        self,
        circuit_code: str,
        function: str,
        *,
        active_until: datetime | None = None,
    ) -> None:
        """Write one confirmed user function and publish its verified reread state."""
        try:
            data = await self.runtime.async_set_user_function(
                circuit_code, function, active_until=active_until
            )
        except AuthenticationError as err:
            raise HomeAssistantError("Seltron authentication expired") from err
        except (aiohttp.ClientError, TimeoutError, RuntimeError, ValueError) as err:
            raise HomeAssistantError("Seltron user-function change was not confirmed") from err
        self.async_set_updated_data(data)
