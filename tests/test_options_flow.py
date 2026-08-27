from types import SimpleNamespace

import pytest

from custom_components.seltron_clausius.config_flow import SeltronOptionsFlow
from custom_components.seltron_clausius.const import (
    CONF_POLLING_INTERVAL,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
    POLLING_INTERVAL_OPTIONS,
    POLLING_INTERVALS,
)
from custom_components.seltron_clausius.models import parse_installation_status
from custom_components.seltron_clausius.runtime import RuntimeData


@pytest.mark.asyncio
async def test_options_flow_lists_discovered_channels_and_persists_normalized_labels() -> None:
    entry = SimpleNamespace(
        entry_id="entry-test",
        options={
            "labels": {"relay:R1": "Existing label"},
            CONF_POLLING_INTERVAL: 600,
            "future_option": True,
        },
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
    assert keys == {
        CONF_POLLING_INTERVAL,
        "temperature:T2",
        "relay:R1",
        "circuit:HC1",
    }
    interval_marker = next(
        key
        for key in form["data_schema"].schema
        if str(key.schema) == CONF_POLLING_INTERVAL
    )
    assert interval_marker.default() == 600
    interval_validator = form["data_schema"].schema[interval_marker]
    assert tuple(interval_validator.container) == POLLING_INTERVALS
    assert interval_validator.container == POLLING_INTERVAL_OPTIONS

    result = await flow.async_step_init(
        {
            CONF_POLLING_INTERVAL: 120,
            "temperature:T2": "  Außentemperatur  ",
            "relay:R1": "Umlaufpumpe der Gasheizung",
            "circuit:HC1": "Heizkörperkreis",
        }
    )
    assert result["data"] == {
        CONF_POLLING_INTERVAL: 120,
        "future_option": True,
        "labels": {
            "temperature:T2": "Außentemperatur",
            "relay:R1": "Umlaufpumpe der Gasheizung",
            "circuit:HC1": "Heizkörperkreis",
        }
    }


@pytest.mark.asyncio
async def test_options_flow_defaults_polling_interval_and_rejects_unknown_value() -> None:
    entry = SimpleNamespace(entry_id="entry-test", options={})
    status = SimpleNamespace(temperatures=(), relays=(), circuits=())
    coordinator = SimpleNamespace(data=RuntimeData(status, None))
    flow = SeltronOptionsFlow(entry)
    flow.hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})

    form = await flow.async_step_init()
    interval_marker = next(iter(form["data_schema"].schema))
    assert interval_marker.default() == DEFAULT_POLLING_INTERVAL

    invalid = await flow.async_step_init({CONF_POLLING_INTERVAL: 31})
    assert invalid["errors"] == {"base": "invalid_polling_interval"}


@pytest.mark.asyncio
async def test_options_flow_replaces_invalid_stored_interval_with_default() -> None:
    entry = SimpleNamespace(
        entry_id="entry-test", options={CONF_POLLING_INTERVAL: 31}
    )
    status = SimpleNamespace(temperatures=(), relays=(), circuits=())
    coordinator = SimpleNamespace(data=RuntimeData(status, None))
    flow = SeltronOptionsFlow(entry)
    flow.hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})

    form = await flow.async_step_init()
    interval_marker = next(iter(form["data_schema"].schema))

    assert interval_marker.default() == DEFAULT_POLLING_INTERVAL
