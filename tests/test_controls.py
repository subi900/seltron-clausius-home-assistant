import math

import pytest

from custom_components.seltron_clausius.controls import (
    validate_operation_mode,
    validate_setpoint,
    validate_user_function,
)


@pytest.mark.parametrize(
    ("code", "mode"),
    [("HC1", "Timer"), ("HC2", "Night"), ("DHWC", "On")],
)
def test_confirmed_operation_modes_are_accepted(code: str, mode: str) -> None:
    assert validate_operation_mode(code, mode) == mode


@pytest.mark.parametrize(
    ("code", "mode"),
    [("HC1", "On"), ("DHWC", "Day"), ("UNKNOWN", "Off"), ("HC1", "day")],
)
def test_unconfirmed_operation_modes_are_rejected(code: str, mode: str) -> None:
    with pytest.raises(ValueError):
        validate_operation_mode(code, mode)


@pytest.mark.parametrize(
    ("code", "key", "value"),
    [
        ("HC1", "day", 8.0),
        ("HC2", "day", 30.0),
        ("HC1", "night", 17.5),
        ("DHWC", "on", 80.0),
    ],
)
def test_confirmed_setpoints_are_accepted(code: str, key: str, value: float) -> None:
    assert validate_setpoint(code, key, value) == float(value)


@pytest.mark.parametrize(
    ("code", "key", "value"),
    [
        ("HC1", "day", 7.5),
        ("HC1", "day", 30.5),
        ("HC1", "day", 21.25),
        ("HC1", "off", 6.0),
        ("DHWC", "day", 50.0),
        ("UNKNOWN", "day", 20.0),
        ("HC1", "day", math.nan),
        ("HC1", "day", math.inf),
        ("HC1", "day", True),
    ],
)
def test_unconfirmed_or_invalid_setpoints_are_rejected(
    code: str, key: str, value: float
) -> None:
    with pytest.raises(ValueError):
        validate_setpoint(code, key, value)


@pytest.mark.parametrize(
    ("code", "function"),
    [
        ("HC1", "Party"),
        ("HC1", "Eco"),
        ("HC2", "Holiday"),
        ("DHWC", "SingleActivation"),
        ("DHWC", "Off"),
    ],
)
def test_confirmed_user_functions_are_accepted(code: str, function: str) -> None:
    assert validate_user_function(code, function) == function


@pytest.mark.parametrize(
    ("code", "function"),
    [("HC1", "SingleActivation"), ("DHWC", "Party"), ("HC1", "party")],
)
def test_unconfirmed_user_functions_are_rejected(code: str, function: str) -> None:
    with pytest.raises(ValueError):
        validate_user_function(code, function)
