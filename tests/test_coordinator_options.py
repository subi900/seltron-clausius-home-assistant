from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from custom_components.seltron_clausius.const import CONF_POLLING_INTERVAL
from custom_components.seltron_clausius.coordinator import SeltronCoordinator


@pytest.mark.parametrize(
    ("options", "expected_seconds"),
    [
        ({CONF_POLLING_INTERVAL: 60}, 60),
        ({}, 300),
        ({CONF_POLLING_INTERVAL: 31}, 300),
        ({CONF_POLLING_INTERVAL: "not-a-number"}, 300),
    ],
)
def test_coordinator_uses_valid_polling_option_or_default(
    options: dict[str, object], expected_seconds: int
) -> None:
    hass = Mock()
    entry = SimpleNamespace(
        data={"access_token": "access", "refresh_token": "refresh", "expires_at": 0},
        options=options,
    )

    with patch(
        "custom_components.seltron_clausius.coordinator.async_get_clientsession",
        return_value=Mock(),
    ):
        coordinator = SeltronCoordinator(hass, entry)

    assert coordinator.update_interval == timedelta(seconds=expected_seconds)
