from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SeltronCoordinator
from .entity import SeltronEntity
from .labels import channel_label


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SeltronCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        CircuitModeSelect(
            coordinator,
            circuit.code,
            circuit.name,
            circuit.supported_modes,
        )
        for circuit in coordinator.data.status.circuits
        if circuit.supported_modes and circuit.program
    )


class CircuitModeSelect(SeltronEntity, SelectEntity):
    _attr_icon = "mdi:radiator"

    def __init__(
        self,
        coordinator: SeltronCoordinator,
        code: str,
        name: str,
        options: tuple[str, ...],
    ) -> None:
        super().__init__(coordinator, "controller")
        self._code = code
        label = channel_label(
            getattr(coordinator.entry, "options", {}), "circuit", code, name
        )
        self._attr_name = f"{label} operation mode"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_control_mode_{code}"
        self._attr_options = list(options)

    @property
    def current_option(self) -> str | None:
        circuit = next(
            (
                item
                for item in self.coordinator.data.status.circuits
                if item.code == self._code
            ),
            None,
        )
        return circuit.mode if circuit else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_operation_mode(self._code, option)
