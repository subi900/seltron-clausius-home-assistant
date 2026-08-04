from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from custom_components.seltron_clausius.const import DOMAIN
from custom_components.seltron_clausius.models import parse_installation_status
from custom_components.seltron_clausius.number import async_setup_entry as setup_numbers
from custom_components.seltron_clausius.runtime import RuntimeData
from custom_components.seltron_clausius.select import async_setup_entry as setup_selects


class FakeCoordinator:
    def __init__(self, data):
        self.data = data
        self.entry = SimpleNamespace(
            entry_id="entry-test",
            options={"labels": {"circuit:HC1": "Heizkörperkreis"}},
        )
        self.last_update_success = True
        self.mode_calls = []
        self.setpoint_calls = []

    def async_add_listener(self, *args, **kwargs):
        return lambda: None

    async def async_set_operation_mode(self, code, mode):
        self.mode_calls.append((code, mode))

    async def async_set_setpoint(self, code, key, value):
        self.setpoint_calls.append((code, key, value))


def coordinator() -> FakeCoordinator:
    status = parse_installation_status(
        {"model": "GWD3E", "connectionState": True},
        {
            "model": "WDC20",
            "isActive": True,
            "circuits": [
                {
                    "code": "HC1",
                    "name": "Heizkreis",
                    "operationMode": {"type": "Timer"},
                    "activeTimetable": "P1",
                    "temperatures": {"day": 21.0, "night": 17.0, "off": 6.0},
                },
                {
                    "code": "DHWC",
                    "name": "Brauchwasser",
                    "operationMode": {"type": "On"},
                    "activeTimetable": "P1",
                    "temperatures": {"on": 55.0, "off": 4.0},
                },
                {
                    "code": "UNKNOWN",
                    "name": "Unbekannt",
                    "operationMode": {"type": "Off"},
                    "activeTimetable": "P1",
                },
            ],
        },
    )
    return FakeCoordinator(
        RuntimeData(status, datetime(2026, 8, 3, tzinfo=UTC))
    )


@pytest.mark.asyncio
async def test_only_confirmed_write_entities_are_exposed_and_call_coordinator() -> None:
    coordinator_ = coordinator()
    entry = coordinator_.entry
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator_}})
    selects = []
    numbers = []

    await setup_selects(hass, entry, selects.extend)
    await setup_numbers(hass, entry, numbers.extend)

    assert len(selects) == 2
    assert len(numbers) == 3
    assert all("UNKNOWN" not in entity.unique_id for entity in [*selects, *numbers])

    hc_mode = next(entity for entity in selects if "HC1" in entity.unique_id)
    assert hc_mode.name == "Heizkörperkreis operation mode"
    assert hc_mode.current_option == "Timer"
    assert hc_mode.options == ["Timer", "Day", "Night", "Off"]
    await hc_mode.async_select_option("Day")
    assert coordinator_.mode_calls == [("HC1", "Day")]

    day = next(entity for entity in numbers if entity.unique_id.endswith("HC1_day"))
    assert day.name == "Heizkörperkreis day setpoint"
    assert day.native_value == 21.0
    assert day.native_min_value == 8.0
    assert day.native_max_value == 30.0
    assert day.native_step == 0.5
    await day.async_set_native_value(21.5)
    assert coordinator_.setpoint_calls == [("HC1", "day", 21.5)]
