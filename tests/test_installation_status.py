import json
from pathlib import Path

from custom_components.seltron_clausius.models import parse_installation_status


def test_parse_confirmed_sanitized_installation_fixture() -> None:
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "installation.json").read_text(
            encoding="utf-8"
        )
    )

    status = parse_installation_status(payload["gateway"], payload["controller"])

    assert status.gateway.connected is True
    assert status.gateway.model == "GWD3E"
    assert status.gateway.hardware_version == "1.0.0"
    assert status.gateway.firmware_version == "1.4.6"
    assert status.controller.connected is True
    assert status.controller.model == "WDC20"
    assert status.controller.hardware_version == "2.0.0"
    assert status.controller.firmware_version == "3.5.1"
    assert len(status.temperatures) == 4
    assert [(relay.code, relay.is_active) for relay in status.relays] == [
        ("R1", False),
        ("R4", True),
    ]
    assert [(circuit.code, circuit.mode, circuit.program) for circuit in status.circuits] == [
        ("DHWC", "Timer", "P1"),
        ("HC1", "Off", "P2"),
    ]
    assert status.active_warning_categories == ()
