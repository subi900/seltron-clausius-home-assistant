from __future__ import annotations

from datetime import datetime
from math import isfinite
from typing import Final

OPERATION_MODES: Final[dict[str, tuple[str, ...]]] = {
    "HC1": ("Timer", "Day", "Night", "Off"),
    "HC2": ("Timer", "Day", "Night", "Off"),
    "DHWC": ("Timer", "On", "Off"),
}

USER_FUNCTIONS: Final[dict[str, tuple[str, ...]]] = {
    "HC1": ("Off", "Party", "Eco", "Holiday"),
    "HC2": ("Off", "Party", "Eco", "Holiday"),
    "DHWC": ("Off", "SingleActivation"),
}

# minimum, maximum, step; copied from the official normal-user Clausius client.
SETPOINT_SPECS: Final[dict[str, dict[str, tuple[float, float, float]]]] = {
    "HC1": {"day": (8.0, 30.0, 0.5), "night": (4.0, 40.0, 0.5)},
    "HC2": {"day": (8.0, 30.0, 0.5), "night": (4.0, 40.0, 0.5)},
    "DHWC": {"on": (20.0, 80.0, 0.5)},
}


def validate_operation_mode(circuit_code: str, mode: str) -> str:
    """Return an exact confirmed mode or reject it before network I/O."""
    if mode not in OPERATION_MODES.get(circuit_code.upper(), ()):
        raise ValueError(f"Unsupported operation mode for circuit {circuit_code}")
    return mode


def validate_user_function(circuit_code: str, function: str) -> str:
    """Return an official normal-user function or reject it before network I/O."""
    if function not in USER_FUNCTIONS.get(circuit_code.upper(), ()):
        raise ValueError(f"Unsupported user function for circuit {circuit_code}")
    return function


def validate_user_function_payload(
    circuit_code: str, payload: dict[str, object]
) -> dict[str, object]:
    """Validate the complete official user-function payload."""
    function = payload.get("type")
    if not isinstance(function, str):
        raise TypeError("User-function type is required")
    validate_user_function(circuit_code, function)
    timetable = payload.get("activeTimetable")
    if not isinstance(timetable, str) or not timetable:
        raise ValueError("Current active timetable is required")
    expected = {"type", "activeTimetable"}
    if function in {"Party", "Eco", "Holiday"}:
        expected |= {"temperature", "activeUntil"}
        temperature = payload.get("temperature")
        if (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not isfinite(float(temperature))
        ):
            raise ValueError("Finite user-function temperature is required")
        active_until = payload.get("activeUntil")
        if not isinstance(active_until, str):
            raise ValueError("User-function expiration is required")
        try:
            parsed = datetime.fromisoformat(active_until)
        except ValueError as err:
            raise ValueError("Invalid user-function expiration") from err
        if parsed.tzinfo is not None or parsed.strftime("%Y-%m-%dT%H:%M:%S") != active_until:
            raise ValueError("Invalid user-function expiration")
    if set(payload) != expected:
        raise ValueError("Unsupported user-function payload fields")
    return dict(payload)


def validate_setpoint(circuit_code: str, key: str, value: float) -> float:
    """Validate a confirmed setpoint key, finite value, range, and step."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Setpoint must be numeric")  # noqa: TRY004 - one public validation error type
    numeric = float(value)
    if not isfinite(numeric):
        raise ValueError("Setpoint must be finite")
    specs = SETPOINT_SPECS.get(circuit_code.upper(), {})
    if key not in specs:
        raise ValueError(f"Unsupported setpoint for circuit {circuit_code}")
    minimum, maximum, step = specs[key]
    if numeric < minimum or numeric > maximum:
        raise ValueError("Setpoint is outside the confirmed range")
    increments = (numeric - minimum) / step
    if abs(increments - round(increments)) > 1e-9:
        raise ValueError("Setpoint is not aligned to the confirmed step")
    return numeric
