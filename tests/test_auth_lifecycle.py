"""Local-only Home Assistant authentication lifecycle regression tests."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.seltron_clausius import async_setup_entry
from custom_components.seltron_clausius.api import AuthenticationError, TokenSet
from custom_components.seltron_clausius.coordinator import SeltronCoordinator
from custom_components.seltron_clausius.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_token_rotation_does_not_reload_but_options_do():
    listener = None

    def register(callback):
        nonlocal listener
        listener = callback
        return lambda: None

    entry = SimpleNamespace(
        entry_id="entry", options={}, data={},
        add_update_listener=register, async_on_unload=Mock(),
    )
    hass = SimpleNamespace(data={}, config_entries=SimpleNamespace(
        async_reload=AsyncMock(), async_forward_entry_setups=AsyncMock(),
    ))
    with patch("custom_components.seltron_clausius.SeltronCoordinator", return_value=AsyncMock()):
        await async_setup_entry(hass, entry)
    entry.data = {"access_token": "rotated"}
    await listener(hass, entry)
    hass.config_entries.async_reload.assert_not_awaited()
    entry.options = {"polling_interval": 60}
    await listener(hass, entry)
    hass.config_entries.async_reload.assert_awaited_once_with("entry")


async def test_coordinator_persists_rotation_preserving_credentials():
    entry = SimpleNamespace(data={
        "access_token": "old", "refresh_token": "old-refresh", "expires_at": 0,
        "email": "synthetic@example.invalid", "password": "dummy",
    }, options={})
    hass = Mock()
    with patch("custom_components.seltron_clausius.coordinator.async_get_clientsession"), patch(
        "custom_components.seltron_clausius.coordinator.SeltronRuntime"
    ) as runtime:
        SeltronCoordinator(hass, entry)
    kwargs = runtime.call_args.kwargs
    assert kwargs["credentials"] == ("synthetic@example.invalid", "dummy")
    await kwargs["persist_tokens"](TokenSet("new", "new-refresh", 1000))
    stored = hass.config_entries.async_update_entry.call_args.kwargs["data"]
    assert stored == {**entry.data, "access_token": "new", "refresh_token": "new-refresh", "expires_at": 1000}


@pytest.mark.parametrize("error, expected", [
    (RuntimeError("cloud"), UpdateFailed),
    (TimeoutError(), UpdateFailed),
    (AuthenticationError("credentials rejected"), ConfigEntryAuthFailed),
])
async def test_coordinator_only_requests_reauth_for_authentication_failures(error, expected):
    coordinator = SimpleNamespace(runtime=SimpleNamespace(async_update=AsyncMock(side_effect=error)))
    with pytest.raises(expected):
        await SeltronCoordinator._async_update_data(coordinator)


async def test_diagnostics_without_loaded_runtime_redacts_saved_credentials():
    entry = SimpleNamespace(entry_id="entry", options={}, data={
        "email": "synthetic@example.invalid", "password": "synthetic-password",
        "access_token": "synthetic-access", "refresh_token": "synthetic-refresh",
    })
    output = await async_get_config_entry_diagnostics(SimpleNamespace(data={}), entry)
    rendered = repr(output)
    assert "synthetic" not in rendered
