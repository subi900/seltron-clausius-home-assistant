import hashlib
from types import SimpleNamespace

import pytest

from custom_components.seltron_clausius import config_flow
from custom_components.seltron_clausius.api import Installation, TokenSet


@pytest.mark.asyncio
async def test_config_flow_discards_password_and_stores_only_tokens(monkeypatch) -> None:
    captured = {}

    async def login(session, email, password):
        captured.update(email=email, password=password)
        return TokenSet("access", "refresh", 1234.0)

    class Api:
        def __init__(self, session, *, access_token):
            assert access_token == "access"

        async def async_discover_installations(self):
            return [
                Installation("s", "g", "gw", "c", {"model": "GWD3E"}, {"model": "WDC20"})
            ]

    monkeypatch.setattr(config_flow, "async_get_clientsession", lambda hass: object())
    monkeypatch.setattr(config_flow, "async_password_login", login)
    monkeypatch.setattr(config_flow, "SeltronApi", Api)

    flow = config_flow.SeltronConfigFlow()
    flow.hass = SimpleNamespace()
    monkeypatch.setattr(flow, "async_set_unique_id", _noop_unique_id)
    monkeypatch.setattr(flow, "_abort_if_unique_id_configured", lambda: None)

    result = await flow.async_step_user(
        {config_flow.CONF_EMAIL: " Person@Example.com ", config_flow.CONF_PASSWORD: "secret"}
    )

    assert result["type"].value == "create_entry"
    assert set(result["data"]) == {"access_token", "refresh_token", "expires_at"}
    assert result["data"]["refresh_token"] == "refresh"
    assert captured == {"email": "person@example.com", "password": "secret"}
    assert "email" not in result["data"] and "password" not in result["data"]


@pytest.mark.asyncio
async def test_reauth_replaces_tokens_for_same_account(monkeypatch) -> None:
    email = "person@example.com"
    entry = SimpleNamespace(
        entry_id="entry-id",
        unique_id=hashlib.sha256(email.encode()).hexdigest(),
        data={"access_token": "old", "refresh_token": "old-refresh", "expires_at": 1.0},
    )
    updated = {}

    async def login(session, normalized_email, password):
        assert normalized_email == email
        assert password == "new-secret"
        return TokenSet("new", "new-refresh", 5678.0)

    class Api:
        def __init__(self, session, *, access_token):
            assert access_token == "new"

        async def async_discover_installations(self):
            return [Installation("s", "g", "gw", "c", {}, {})]

    class Entries:
        def async_get_entry(self, entry_id):
            assert entry_id == "entry-id"
            return entry

        def async_update_entry(self, target, *, data):
            assert target is entry
            updated.update(data)

        async def async_reload(self, entry_id):
            assert entry_id == "entry-id"

    monkeypatch.setattr(config_flow, "async_get_clientsession", lambda hass: object())
    monkeypatch.setattr(config_flow, "async_password_login", login)
    monkeypatch.setattr(config_flow, "SeltronApi", Api)

    flow = config_flow.SeltronConfigFlow()
    flow.hass = SimpleNamespace(config_entries=Entries())
    flow.context = {"entry_id": "entry-id"}

    result = await flow.async_step_reauth_confirm(
        {config_flow.CONF_EMAIL: email, config_flow.CONF_PASSWORD: "new-secret"}
    )

    assert result["type"].value == "abort"
    assert result["reason"] == "reauth_successful"
    assert updated == {
        "access_token": "new",
        "refresh_token": "new-refresh",
        "expires_at": 5678.0,
    }


async def _noop_unique_id(value):
    assert len(value) == 64
