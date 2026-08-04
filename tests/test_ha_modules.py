import inspect

from custom_components.seltron_clausius.const import PLATFORMS, UPDATE_INTERVAL


def test_home_assistant_modules_expose_only_confirmed_conservative_controls() -> None:
    from custom_components.seltron_clausius import (
        binary_sensor,
        config_flow,
        coordinator,
        datetime,
        number,
        select,
        sensor,
        switch,
    )

    assert config_flow.SeltronConfigFlow.VERSION == 1
    assert PLATFORMS == (
        "sensor",
        "binary_sensor",
        "number",
        "select",
        "datetime",
        "switch",
    )
    assert UPDATE_INTERVAL.total_seconds() == 300

    source = "\n".join(
        inspect.getsource(module)
        for module in (
            binary_sensor,
            config_flow,
            coordinator,
            datetime,
            sensor,
            select,
            number,
            switch,
        )
    )
    forbidden = (
        "climate",
        "relay_control",
        "service.register",
    )
    assert not any(term in source for term in forbidden)
