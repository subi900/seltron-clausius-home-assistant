from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import SeltronCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SeltronHome status and narrowly verified controls."""
    coordinator = SeltronCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    options = dict(entry.options)

    async def reload_options(hass: HomeAssistant, updated: ConfigEntry) -> None:
        nonlocal options
        if updated.options != options:
            options = dict(updated.options)
            await hass.config_entries.async_reload(updated.entry_id)

    # Token persistence also invokes update listeners; only options require reload.
    entry.async_on_unload(entry.add_update_listener(reload_options))
    await hass.config_entries.async_forward_entry_setups(entry, list(PLATFORMS))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a SeltronHome config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, list(PLATFORMS))
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
