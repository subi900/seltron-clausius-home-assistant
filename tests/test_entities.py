import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from custom_components.seltron_clausius.binary_sensor import (
    async_setup_entry as setup_binary,
)
from custom_components.seltron_clausius.const import DOMAIN
from custom_components.seltron_clausius.datetime import (
    async_setup_entry as setup_datetimes,
)
from custom_components.seltron_clausius.models import parse_installation_status
from custom_components.seltron_clausius.runtime import RuntimeData
from custom_components.seltron_clausius.sensor import async_setup_entry as setup_sensors
from custom_components.seltron_clausius.switch import (
    async_setup_entry as setup_switches,
)


class FakeCoordinator:
    def __init__(self, data):
        self.data = data
        self.entry = SimpleNamespace(
            entry_id="entry-test",
            options={
                "labels": {
                    "temperature:T2": "Außentemperatur",
                    "relay:R1": "Umlaufpumpe der Gasheizung",
                    "circuit:HC1": "Heizkörperkreis",
                }
            },
        )
        self.last_update_success = True
        self.user_function_until = {}

    def async_add_listener(self, *args, **kwargs):
        return lambda: None


@pytest.mark.asyncio
async def test_entity_platforms_expose_confirmed_status_without_controls() -> None:
    raw = json.loads(
        (Path(__file__).parent / "fixtures" / "installation.json").read_text()
    )
    status = parse_installation_status(
        raw["gateway"],
        raw["controller"],
        {
            "sources": [
                {"code": "LiquidFuelBoiler", "id": "LiquidFuelBoiler1"},
                {"code": "WaterPump", "id": "WaterPump1"},
            ],
            "outputs": [
                {
                    "code": "R1",
                    "regulatedObject": "LiquidFuelBoiler",
                    "regulatedObjectId": "LiquidFuelBoiler1",
                },
                {
                    "code": "R2",
                    "regulatedObject": "WaterPump",
                    "regulatedObjectId": "WaterPump1",
                },
            ],
        },
    )
    coordinator = FakeCoordinator(
        RuntimeData(status, datetime(2026, 8, 3, tzinfo=UTC))
    )
    entry = coordinator.entry
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})
    sensors = []
    binary_sensors = []
    switches = []
    datetimes = []

    await setup_sensors(hass, entry, sensors.extend)
    await setup_binary(hass, entry, binary_sensors.extend)
    await setup_switches(hass, entry, switches.extend)
    await setup_datetimes(hass, entry, datetimes.extend)

    assert len(sensors) == 9
    assert len(binary_sensors) == 9
    assert len(switches) == 0
    assert len(datetimes) == 0
    assert any(entity.native_value == 29.2 for entity in sensors)
    assert any(entity.native_value == "Timer" for entity in sensors)
    assert any(entity.native_value == "P1" for entity in sensors)
    assert sum(entity.is_on is True for entity in binary_sensors) == 3
    assert all(not hasattr(entity, "async_turn_on") for entity in binary_sensors)
    assert any(
        entity.name == "Außentemperatur measured"
        and entity.unique_id == "entry-test_temperature_T2_measured"
        for entity in sensors
    )
    assert any(
        entity.name == "Umlaufpumpe der Gasheizung"
        and entity.unique_id == "entry-test_relay_R1"
        for entity in binary_sensors
    )
    boiler = next(
        entity for entity in binary_sensors if entity.name == "Flüssigbrennstoffkessel"
    )
    r1 = next(entity for entity in binary_sensors if entity.unique_id == "entry-test_relay_R1")
    assert boiler.is_on is r1.is_on
    assert boiler.extra_state_attributes == {"output": "R1"}
    assert not any(entity.name == "WaterPump" for entity in binary_sensors)

    assert any(
        entity.name == "Heizkörperkreis mode"
        and entity.unique_id == "entry-test_circuit_HC1_mode"
        for entity in sensors
    )

    controller = next(
        entity for entity in sensors if entity.device_info["model"] == "WDC20"
    )
    assert controller.device_info["hw_version"] == "2.0.0"
    assert controller.device_info["sw_version"] == "3.5.1"
