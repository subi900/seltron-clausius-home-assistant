from custom_components.seltron_clausius.api import Installation
from custom_components.seltron_clausius.probe import build_probe_report


def test_probe_report_contains_no_private_identifiers() -> None:
    installation = Installation(
        subscription_id="private-sub",
        resource_group_id="private-group",
        gateway_id="private-gateway",
        controller_id="private-controller",
        gateway={"id": "private-gateway", "model": "GWD3E", "firmware": "1.4.6"},
        controller={"id": "private-controller", "model": "WDC20", "serialNumber": "private-serial"},
    )

    report = build_probe_report([installation])
    rendered = repr(report)

    assert "private-" not in rendered
    assert report["installations"][0]["gateway"]["model"] == "GWD3E"
    assert report["installations"][0]["controller"]["model"] == "WDC20"
