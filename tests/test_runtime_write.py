from __future__ import annotations

from dataclasses import replace
from datetime import datetime

import pytest

from custom_components.seltron_clausius.api import Installation, TokenSet
from custom_components.seltron_clausius.runtime import (
    SeltronRuntime,
    WriteVerificationError,
)


def make_installation(*, mode: str = "Timer", day: float = 21.0) -> Installation:
    return Installation(
        subscription_id="sub",
        resource_group_id="group",
        gateway_id="gateway",
        controller_id="controller",
        gateway={"model": "GWD3E", "connectionState": True},
        controller={
            "model": "WDC20",
            "isActive": True,
            "clock": {"dateTime": "2026-08-04T20:00:00"},
            "circuits": [
                {
                    "code": "HC1",
                    "name": "Heizkreis",
                    "operationMode": {"type": mode},
                    "activeTimetable": "P1",
                    "temperatures": {"off": 6.0, "day": day, "night": 17.0},
                    "userFunction": {"type": "Off"},
                }
            ],
        },
    )


class WriteApi:
    def __init__(self, installation: Installation, *, apply_writes: bool = True) -> None:
        self.installation = installation
        self.apply_writes = apply_writes
        self.mode_calls: list[tuple[str, str]] = []
        self.temperature_calls: list[tuple[str, dict[str, float]]] = []
        self.user_function_calls: list[tuple[str, dict]] = []
        self.refresh_calls = 0

    async def async_discover_installations(self):
        return [self.installation]

    async def async_refresh_installation(self, installation):
        self.refresh_calls += 1
        return self.installation

    async def async_set_operation_mode(self, installation, code, mode):
        self.mode_calls.append((code, mode))
        if self.apply_writes:
            circuit = dict(self.installation.controller["circuits"][0])
            circuit["operationMode"] = {"type": mode}
            controller = dict(self.installation.controller)
            controller["circuits"] = [circuit]
            self.installation = replace(self.installation, controller=controller)

    async def async_set_temperatures(self, installation, code, temperatures):
        self.temperature_calls.append((code, temperatures))
        if self.apply_writes:
            circuit = dict(self.installation.controller["circuits"][0])
            current = dict(circuit["temperatures"])
            current.update(temperatures)
            circuit["temperatures"] = current
            controller = dict(self.installation.controller)
            controller["circuits"] = [circuit]
            self.installation = replace(self.installation, controller=controller)

    async def async_set_user_function(self, installation, code, user_function):
        self.user_function_calls.append((code, user_function))
        if self.apply_writes:
            circuit = dict(self.installation.controller["circuits"][0])
            circuit["userFunction"] = dict(user_function)
            controller = dict(self.installation.controller)
            controller["circuits"] = [circuit]
            self.installation = replace(self.installation, controller=controller)


class DelayedSetpointWriteApi(WriteApi):
    def __init__(self, installation: Installation) -> None:
        super().__init__(installation, apply_writes=False)
        self._pending_temperatures: dict[str, float] = {}

    async def async_set_temperatures(self, installation, code, temperatures):
        self.temperature_calls.append((code, temperatures))
        self._pending_temperatures = temperatures

    async def async_refresh_installation(self, installation):
        self.refresh_calls += 1
        if self.refresh_calls == 2 and self._pending_temperatures:
            circuit = dict(self.installation.controller["circuits"][0])
            temperatures = dict(circuit["temperatures"])
            temperatures.update(self._pending_temperatures)
            circuit["temperatures"] = temperatures
            controller = dict(self.installation.controller)
            controller["circuits"] = [circuit]
            self.installation = replace(self.installation, controller=controller)
        return self.installation


class DelayedModeWriteApi(WriteApi):
    def __init__(self, installation: Installation) -> None:
        super().__init__(installation, apply_writes=False)
        self._pending_mode: str | None = None

    async def async_set_operation_mode(self, installation, code, mode):
        self.mode_calls.append((code, mode))
        self._pending_mode = mode

    async def async_refresh_installation(self, installation):
        self.refresh_calls += 1
        if self.refresh_calls == 2 and self._pending_mode is not None:
            circuit = dict(self.installation.controller["circuits"][0])
            circuit["operationMode"] = {"type": self._pending_mode}
            controller = dict(self.installation.controller)
            controller["circuits"] = [circuit]
            self.installation = replace(self.installation, controller=controller)
        return self.installation


def make_runtime(api: WriteApi) -> SeltronRuntime:
    async def persist(_tokens):
        return None

    return SeltronRuntime(
        object(),
        TokenSet("access", "refresh", 9999999999.0),
        persist_tokens=persist,
        api_factory=lambda _session, *, access_token: api,
        now=lambda: 1000.0,
        confirmation_delays=(0.0, 0.0, 0.0),
    )


@pytest.mark.asyncio
async def test_runtime_writes_mode_and_rereads() -> None:
    api = WriteApi(make_installation())
    runtime = make_runtime(api)
    await runtime.async_update()

    data = await runtime.async_set_operation_mode("HC1", "Day")

    assert api.mode_calls == [("HC1", "Day")]
    assert api.refresh_calls == 1
    assert data.status.circuits[0].mode == "Day"


@pytest.mark.asyncio
async def test_runtime_validates_temperature_then_rereads() -> None:
    api = WriteApi(make_installation())
    runtime = make_runtime(api)
    await runtime.async_update()

    data = await runtime.async_set_setpoint("HC1", "day", 21.5)

    assert api.temperature_calls == [("HC1", {"day": 21.5})]
    assert api.refresh_calls == 1
    assert data.status.circuits[0].setpoints[0].value == 21.5


@pytest.mark.asyncio
async def test_runtime_rejects_invalid_write_before_network() -> None:
    api = WriteApi(make_installation())
    runtime = make_runtime(api)
    await runtime.async_update()

    with pytest.raises(ValueError):
        await runtime.async_set_setpoint("HC1", "day", 21.25)
    with pytest.raises(ValueError):
        await runtime.async_set_operation_mode("HC1", "On")

    assert api.mode_calls == []
    assert api.temperature_calls == []
    assert api.refresh_calls == 0


@pytest.mark.asyncio
async def test_runtime_does_not_claim_success_when_readback_differs() -> None:
    api = WriteApi(make_installation(), apply_writes=False)
    runtime = make_runtime(api)
    await runtime.async_update()

    with pytest.raises(WriteVerificationError):
        await runtime.async_set_operation_mode("HC1", "Day")

    assert api.refresh_calls == 3


@pytest.mark.asyncio
async def test_runtime_retries_until_delayed_mode_readback_is_confirmed() -> None:
    api = DelayedModeWriteApi(make_installation())
    runtime = make_runtime(api)
    await runtime.async_update()

    data = await runtime.async_set_operation_mode("HC1", "Day")

    assert api.refresh_calls == 2
    assert data.status.circuits[0].mode == "Day"


@pytest.mark.asyncio
async def test_runtime_retries_until_delayed_setpoint_readback_is_confirmed() -> None:
    api = DelayedSetpointWriteApi(make_installation())
    runtime = make_runtime(api)
    await runtime.async_update()

    data = await runtime.async_set_setpoint("HC1", "day", 21.5)

    assert api.refresh_calls == 2
    assert data.status.circuits[0].setpoints[0].value == 21.5


@pytest.mark.asyncio
async def test_runtime_builds_party_function_from_controller_state_and_rereads() -> None:
    api = WriteApi(make_installation(day=23.0))
    runtime = make_runtime(api)
    await runtime.async_update()

    data = await runtime.async_set_user_function(
        "HC1", "Party", active_until=datetime.fromisoformat("2026-08-18T10:30:00")
    )

    assert api.user_function_calls == [
        (
            "HC1",
            {
                "type": "Party",
                "activeTimetable": "P1",
                "temperature": 23.0,
                "activeUntil": "2026-08-18T10:30:00",
            },
        )
    ]
    assert api.refresh_calls == 1
    assert data.status.circuits[0].user_function == "Party"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "active_until",
    [
        datetime.fromisoformat("2026-08-04T20:00:00"),
        datetime.fromisoformat("2027-08-06T20:00:00"),
    ],
)
async def test_runtime_rejects_invalid_user_function_end_before_network(
    active_until: datetime,
) -> None:
    api = WriteApi(make_installation())
    runtime = make_runtime(api)
    await runtime.async_update()

    with pytest.raises(ValueError, match="future|366 days"):
        await runtime.async_set_user_function(
            "HC1", "Holiday", active_until=active_until
        )

    assert api.user_function_calls == []
