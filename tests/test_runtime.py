from __future__ import annotations

from dataclasses import dataclass

import pytest

from custom_components.seltron_clausius.api import Installation, TokenSet
from custom_components.seltron_clausius.runtime import SeltronRuntime


@dataclass
class FakeApi:
    token: str
    installation: Installation
    discover_calls: int = 0
    refresh_calls: int = 0

    async def async_discover_installations(self):
        self.discover_calls += 1
        return [self.installation]

    async def async_refresh_installation(self, installation):
        self.refresh_calls += 1
        return installation


@pytest.mark.asyncio
async def test_runtime_rotates_tokens_atomically_then_reuses_known_installation() -> None:
    installation = Installation(
        subscription_id="sub",
        resource_group_id="group",
        gateway_id="gateway",
        controller_id="controller",
        gateway={"model": "GWD3E", "connectionState": True, "isActive": True},
        controller={"model": "WDC20", "isActive": True},
    )
    persisted: list[TokenSet] = []
    apis: list[FakeApi] = []

    async def refresh(_session, old_refresh_token):
        assert old_refresh_token == "old-refresh"
        return TokenSet("new-access", "rotated-refresh", 9999999999.0)

    def api_factory(_session, *, access_token):
        api = FakeApi(access_token, installation)
        apis.append(api)
        return api

    async def persist(tokens):
        persisted.append(tokens)

    runtime = SeltronRuntime(
        object(),
        TokenSet("old-access", "old-refresh", 0.0),
        persist_tokens=persist,
        refresh_tokens=refresh,
        api_factory=api_factory,
        now=lambda: 1000.0,
    )

    first = await runtime.async_update()
    second = await runtime.async_update()

    assert persisted == [TokenSet("new-access", "rotated-refresh", 9999999999.0)]
    assert [api.token for api in apis] == ["new-access", "new-access"]
    assert apis[0].discover_calls == 1
    assert apis[1].refresh_calls == 1
    assert first.status.gateway.connected is True
    assert second.status.controller.connected is True
