from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import SeltronCoordinator
from .entity import SeltronEntity

FUNCTIONS: dict[str, tuple[str, str]] = {
    "Party": ("Party bis", "mdi:party-popper"),
    "Eco": ("Eco bis", "mdi:leaf"),
    "Holiday": ("Urlaub bis", "mdi:palm-tree"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SeltronCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        UserFunctionUntilEntity(
            coordinator,
            circuit.code,
            circuit.name,
            function,
            label,
            icon,
        )
        for circuit in coordinator.data.status.circuits
        if circuit.code.upper().startswith("HC")
        for function, (label, icon) in FUNCTIONS.items()
    )


class UserFunctionUntilEntity(SeltronEntity, DateTimeEntity, RestoreEntity):
    """User-selected absolute expiration for a Clausius user function."""

    def __init__(
        self,
        coordinator: SeltronCoordinator,
        circuit_code: str,
        circuit_name: str,
        function: str,
        label: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, "controller")
        self._circuit_code = circuit_code
        self._function = function
        self._attr_name = f"{circuit_name} {label}"
        self._attr_icon = icon
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_{circuit_code}_user_function_{function}_until"
        )
        self._attr_native_value = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        restored = await self.async_get_last_state()
        if restored is None or restored.state in {"unknown", "unavailable"}:
            return
        try:
            value = datetime.fromisoformat(restored.state)
        except ValueError:
            return
        if value.tzinfo is None:
            return
        self._set_native_value(value)

    async def async_set_value(self, value: datetime) -> None:
        if value.tzinfo is None:
            raise HomeAssistantError("End date and time must include a timezone")
        now = dt_util.utcnow()
        if value <= now:
            raise HomeAssistantError("End date and time must be in the future")
        if value > now + timedelta(days=366):
            raise HomeAssistantError("End date and time cannot exceed 366 days")
        self._set_native_value(value)
        self.async_write_ha_state()

    def _set_native_value(self, value: datetime) -> None:
        self._attr_native_value = value
        self.coordinator.user_function_until[(self._circuit_code, self._function)] = value