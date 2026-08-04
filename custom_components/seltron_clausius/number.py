from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
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
        CircuitSetpointNumber(
            coordinator,
            circuit.code,
            circuit.name,
            setpoint.key,
            setpoint.minimum,
            setpoint.maximum,
            setpoint.step,
        )
        for circuit in coordinator.data.status.circuits
        for setpoint in circuit.setpoints
    )


class CircuitSetpointNumber(SeltronEntity, NumberEntity):
    _attr_icon = "mdi:thermometer"
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator: SeltronCoordinator,
        code: str,
        circuit_name: str,
        key: str,
        minimum: float,
        maximum: float,
        step: float,
    ) -> None:
        super().__init__(coordinator, "controller")
        self._code = code
        self._key = key
        label = channel_label(
            getattr(coordinator.entry, "options", {}), "circuit", code, circuit_name
        )
        self._attr_name = f"{label} {key} setpoint"
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_control_setpoint_{code}_{key}"
        )
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._native_step = step

    @property
    def native_step(self) -> float:
        """Return the confirmed increment on old and current HA cores."""
        return self._native_step

    @property
    def native_value(self) -> float | None:
        circuit = next(
            (
                item
                for item in self.coordinator.data.status.circuits
                if item.code == self._code
            ),
            None,
        )
        if circuit is None:
            return None
        setpoint = next(
            (item for item in circuit.setpoints if item.key == self._key), None
        )
        return setpoint.value if setpoint else None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_setpoint(self._code, self._key, value)
