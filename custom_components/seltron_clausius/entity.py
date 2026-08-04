from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SeltronCoordinator


class SeltronEntity(CoordinatorEntity[SeltronCoordinator]):
    """Base for entities belonging to one Seltron device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SeltronCoordinator, kind: str) -> None:
        super().__init__(coordinator)
        self._kind = kind

    @property
    def device_info(self) -> DeviceInfo:
        status = self.coordinator.data.status
        device = status.gateway if self._kind == "gateway" else status.controller
        via = None
        if self._kind == "controller":
            via = (DOMAIN, f"{self.coordinator.entry.entry_id}_gateway")
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.entry.entry_id}_{self._kind}")},
            name=f"Seltron {device.model}",
            manufacturer=device.manufacturer,
            model=device.model,
            hw_version=device.hardware_version,
            sw_version=device.firmware_version,
            via_device=via,
        )
