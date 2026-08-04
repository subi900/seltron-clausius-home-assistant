from __future__ import annotations

from zoneinfo import ZoneInfo

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SeltronCoordinator
from .entity import SeltronEntity

HEATING_FUNCTIONS: dict[str, tuple[str, str]] = {
    "Party": ("Party-Modus", "mdi:party-popper"),
    "Eco": ("Eco-Modus", "mdi:leaf"),
    "Holiday": ("Urlaubsmodus", "mdi:palm-tree"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SeltronCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = []
    for circuit in coordinator.data.status.circuits:
        if circuit.code.upper().startswith("HC"):
            entities.extend(
                UserFunctionSwitch(
                    coordinator,
                    circuit.code,
                    circuit.name,
                    function,
                    label,
                    icon,
                )
                for function, (label, icon) in HEATING_FUNCTIONS.items()
            )
        elif circuit.code.upper() == "DHWC":
            entities.append(
                UserFunctionSwitch(
                    coordinator,
                    circuit.code,
                    circuit.name,
                    "SingleActivation",
                    "Einzel-Aktivierung",
                    "mdi:water-boiler-auto",
                )
            )
    async_add_entities(entities)


class UserFunctionSwitch(SeltronEntity, SwitchEntity):
    """A stateful, mutually exclusive Clausius normal-user function."""

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
            f"{coordinator.entry.entry_id}_{circuit_code}_user_function_{function}"
        )

    @property
    def _circuit(self):
        return next(
            item
            for item in self.coordinator.data.status.circuits
            if item.code == self._circuit_code
        )

    @property
    def is_on(self) -> bool:
        return self._circuit.user_function == self._function

    @property
    def extra_state_attributes(self) -> dict[str, str | float | None]:
        circuit = self._circuit
        return {
            "funktion": circuit.user_function,
            "aktiv_bis": circuit.user_function_active_until,
            "solltemperatur": circuit.user_function_temperature,
            "gewahltes_ende": (
                selected.isoformat()
                if (
                    selected := self.coordinator.user_function_until.get(
                        (self._circuit_code, self._function)
                    )
                )
                else None
            ),
        }

    async def async_turn_on(self, **kwargs) -> None:
        active_until = None
        if self._function in HEATING_FUNCTIONS:
            selected = self.coordinator.user_function_until.get(
                (self._circuit_code, self._function)
            )
            if selected is None:
                raise HomeAssistantError(
                    f"Set an end date and time for {self._function} first"
                )
            active_until = selected.astimezone(
                ZoneInfo(self.hass.config.time_zone)
            ).replace(tzinfo=None)
        await self.coordinator.async_set_user_function(
            self._circuit_code,
            self._function,
            active_until=active_until,
        )

    async def async_turn_off(self, **kwargs) -> None:
        if self.is_on:
            await self.coordinator.async_set_user_function(self._circuit_code, "Off")
