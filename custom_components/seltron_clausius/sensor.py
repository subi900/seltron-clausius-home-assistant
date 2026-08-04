from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
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
    data = coordinator.data
    entities: list[SensorEntity] = [LastUpdateSensor(coordinator)]
    entities.extend(
        TemperatureSensor(coordinator, reading.code, reading.kind, reading.name)
        for reading in data.status.temperatures
    )
    for circuit in data.status.circuits:
        entities.append(CircuitSensor(coordinator, circuit.code, circuit.name, "mode"))
        entities.append(CircuitSensor(coordinator, circuit.code, circuit.name, "program"))
    async_add_entities(entities)


class LastUpdateSensor(SeltronEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_name = "Last successful update"

    def __init__(self, coordinator: SeltronCoordinator) -> None:
        super().__init__(coordinator, "gateway")
        self._attr_unique_id = f"{coordinator.entry.entry_id}_last_update"

    @property
    def native_value(self):
        return self.coordinator.data.last_successful_update


class TemperatureSensor(SeltronEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, code: str, kind: str, name: str) -> None:
        super().__init__(coordinator, "controller")
        self._code = code
        self._kind = kind
        suffix = "measured" if kind == "measured" else "calculated"
        label = channel_label(
            getattr(coordinator.entry, "options", {}), "temperature", code, name
        )
        self._attr_name = f"{label} {suffix}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_temperature_{code}_{kind}"

    @property
    def native_value(self):
        return next(
            (
                item.value
                for item in self.coordinator.data.status.temperatures
                if item.code == self._code and item.kind == self._kind
            ),
            None,
        )


class CircuitSensor(SeltronEntity, SensorEntity):
    _attr_icon = "mdi:radiator"

    def __init__(self, coordinator, code: str, name: str, field: str) -> None:
        super().__init__(coordinator, "controller")
        self._code = code
        self._field = field
        label = channel_label(
            getattr(coordinator.entry, "options", {}), "circuit", code, name
        )
        self._attr_name = f"{label} {field}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_circuit_{code}_{field}"

    @property
    def native_value(self):
        circuit = next(
            (item for item in self.coordinator.data.status.circuits if item.code == self._code),
            None,
        )
        return getattr(circuit, self._field, None) if circuit else None
