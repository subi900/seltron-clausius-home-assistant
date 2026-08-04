from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .controls import OPERATION_MODES, SETPOINT_SPECS

TemperatureKind = Literal["measured", "calculated"]


@dataclass(frozen=True)
class TemperatureReading:
    code: str
    name: str
    kind: TemperatureKind
    value: float


@dataclass(frozen=True)
class RelayState:
    code: str
    name: str
    is_active: bool


@dataclass(frozen=True)
class RegulatedOutputState:
    """Semantic component state mapped from an official-schema relay output."""

    component_code: str
    component_id: str
    output_code: str
    is_active: bool


@dataclass(frozen=True)
class HeatingCircuitState:
    code: str
    name: str
    mode: str
    program: str | None
    supported_modes: tuple[str, ...] = ()
    setpoints: tuple[TemperatureSetpoint, ...] = ()
    user_function: str = "Off"
    user_function_temperature: float | None = None
    user_function_active_until: str | None = None
    frost_temperature: float | None = None


@dataclass(frozen=True)
class TemperatureSetpoint:
    key: str
    value: float
    minimum: float
    maximum: float
    step: float


@dataclass(frozen=True)
class WarningState:
    code: str
    category: str


@dataclass(frozen=True)
class DeviceStatus:
    manufacturer: str
    model: str
    hardware_version: str | None
    firmware_version: str | None
    connected: bool


@dataclass(frozen=True)
class InstallationStatus:
    gateway: DeviceStatus
    controller: DeviceStatus
    temperatures: tuple[TemperatureReading, ...]
    relays: tuple[RelayState, ...]
    regulated_outputs: tuple[RegulatedOutputState, ...]
    circuits: tuple[HeatingCircuitState, ...]
    active_warning_categories: tuple[str, ...]


def _device_status(raw: dict[str, Any], *, connected_field: str) -> DeviceStatus:
    hardware = raw.get("hardwareVersion")
    firmware = raw.get("softwareVersion")
    return DeviceStatus(
        manufacturer=str(raw.get("manufacturer") or "SELTRON"),
        model=str(raw.get("model") or "unknown"),
        hardware_version=hardware if isinstance(hardware, str) and hardware else None,
        firmware_version=firmware if isinstance(firmware, str) and firmware else None,
        connected=raw.get(connected_field) is True,
    )


def parse_installation_status(
    gateway: dict[str, Any],
    controller: dict[str, Any],
    schema: dict[str, Any] | None = None,
) -> InstallationStatus:
    """Normalize the confirmed GWD3E/WDC20 response without adding controls."""
    warning_fields = {
        "hasActiveBoilerWarnings": "boiler",
        "hasActiveCommunicationWarnings": "communication",
        "hasActiveSensorWarnings": "sensor",
        "hasActiveMessages": "message",
    }
    return InstallationStatus(
        gateway=_device_status(gateway, connected_field="connectionState"),
        controller=_device_status(controller, connected_field="isActive"),
        temperatures=tuple(
            parse_temperature_sensors(controller.get("temperatureSensors", []))
        ),
        relays=tuple(parse_relays(controller.get("relays", []))),
        regulated_outputs=parse_regulated_outputs(
            controller.get("relays", []), schema or {}
        ),
        circuits=tuple(parse_heating_circuits(controller.get("circuits", []))),
        active_warning_categories=tuple(
            category
            for field, category in warning_fields.items()
            if controller.get(field) is True
        ),
    )


def parse_active_warnings(raw: list[dict[str, Any]]) -> list[WarningState]:
    """Return only warnings that the API explicitly marks active."""
    warnings: list[WarningState] = []
    for warning in raw:
        if warning.get("isActive") is not True:
            continue
        warnings.append(
            WarningState(
                code=str(warning.get("code") or "unknown"),
                category=str(warning.get("category") or "unknown"),
            )
        )
    return warnings


def parse_heating_circuits(raw: list[dict[str, Any]]) -> list[HeatingCircuitState]:
    """Parse circuit status and only the capabilities proven by the official client."""

    circuits: list[HeatingCircuitState] = []
    for circuit in raw:
        mode: Any = circuit.get("operationMode", circuit.get("operatingMode"))
        if isinstance(mode, dict):
            mode = mode.get("type")
        if not isinstance(mode, str) or not mode:
            continue
        code = str(circuit.get("code") or "unknown")
        program = circuit.get("activeTimetable", circuit.get("activeProgram"))
        temperatures = circuit.get("temperatures")
        if not isinstance(temperatures, dict):
            temperatures = {}
        setpoints = []
        for key, (minimum, maximum, step) in SETPOINT_SPECS.get(code.upper(), {}).items():
            value = temperatures.get(key)
            if isinstance(value, (int, float)):
                setpoints.append(
                    TemperatureSetpoint(key, float(value), minimum, maximum, step)
                )
        user_function = circuit.get("userFunction")
        if not isinstance(user_function, dict):
            user_function = {}
        function_type = user_function.get("type")
        function_temperature = user_function.get("temperature")
        function_active_until = user_function.get("activeUntil")
        frost_temperature = temperatures.get("off")
        circuits.append(
            HeatingCircuitState(
                code=code,
                name=str(circuit.get("name") or code),
                mode=mode,
                program=program if isinstance(program, str) and program else None,
                supported_modes=OPERATION_MODES.get(code.upper(), ()),
                setpoints=tuple(setpoints),
                user_function=(
                    function_type if isinstance(function_type, str) else "Off"
                ),
                user_function_temperature=(
                    float(function_temperature)
                    if isinstance(function_temperature, (int, float))
                    else None
                ),
                user_function_active_until=(
                    function_active_until
                    if isinstance(function_active_until, str)
                    else None
                ),
                frost_temperature=(
                    float(frost_temperature)
                    if isinstance(frost_temperature, (int, float))
                    else None
                ),
            )
        )
    return circuits


def parse_relays(raw: list[dict[str, Any]]) -> list[RelayState]:
    """Parse relay states without inferring a physical function from the code."""
    relays: list[RelayState] = []
    for relay in raw:
        code = str(relay.get("code") or "unknown")
        state = relay.get("state", relay.get("isActive"))
        if not isinstance(state, bool):
            continue
        relays.append(
            RelayState(
                code=code,
                name=str(relay.get("name") or code),
                is_active=state,
            )
        )
    return relays


def parse_regulated_outputs(
    raw_relays: Any, schema: Any
) -> tuple[RegulatedOutputState, ...]:
    """Map current relay values to source/consumer roles from the official schema."""
    if not isinstance(schema, dict):
        return ()
    relay_states = {item.code: item.is_active for item in parse_relays(raw_relays)}
    known_components: set[tuple[str, str]] = set()
    for section in ("sources", "consumers", "otherComponents"):
        components = schema.get(section)
        if not isinstance(components, list):
            continue
        for component in components:
            if not isinstance(component, dict):
                continue
            code = component.get("code")
            component_id = component.get("id")
            if isinstance(code, str) and isinstance(component_id, str):
                known_components.add((code, component_id))
    outputs = schema.get("outputs")
    if not isinstance(outputs, list):
        return ()
    items: list[RegulatedOutputState] = []
    for output in outputs:
        if not isinstance(output, dict):
            continue
        output_code = output.get("code")
        component_code = output.get("regulatedObject")
        component_id = output.get("regulatedObjectId")
        if (
            isinstance(output_code, str)
            and output_code in relay_states
            and isinstance(component_code, str)
            and isinstance(component_id, str)
            and (component_code, component_id) in known_components
        ):
            items.append(
                RegulatedOutputState(
                    component_code=component_code,
                    component_id=component_id,
                    output_code=output_code,
                    is_active=relay_states[output_code],
                )
            )
    return tuple(items)


def parse_temperature_sensors(raw: list[dict[str, Any]]) -> list[TemperatureReading]:
    """Parse connected temperature values, keeping measured/calculated distinct."""
    readings: list[TemperatureReading] = []
    for sensor in raw:
        value_keys = {
            "measured": ("measured", "measuredTemperature"),
            "calculated": ("calculated", "calculatedTemperature"),
        }
        for kind, keys in value_keys.items():
            value = next((sensor[key] for key in keys if key in sensor), None)
            if not isinstance(value, (int, float)) or float(value) <= -49.9:
                continue
            readings.append(
                TemperatureReading(
                    code=str(sensor.get("code", "unknown")),
                    name=str(sensor.get("name") or sensor.get("code") or "Temperature"),
                    kind=kind,
                    value=float(value),
                )
            )
    return readings
