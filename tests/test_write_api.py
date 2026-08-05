from urllib.parse import quote
from uuid import UUID

import pytest

from custom_components.seltron_clausius.api import (
    API_BASE_URL,
    Installation,
    SeltronApi,
)


class FakeResponse:
    status = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def raise_for_status(self) -> None:
        return None


class RecordingSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def put(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse()


def installation() -> Installation:
    return Installation(
        subscription_id="sub/id",
        resource_group_id="group id",
        gateway_id="gateway/id",
        controller_id="controller id",
        gateway={},
        controller={},
    )


@pytest.mark.asyncio
async def test_put_operation_mode_matches_official_client_contract() -> None:
    item = installation()
    expected_url = (
        f"{API_BASE_URL}/api/subscriptions/{quote(item.subscription_id, safe='')}"
        f"/resourceGroups/{quote(item.resource_group_id, safe='')}"
        f"/WDC/{quote(item.controller_id, safe='')}/HC1/operationMode"
    )
    session = RecordingSession()

    await SeltronApi(session, access_token="secret").async_set_operation_mode(
        item, "HC1", "Day"
    )

    assert len(session.calls) == 1
    url, kwargs = session.calls[0]
    assert url == expected_url
    assert kwargs["json"] == {"type": "Day"}
    assert kwargs["headers"]["Authorization"] == "Bearer secret"
    assert UUID(kwargs["headers"]["correlationId"])
    assert "params" not in kwargs


@pytest.mark.asyncio
async def test_put_temperatures_matches_official_client_contract() -> None:
    item = installation()
    expected_url = (
        f"{API_BASE_URL}/api/subscriptions/{quote(item.subscription_id, safe='')}"
        f"/resourceGroups/{quote(item.resource_group_id, safe='')}"
        f"/WDC/{quote(item.controller_id, safe='')}/DHWC/temperatures"
    )
    session = RecordingSession()

    await SeltronApi(session, access_token="secret").async_set_temperatures(
        item, "DHWC", {"on": 55.5}
    )

    assert len(session.calls) == 1
    url, kwargs = session.calls[0]
    assert url == expected_url
    assert kwargs["json"] == {"on": 55.5}
    assert kwargs["headers"]["Authorization"] == "Bearer secret"
    assert UUID(kwargs["headers"]["correlationId"])


@pytest.mark.asyncio
async def test_put_user_function_matches_official_client_contract() -> None:
    item = installation()
    expected_url = (
        f"{API_BASE_URL}/api/subscriptions/{quote(item.subscription_id, safe='')}"
        f"/resourceGroups/{quote(item.resource_group_id, safe='')}"
        f"/WDC/{quote(item.controller_id, safe='')}/HC1/userFunction"
    )
    session = RecordingSession()
    payload = {
        "type": "Party",
        "temperature": 23.0,
        "activeUntil": "2026-08-04T22:00:00",
        "activeTimetable": "P1",
    }

    await SeltronApi(session, access_token="secret").async_set_user_function(
        item, "HC1", payload
    )

    url, kwargs = session.calls[0]
    assert url == expected_url
    assert kwargs["json"] == payload
    assert UUID(kwargs["headers"]["correlationId"])


@pytest.mark.asyncio
async def test_write_api_rejects_unconfirmed_values_before_network() -> None:
    session = RecordingSession()
    api = SeltronApi(session, access_token="secret")
    item = installation()

    with pytest.raises(ValueError):
        await api.async_set_operation_mode(item, "HC1", "Boost")
    with pytest.raises(ValueError):
        await api.async_set_operation_mode(item, "UNKNOWN", "Off")
    with pytest.raises(ValueError):
        await api.async_set_temperatures(item, "DHWC", {"on": 80.1})
    with pytest.raises(ValueError):
        await api.async_set_temperatures(item, "HC1", {"day": 20.25})
    with pytest.raises(ValueError):
        await api.async_set_user_function(item, "DHWC", {"type": "Party"})
    with pytest.raises(ValueError):
        await api.async_set_user_function(
            item,
            "HC1",
            {"type": "Party", "unexpected": True},
        )

    assert session.calls == []
