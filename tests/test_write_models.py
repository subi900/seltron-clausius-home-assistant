from custom_components.seltron_clausius.models import parse_heating_circuits


def test_write_capabilities_are_exposed_only_for_confirmed_wdc_circuit_codes() -> None:
    raw = [
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
            "temperatures": {"day": 20.0},
        },
    ]

    hc, dhwc, unknown = parse_heating_circuits(raw)

    assert hc.supported_modes == ("Timer", "Day", "Night", "Off")
    assert [(item.key, item.value, item.minimum, item.maximum, item.step) for item in hc.setpoints] == [
        ("day", 21.0, 8.0, 30.0, 0.5),
        ("night", 17.0, 4.0, 40.0, 0.5),
    ]
    assert dhwc.supported_modes == ("Timer", "On", "Off")
    assert [(item.key, item.value, item.minimum, item.maximum, item.step) for item in dhwc.setpoints] == [
        ("on", 55.0, 20.0, 80.0, 0.5),
    ]
    assert unknown.supported_modes == ()
    assert unknown.setpoints == ()
