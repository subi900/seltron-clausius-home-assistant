from custom_components.seltron_clausius.models import (
    parse_active_warnings,
    parse_heating_circuits,
    parse_regulated_outputs,
    parse_relays,
    parse_temperature_sensors,
)


def test_temperature_parser_separates_values_and_drops_disconnected_sentinel() -> None:
    raw = [
        {"code": "T1", "name": "Buffer", "measured": 60.5, "calculated": 61.0},
        {"code": "T2", "name": "Room", "measured": 25.8, "calculated": 29.4},
        {"code": "T3", "name": "Unused", "measured": -50, "calculated": -50.0},
    ]

    parsed = parse_temperature_sensors(raw)

    assert [(item.code, item.kind, item.value) for item in parsed] == [
        ("T1", "measured", 60.5),
        ("T1", "calculated", 61.0),
        ("T2", "measured", 25.8),
        ("T2", "calculated", 29.4),
    ]


def test_temperature_parser_accepts_cloud_field_names() -> None:
    raw = [
        {
            "code": "T2",
            "name": "Room",
            "measuredTemperature": 25.8,
            "calculatedTemperature": 29.4,
        }
    ]

    parsed = parse_temperature_sensors(raw)

    assert [(item.kind, item.value) for item in parsed] == [
        ("measured", 25.8),
        ("calculated", 29.4),
    ]


def test_relay_parser_preserves_unknown_relay_identity_without_guessing_function() -> None:
    parsed = parse_relays(
        [
            {"code": "R1", "name": "Heating pump", "isActive": False},
            {"code": "R4", "name": "", "isActive": True},
        ]
    )

    assert [(item.code, item.name, item.is_active) for item in parsed] == [
        ("R1", "Heating pump", False),
        ("R4", "R4", True),
    ]


def test_relay_parser_accepts_confirmed_cloud_state_field() -> None:
    parsed = parse_relays([{"code": "R4", "name": "", "state": True}])

    assert [(item.code, item.name, item.is_active) for item in parsed] == [
        ("R4", "R4", True)
    ]


def test_heating_circuit_parser_exposes_mode_and_program_as_status_only() -> None:
    parsed = parse_heating_circuits(
        [
            {"code": "HC1", "name": "", "operatingMode": "Off", "activeProgram": "P2"},
            {"code": "HC2", "name": "Upstairs", "operatingMode": "Timer", "activeProgram": "P1"},
        ]
    )

    assert [(item.code, item.name, item.mode, item.program) for item in parsed] == [
        ("HC1", "HC1", "Off", "P2"),
        ("HC2", "Upstairs", "Timer", "P1"),
    ]


def test_heating_circuit_parser_accepts_confirmed_cloud_fields() -> None:
    parsed = parse_heating_circuits(
        [
            {
                "code": "DHWC",
                "name": "",
                "operationMode": {"type": "Timer"},
                "activeTimetable": "P1",
            }
        ]
    )

    assert [(item.code, item.mode, item.program) for item in parsed] == [
        ("DHWC", "Timer", "P1")
    ]


def test_heating_circuit_parser_keeps_user_function_state() -> None:
    parsed = parse_heating_circuits(
        [
            {
                "code": "HC1",
                "operationMode": {"type": "Timer"},
                "activeTimetable": "P1",
                "temperatures": {"off": 6.0, "day": 22.0, "night": 18.0},
                "userFunction": {
                    "type": "Party",
                    "temperature": 24.0,
                    "activeUntil": "2026-08-04T22:00:00",
                },
            }
        ]
    )

    assert parsed[0].user_function == "Party"
    assert parsed[0].user_function_temperature == 24.0
    assert parsed[0].user_function_active_until == "2026-08-04T22:00:00"
    assert parsed[0].frost_temperature == 6.0


def test_warning_parser_returns_only_explicitly_active_warnings() -> None:
    parsed = parse_active_warnings(
        [
            {"code": "S1", "category": "sensor", "isActive": False},
            {"code": "C1", "category": "communication", "isActive": True},
        ]
    )

    assert [(item.code, item.category) for item in parsed] == [
        ("C1", "communication")
    ]


def test_regulated_output_parser_maps_schema_component_to_live_relay_state() -> None:
    parsed = parse_regulated_outputs(
        [{"code": "R1", "state": True}],
        {
            "sources": [{"code": "LiquidFuelBoiler", "id": "LiquidFuelBoiler1"}],
            "outputs": [
                {
                    "code": "R1",
                    "regulatedObject": "LiquidFuelBoiler",
                    "regulatedObjectId": "LiquidFuelBoiler1",
                }
            ],
        },
    )

    assert [
        (item.component_code, item.component_id, item.output_code, item.is_active)
        for item in parsed
    ] == [("LiquidFuelBoiler", "LiquidFuelBoiler1", "R1", True)]
