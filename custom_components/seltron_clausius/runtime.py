from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from .api import Installation, SeltronApi, TokenSet, async_refresh_tokens
from .controls import validate_operation_mode, validate_setpoint, validate_user_function
from .models import HeatingCircuitState, InstallationStatus, parse_installation_status


class _Api(Protocol):
    async def async_discover_installations(self) -> list[Installation]: ...
    async def async_refresh_installation(self, installation: Installation) -> Installation: ...
    async def async_set_operation_mode(
        self, installation: Installation, circuit_code: str, mode: str
    ) -> None: ...
    async def async_set_temperatures(
        self, installation: Installation, circuit_code: str, temperatures: dict[str, float]
    ) -> None: ...
    async def async_set_user_function(
        self,
        installation: Installation,
        circuit_code: str,
        user_function: dict[str, Any],
    ) -> None: ...


@dataclass(frozen=True)
class RuntimeData:
    status: InstallationStatus
    last_successful_update: datetime


class WriteVerificationError(RuntimeError):
    """The controller reread did not confirm a requested command."""


class WriteUnavailableError(RuntimeError):
    """The live gateway/controller state does not permit a safe write."""


class SeltronRuntime:
    """Own token rotation, serialized polling, and narrowly verified controls."""

    def __init__(
        self,
        session: Any,
        tokens: TokenSet,
        *,
        persist_tokens: Callable[[TokenSet], Awaitable[None]],
        refresh_tokens: Callable[[Any, str], Awaitable[TokenSet]] = async_refresh_tokens,
        api_factory: Callable[..., _Api] = SeltronApi,
        now: Callable[[], float] = time.time,
        confirmation_delays: tuple[float, ...] = (0.0, 1.0, 2.0),
    ) -> None:
        self._session = session
        self._tokens = tokens
        self._persist_tokens = persist_tokens
        self._refresh_tokens = refresh_tokens
        self._api_factory = api_factory
        self._now = now
        if not confirmation_delays:
            raise ValueError("At least one write-confirmation attempt is required")
        self._confirmation_delays = confirmation_delays
        self._installation: Installation | None = None
        self._lock = asyncio.Lock()

    async def _async_api(self) -> _Api:
        if self._tokens.expires_at <= self._now() + 60:
            rotated = await self._refresh_tokens(
                self._session, self._tokens.refresh_token
            )
            await self._persist_tokens(rotated)
            self._tokens = rotated
        return self._api_factory(
            self._session, access_token=self._tokens.access_token
        )

    async def _async_refresh_installation(self, api: _Api) -> RuntimeData:
        if self._installation is None:
            installations = await api.async_discover_installations()
            if not installations:
                raise RuntimeError("No compatible Seltron installation found")
            self._installation = installations[0]
        else:
            self._installation = await api.async_refresh_installation(
                self._installation
            )
        return self._runtime_data()

    def _runtime_data(self) -> RuntimeData:
        if self._installation is None:
            raise RuntimeError("No compatible Seltron installation loaded")
        return RuntimeData(
            status=parse_installation_status(
                self._installation.gateway,
                self._installation.controller,
                self._installation.schema,
            ),
            last_successful_update=datetime.now(UTC),
        )

    @staticmethod
    def _circuit(data: RuntimeData, circuit_code: str) -> HeatingCircuitState:
        circuit = next(
            (
                item
                for item in data.status.circuits
                if item.code.upper() == circuit_code.upper()
            ),
            None,
        )
        if circuit is None:
            raise ValueError(f"Unknown heating circuit {circuit_code}")
        return circuit

    @staticmethod
    def _ensure_write_available(data: RuntimeData) -> None:
        if not data.status.gateway.connected:
            raise WriteUnavailableError("Seltron gateway is not connected")
        if not data.status.controller.connected:
            raise WriteUnavailableError("Seltron controller is not connected")

    async def async_update(self) -> RuntimeData:
        """Refresh tokens if needed and poll the known installation."""
        async with self._lock:
            api = await self._async_api()
            return await self._async_refresh_installation(api)

    async def async_set_operation_mode(
        self, circuit_code: str, mode: str
    ) -> RuntimeData:
        """Validate, write, reread, and verify a confirmed circuit mode."""
        async with self._lock:
            requested = validate_operation_mode(circuit_code, mode)
            api = await self._async_api()
            current_data = await self._async_refresh_installation(api)
            self._ensure_write_available(current_data)
            circuit = self._circuit(current_data, circuit_code)
            if circuit.mode == requested:
                return current_data
            assert self._installation is not None
            await api.async_set_operation_mode(
                self._installation, circuit.code, requested
            )
            for delay in self._confirmation_delays:
                if delay > 0:
                    await asyncio.sleep(delay)
                reread = await self._async_refresh_installation(api)
                if self._circuit(reread, circuit.code).mode == requested:
                    return reread
            raise WriteVerificationError(
                f"Operation mode readback for {circuit.code} did not match"
            )

    async def async_set_setpoint(
        self, circuit_code: str, key: str, value: float
    ) -> RuntimeData:
        """Validate, write only one key, reread, and verify a confirmed setpoint."""
        async with self._lock:
            requested = validate_setpoint(circuit_code, key, value)
            api = await self._async_api()
            current_data = await self._async_refresh_installation(api)
            self._ensure_write_available(current_data)
            circuit = self._circuit(current_data, circuit_code)
            current = next((item for item in circuit.setpoints if item.key == key), None)
            if current is None:
                raise ValueError(
                    f"Setpoint {key} is not present on heating circuit {circuit.code}"
                )
            if current.value == requested:
                return current_data
            assert self._installation is not None
            await api.async_set_temperatures(
                self._installation, circuit.code, {key: requested}
            )
            for delay in self._confirmation_delays:
                if delay > 0:
                    await asyncio.sleep(delay)
                reread = await self._async_refresh_installation(api)
                confirmed = next(
                    (
                        item
                        for item in self._circuit(reread, circuit.code).setpoints
                        if item.key == key
                    ),
                    None,
                )
                if confirmed is not None and confirmed.value == requested:
                    return reread
            raise WriteVerificationError(
                f"Setpoint readback for {circuit.code}/{key} did not match"
            )

    async def async_set_user_function(
        self,
        circuit_code: str,
        function: str,
        *,
        active_until: datetime | None = None,
    ) -> RuntimeData:
        """Write and verify one allowlisted Clausius normal-user function."""
        async with self._lock:
            requested = validate_user_function(circuit_code, function)
            api = await self._async_api()
            current_data = await self._async_refresh_installation(api)
            self._ensure_write_available(current_data)
            circuit = self._circuit(current_data, circuit_code)
            if requested not in circuit.supported_user_functions:
                raise ValueError(
                    f"User function {requested} is not reported for {circuit.code}"
                )
            if circuit.user_function == requested:
                return current_data
            payload: dict[str, Any] = {
                "type": requested,
                "activeTimetable": circuit.program,
            }
            if requested in {"Party", "Eco", "Holiday"}:
                temperatures = {item.key: item.value for item in circuit.setpoints}
                target = {
                    "Party": temperatures.get("day"),
                    "Eco": temperatures.get("night"),
                    "Holiday": circuit.frost_temperature,
                }[requested]
                if target is None:
                    raise ValueError(f"No target temperature available for {requested}")
                assert self._installation is not None
                raw_clock = self._installation.controller.get("clock", {})
                raw_date_time = (
                    raw_clock.get("dateTime") if isinstance(raw_clock, dict) else None
                )
                if not isinstance(raw_date_time, str):
                    raise ValueError("Controller clock is unavailable")
                controller_now = datetime.fromisoformat(raw_date_time)
                if active_until is None or active_until.tzinfo is not None:
                    raise ValueError("A local end date and time is required")
                if active_until <= controller_now:
                    raise ValueError("The end date and time must be in the future")
                if active_until > controller_now + timedelta(days=366):
                    raise ValueError("The end date and time cannot exceed 366 days")
                payload.update(
                    {
                        "temperature": target,
                        "activeUntil": active_until.isoformat(timespec="seconds"),
                    }
                )
            assert self._installation is not None
            await api.async_set_user_function(
                self._installation, circuit.code, payload
            )
            for delay in self._confirmation_delays:
                if delay > 0:
                    await asyncio.sleep(delay)
                reread = await self._async_refresh_installation(api)
                confirmed = self._circuit(reread, circuit.code)
                if confirmed.user_function != requested:
                    continue
                if requested in {"Party", "Eco", "Holiday"} and (
                    confirmed.user_function_temperature != payload["temperature"]
                    or confirmed.user_function_active_until != payload["activeUntil"]
                ):
                    continue
                return reread
            raise WriteVerificationError(
                f"User-function readback for {circuit.code} did not match"
            )
