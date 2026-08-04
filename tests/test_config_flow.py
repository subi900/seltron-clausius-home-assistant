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


async def _noop_unique_id(value):
    assert len(value) == 64
