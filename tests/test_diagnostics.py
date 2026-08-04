from custom_components.seltron_clausius.diagnostics import redact_payload


def test_redaction_removes_credentials_and_private_identifiers_recursively() -> None:
    raw = {
        "id": "private-id",
        "serialNumber": "private-serial",
        "access_token": "private-access",
        "nested": {"refreshToken": "private-refresh", "model": "WDC20"},
        "temperature": 25.8,
    }

    redacted = redact_payload(raw)
    rendered = repr(redacted)

    assert "private-id" not in rendered
    assert "private-serial" not in rendered
    assert "private-access" not in rendered
    assert "private-refresh" not in rendered
    assert redacted["nested"]["model"] == "WDC20"
    assert redacted["temperature"] == 25.8
