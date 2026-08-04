from __future__ import annotations

from typing import Any, Self

import pytest

from custom_components.seltron_clausius.api import Installation, SeltronApi


class Response:
    status = 200

    def __init__(self, payload: Any) -> None:
        self.payload = payload

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    async def json(self) -> Any:
        return self.payload


class QueueSession:
    def __init__(self, payloads: list[Any]) -> None:
        self.payloads = payloads
        self.urls: list[str] = []

    def get(self, url: str, **_: Any) -> Response:
        self.urls.append(url)
        return Response(self.payloads.pop(0))


@pytest.mark.asyncio
async def test_discovery_follows_subscription_group_gateway_and_wdc() -> None:
    session = QueueSession(
        [
            [{"id": "sub-private"}],
            {"id": "sub-private", "resourceGroups": [{"id": "rg-private"}]},
            {
                "id": "rg-private",
                "resources": [{"id": "gw-private", "type": "GWD3"}],
            },
            {
                "id": "gw-private",
                "model": "GWD3E",
                "connectedControllers": [{"id": "wdc-private", "type": "WDC"}],
            },
            {"id": "wdc-private", "model": "WDC20"},
        ]
    )
    api = SeltronApi(session, access_token="dummy")  # type: ignore[arg-type]

    installations = await api.async_discover_installations()

    assert len(installations) == 1
    assert installations[0].gateway["model"] == "GWD3E"
    assert installations[0].controller["model"] == "WDC20"
    assert session.urls == [
        "https://api.seltronhome.com/api/subscriptions?$expand=Tags",
        "https://api.seltronhome.com/api/subscriptions/sub-private",
        "https://api.seltronhome.com/api/subscriptions/sub-private/resourceGroups/rg-private?$expand=Tags",
        "https://api.seltronhome.com/api/subscriptions/sub-private/resourceGroups/rg-private/GWD3/gw-private?$expand=Tags",
        "https://api.seltronhome.com/api/subscriptions/sub-private/resourceGroups/rg-private/WDC/wdc-private?$expand=Tags",
    ]


@pytest.mark.asyncio
async def test_refresh_installation_uses_only_two_direct_gets() -> None:
    session = QueueSession(
        [
            {"id": "gw-private", "model": "GWD3E"},
            {"id": "wdc-private", "model": "WDC20"},
        ]
    )
    api = SeltronApi(session, access_token="dummy")  # type: ignore[arg-type]
    existing = Installation(
        subscription_id="sub-private",
        resource_group_id="rg-private",
        gateway_id="gw-private",
        controller_id="wdc-private",
        gateway={},
        controller={},
    )

    refreshed = await api.async_refresh_installation(existing)

    assert refreshed.gateway["model"] == "GWD3E"
    assert refreshed.controller["model"] == "WDC20"
    assert session.urls == [
        "https://api.seltronhome.com/api/subscriptions/sub-private/resourceGroups/rg-private/GWD3/gw-private?$expand=Tags",
        "https://api.seltronhome.com/api/subscriptions/sub-private/resourceGroups/rg-private/WDC/wdc-private?$expand=Tags",
    ]


@pytest.mark.asyncio
async def test_discovery_loads_the_official_controller_schema() -> None:
    session = QueueSession(
        [
            [{"id": "sub-private"}],
            {"id": "sub-private", "resourceGroups": [{"id": "rg-private"}]},
            {
                "id": "rg-private",
                "resources": [{"id": "gw-private", "type": "GWD3"}],
            },
            {
                "id": "gw-private",
                "connectedControllers": [{"id": "wdc-private", "type": "WDC"}],
            },
            {
                "id": "wdc-private",
                "manufacturer": "SELTRON",
                "model": "WDC20",
                "softwareVersion": "3.5.1",
                "schemaCode": 0,
            },
            [{"id": "SELTRON.WDC20.3.5.1"}],
            {
                "code": 0,
                "sources": [{"code": "LiquidFuelBoiler", "id": "LiquidFuelBoiler1"}],
                "outputs": [
                    {
                        "code": "R1",
                        "regulatedObject": "LiquidFuelBoiler",
                        "regulatedObjectId": "LiquidFuelBoiler1",
                    }
                ],
            },
        ]
    )
    api = SeltronApi(session, access_token="dummy")  # type: ignore[arg-type]

    installation = (await api.async_discover_installations())[0]

    assert installation.schema["sources"][0]["code"] == "LiquidFuelBoiler"
    assert session.urls[-2:] == [
        "https://api.seltronhome.com/api/specifications/?manufacturer=SELTRON&model=WDC20&version=3.5.1",
        "https://api.seltronhome.com/api/specifications/SELTRON.WDC20.3.5.1/schemas/0",
    ]


@pytest.mark.asyncio
async def test_refresh_preserves_discovered_schema_without_extra_requests() -> None:
    session = QueueSession(
        [
            {"id": "gw-private", "model": "GWD3E"},
            {"id": "wdc-private", "model": "WDC20"},
        ]
    )
    api = SeltronApi(session, access_token="dummy")  # type: ignore[arg-type]
    schema = {"code": 0, "outputs": [{"code": "R1"}]}
    existing = Installation(
        subscription_id="sub-private",
        resource_group_id="rg-private",
        gateway_id="gw-private",
        controller_id="wdc-private",
        gateway={},
        controller={},
        schema=schema,
    )

    refreshed = await api.async_refresh_installation(existing)

    assert refreshed.schema is schema
