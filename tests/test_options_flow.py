from types import SimpleNamespace

import pytest

from custom_components.seltron_clausius.config_flow import SeltronOptionsFlow
from custom_components.seltron_clausius.const import DOMAIN
from custom_components.seltron_clausius.models import parse_installation_status
from custom_components.seltron_clausius.runtime import RuntimeData


@pytest.mark.asyncio
async def test_options_flow_lists_discovered_channels_and_persists_normalized_labels() -> None:
    entry = SimpleNamespace(
        entry_id="entry-test",
        options={"labels": {"relay:R1": "Existing label"}},
    )
    status = parse_installation_status(
        {"model": "GWD3E", "connectionState": True},
        {
            "model": "WDC20",
            "isActive": True,
            "temperatureSensors": [
                {"code": "T2", "name": "Sensor 2", "measured": 10.0}
            ],
            "relays": [{"code": "R1", "name": "Relay 1", "state": True}],
            "circuits": [
                {
                    "code": "HC1",
                    "name": "Circuit 1",
                    "operationMode": {"type": "Timer"},
                    "activeTimetable": "P1",
                }
            ],
        },
    )
    coordinator = SimpleNamespace(data=RuntimeData(status, None))
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})
    flow = SeltronOptionsFlow(entry)
    flow.hass = hass

    form = await flow.async_step_init()
    keys = {str(key.schema) for key in form["data_schema"].schema}
    assert keys == {"temperature:T2", "relay:R1", "circuit:HC1"}

    result = await flow.async_step_init(
        {
            "temperature:T2": "  Außentemperatur  ",
            "relay:R1": "Umlaufpumpe der Gasheizung",
            "circuit:HC1": "Heizkörperkreis",
        }
    )
    assert result["data"] == {
        "labels": {
            "temperature:T2": "Außentemperatur",
            "relay:R1": "Umlaufpumpe der Gasheizung",
            "circuit:HC1": "Heizkörperkreis",
        }
    }
