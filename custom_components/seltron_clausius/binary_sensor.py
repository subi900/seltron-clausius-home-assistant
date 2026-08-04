from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SeltronCoordinator
from .entity import SeltronEntity
from .labels import channel_label

WARNING_CATEGORIES = ("boiler", "communication", "sensor", "message")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SeltronCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = [
        ConnectivitySensor(coordinator, "gateway"),
        ConnectivitySensor(coordinator, "controller"),
    ]
    entities.extend(
        RelaySensor(coordinator, relay.code, relay.name)
        for relay in coordinator.data.status.relays
    )
    entities.extend(
        RegulatedOutputSensor(
            coordinator,
            output.component_code,
            output.component_id,
            output.output_code,
        )
        for output in coordinator.data.status.regulated_outputs
        if output.component_code == "LiquidFuelBoiler"
    )
    entities.extend(WarningSensor(coordinator, category) for category in WARNING_CATEGORIES)
    async_add_entities(entities)


class ConnectivitySensor(SeltronEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_name = "Connection"

    def __init__(self, coordinator: SeltronCoordinator, kind: str) -> None:
        super().__init__(coordinator, kind)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{kind}_connection"

    @property
    def is_on(self) -> bool:
        status = self.coordinator.data.status
        return status.gateway.connected if self._kind == "gateway" else status.controller.connected


class RelaySensor(SeltronEntity, BinarySensorEntity):
    """Expose an explicitly boolean cloud relay without inferring its function."""

    _attr_icon = "mdi:electric-switch"

    def __init__(self, coordinator, code: str, name: str) -> None:
        super().__init__(coordinator, "controller")
        self._code = code
        self._attr_name = channel_label(
            getattr(coordinator.entry, "options", {}), "relay", code, name
        )
        self._attr_unique_id = f"{coordinator.entry.entry_id}_relay_{code}"

    @property
    def is_on(self) -> bool | None:
        relay = next(
            (item for item in self.coordinator.data.status.relays if item.code == self._code),
            None,
        )
        return relay.is_active if relay else None


class RegulatedOutputSensor(SeltronEntity, BinarySensorEntity):
    """Expose the official-schema physical role of a live controller output."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: SeltronCoordinator,
        component_code: str,
        component_id: str,
        output_code: str,
    ) -> None:
        super().__init__(coordinator, "controller")
        self._component_code = component_code
        self._component_id = component_id
        self._output_code = output_code
        self._attr_name = {
            "LiquidFuelBoiler": "Flüssigbrennstoffkessel",
        }.get(component_code, component_code)
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_component_{component_code}_{component_id}"
        )

    @property
    def is_on(self) -> bool | None:
        output = next(
            (
                item
                for item in self.coordinator.data.status.regulated_outputs
                if item.component_code == self._component_code
                and item.component_id == self._component_id
            ),
            None,
        )
        return output.is_active if output else None

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return {"output": self._output_code}


class WarningSensor(SeltronEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator, category: str) -> None:
        super().__init__(coordinator, "controller")
        self._category = category
        self._attr_name = f"{category.title()} warning"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_warning_{category}"

    @property
    def is_on(self) -> bool:
        return self._category in self.coordinator.data.status.active_warning_categories
