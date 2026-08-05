from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from custom_components.seltron_clausius.const import DOMAIN
from custom_components.seltron_clausius.diagnostics import (
    async_get_config_entry_diagnostics,
    redact_payload,
)
from custom_components.seltron_clausius.models import parse_installation_status
from custom_components.seltron_clausius.runtime import RuntimeData


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


@pytest.mark.asyncio
async def test_config_entry_diagnostics_redacts_tokens_labels_and_installation_ids() -> None:
    runtime = RuntimeData(
        status=parse_installation_status(
            {"model": "GWD3E", "connectionState": True},
            {"model": "WDC20", "isActive": True, "circuits": []},
        ),
        last_successful_update=datetime(2026, 8, 5, tzinfo=UTC),
    )
    coordinator = SimpleNamespace(data=runtime)
    entry = SimpleNamespace(
        entry_id="entry-id",
        data={
            "access_token": "private-access",
            "refresh_token": "private-refresh",
            "expires_at": 1234.0,
        },
        options={"labels": {"relay:R1": "private-label"}},
    )
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    rendered = repr(diagnostics)

    assert "private-access" not in rendered
    assert "private-refresh" not in rendered
    assert "private-label" not in rendered
    assert diagnostics["runtime"]["status"]["gateway"]["model"] == "GWD3E"
