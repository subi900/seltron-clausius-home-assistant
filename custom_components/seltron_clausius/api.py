from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, urlencode
from uuid import uuid4

import aiohttp

from .controls import (
    validate_operation_mode,
    validate_setpoint,
    validate_user_function_payload,
)

API_BASE_URL = "https://api.seltronhome.com"
AUTH0_TOKEN_URL = "https://seltronhome.eu.auth0.com/oauth/token"
AUTH0_CLIENT_ID = "lbO893m2FNTundKaTrRM00jTw5LTLMz2"
AUTH0_AUDIENCE = "https://api.seltronhome.com"
AUTH0_REALM = "Username-Password-Authentication"
AUTH0_SCOPE = "openid profile email offline_access"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)


@dataclass(frozen=True)
class TokenSet:
    """Auth tokens whose representation can never disclose their values."""

    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    expires_at: float


async def async_password_login(
    session: aiohttp.ClientSession, email: str, password: str
) -> TokenSet:
    """Exchange locally supplied credentials for tokens without retaining the password."""
    payload = {
        "grant_type": "http://auth0.com/oauth/grant-type/password-realm",
        "client_id": AUTH0_CLIENT_ID,
        "audience": AUTH0_AUDIENCE,
        "realm": AUTH0_REALM,
        "scope": AUTH0_SCOPE,
        "username": email,
        "password": password,
    }
    async with session.post(
        AUTH0_TOKEN_URL, data=payload, timeout=REQUEST_TIMEOUT
    ) as response:
        if response.status != 200:
            raise AuthenticationError(f"Auth0 authentication failed (HTTP {response.status})")
        data = await response.json()
    return TokenSet(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_at=time.time() + int(data["expires_in"]),
    )


class AuthenticationError(Exception):
    """Authentication failed without exposing response content or credentials."""


async def async_refresh_tokens(
    session: aiohttp.ClientSession, refresh_token: str
) -> TokenSet:
    """Refresh tokens and retain an Auth0-rotated refresh token."""
    payload = {
        "grant_type": "refresh_token",
        "client_id": AUTH0_CLIENT_ID,
        "refresh_token": refresh_token,
    }
    async with session.post(
        AUTH0_TOKEN_URL, data=payload, timeout=REQUEST_TIMEOUT
    ) as response:
        if response.status != 200:
            raise AuthenticationError(f"Auth0 token refresh failed (HTTP {response.status})")
        data = await response.json()
    return TokenSet(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token", refresh_token),
        expires_at=time.time() + int(data["expires_in"]),
    )


class UnsafePathError(ValueError):
    """Raised when a data request could escape the fixed read-only API scope."""


@dataclass(frozen=True)
class Installation:
    """Discovered GWD3/WDC installation; private identifiers never appear in repr."""

    subscription_id: str = field(repr=False)
    resource_group_id: str = field(repr=False)
    gateway_id: str = field(repr=False)
    controller_id: str = field(repr=False)
    gateway: dict[str, Any] = field(repr=False)
    controller: dict[str, Any] = field(repr=False)
    schema: dict[str, Any] = field(default_factory=dict, repr=False)


def _collection(value: Any, key: str | None = None) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        if key:
            for candidate, item in value.items():
                if candidate.lower() == key.lower() and isinstance(item, list):
                    return [entry for entry in item if isinstance(entry, dict)]
        for candidate in ("value", "items"):
            item = value.get(candidate)
            if isinstance(item, list):
                return [entry for entry in item if isinstance(entry, dict)]
    return []


def _field(value: dict[str, Any], name: str) -> Any:
    return next((item for key, item in value.items() if key.lower() == name.lower()), None)


def _id(value: dict[str, Any]) -> str:
    identifier = _field(value, "id")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("Seltron response item has no usable identifier")
    return identifier


class SeltronApi:
    """Narrow client for SeltronHome status and proven normal-user controls."""

    def __init__(self, session: aiohttp.ClientSession, *, access_token: str) -> None:
        self._session = session
        self._access_token = access_token

    @staticmethod
    def _raise_for_status(response: aiohttp.ClientResponse) -> None:
        """Map rejected credentials to Home Assistant reauthentication."""
        if response.status in {401, 403}:
            raise AuthenticationError("Seltron access token was rejected")
        response.raise_for_status()

    async def async_get(self, path: str) -> Any:
        """Fetch JSON data using the only supported Seltron data verb: GET."""
        if not path.startswith("/api/") or path.startswith("//") or "://" in path:
            raise UnsafePathError("Seltron data paths must start with /api/")
        headers = {"Authorization": f"Bearer {self._access_token}"}
        async with self._session.get(
            f"{API_BASE_URL}{path}", headers=headers, timeout=REQUEST_TIMEOUT
        ) as response:
            self._raise_for_status(response)
            return await response.json()

    def _heating_circuit_root(self, installation: Installation, circuit_code: str) -> str:
        sid = quote(installation.subscription_id, safe="")
        rgid = quote(installation.resource_group_id, safe="")
        cid = quote(installation.controller_id, safe="")
        circuit = quote(circuit_code, safe="")
        return f"/api/subscriptions/{sid}/resourceGroups/{rgid}/WDC/{cid}/{circuit}"

    async def async_set_operation_mode(
        self,
        installation: Installation,
        circuit_code: str,
        mode: str,
    ) -> None:
        """Set one proven heating-circuit mode using the official-client contract."""
        validate_operation_mode(circuit_code, mode)
        path = f"{self._heating_circuit_root(installation, circuit_code)}/operationMode"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "correlationId": str(uuid4()),
        }
        async with self._session.put(
            f"{API_BASE_URL}{path}",
            json={"type": mode},
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        ) as response:
            self._raise_for_status(response)

    async def async_set_temperatures(
        self,
        installation: Installation,
        circuit_code: str,
        temperatures: dict[str, float],
    ) -> None:
        """Set exactly one confirmed and locally validated circuit temperature."""
        if len(temperatures) != 1:
            raise ValueError("Exactly one temperature setpoint is required")
        key, value = next(iter(temperatures.items()))
        validated_value = validate_setpoint(circuit_code, key, value)
        temperatures = {key: validated_value}
        path = f"{self._heating_circuit_root(installation, circuit_code)}/temperatures"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "correlationId": str(uuid4()),
        }
        async with self._session.put(
            f"{API_BASE_URL}{path}",
            json=temperatures,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        ) as response:
            self._raise_for_status(response)

    async def async_set_user_function(
        self,
        installation: Installation,
        circuit_code: str,
        user_function: dict[str, Any],
    ) -> None:
        """Set one allowlisted Clausius user function using the official contract."""
        payload = validate_user_function_payload(circuit_code, user_function)
        path = f"{self._heating_circuit_root(installation, circuit_code)}/userFunction"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "correlationId": str(uuid4()),
        }
        async with self._session.put(
            f"{API_BASE_URL}{path}",
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        ) as response:
            self._raise_for_status(response)

    async def async_discover_installations(self) -> list[Installation]:
        """Discover GWD3 gateways and WDC controllers using GET requests only."""
        subscriptions = _collection(
            await self.async_get("/api/subscriptions?$expand=Tags")
        )
        installations: list[Installation] = []
        for subscription in subscriptions:
            subscription_id = _id(subscription)
            sid = quote(subscription_id, safe="")
            subscription_detail = await self.async_get(f"/api/subscriptions/{sid}")
            for group_stub in _collection(subscription_detail, "resourceGroups"):
                resource_group_id = _id(group_stub)
                rgid = quote(resource_group_id, safe="")
                root = f"/api/subscriptions/{sid}/resourceGroups/{rgid}"
                group = await self.async_get(f"{root}?$expand=Tags")
                resources = _collection(group, "resources")
                for resource in resources:
                    resource_type = str(
                        _field(resource, "type")
                        or _field(resource, "code")
                        or _field(resource, "model")
                        or ""
                    ).upper()
                    if "GWD3" not in resource_type:
                        continue
                    gateway_id = _id(resource)
                    gid = quote(gateway_id, safe="")
                    gateway = await self.async_get(f"{root}/GWD3/{gid}?$expand=Tags")
                    controllers = _collection(gateway, "connectedControllers")
                    for controller_stub in controllers:
                        controller_type = str(
                            _field(controller_stub, "type")
                            or _field(controller_stub, "code")
                            or _field(controller_stub, "model")
                            or ""
                        ).upper()
                        if "WDC" not in controller_type:
                            continue
                        controller_id = _id(controller_stub)
                        cid = quote(controller_id, safe="")
                        controller = await self.async_get(
                            f"{root}/WDC/{cid}?$expand=Tags"
                        )
                        schema = await self._async_load_controller_schema(controller)
                        installations.append(
                            Installation(
                                subscription_id=subscription_id,
                                resource_group_id=resource_group_id,
                                gateway_id=gateway_id,
                                controller_id=controller_id,
                                gateway=gateway,
                                controller=controller,
                                schema=schema,
                            )
                        )
        return installations

    async def _async_load_controller_schema(
        self, controller: dict[str, Any]
    ) -> dict[str, Any]:
        """Load the official schematic used by Clausius to label live outputs."""
        manufacturer = _field(controller, "manufacturer")
        model = _field(controller, "model") or _field(controller, "code")
        version = _field(controller, "softwareVersion")
        schema_code = _field(controller, "schemaCode")
        if not all(isinstance(item, str) and item for item in (manufacturer, model, version)):
            return {}
        if schema_code is None:
            return {}
        query = urlencode(
            {"manufacturer": manufacturer, "model": model, "version": version}
        )
        specifications = _collection(await self.async_get(f"/api/specifications/?{query}"))
        if not specifications:
            return {}
        specification_id = quote(_id(specifications[0]), safe="")
        schema = await self.async_get(
            f"/api/specifications/{specification_id}/schemas/{quote(str(schema_code), safe='')}"
        )
        return schema if isinstance(schema, dict) else {}

    async def async_refresh_installation(self, installation: Installation) -> Installation:
        """Refresh one known installation with exactly two read-only requests."""
        sid = quote(installation.subscription_id, safe="")
        rgid = quote(installation.resource_group_id, safe="")
        gid = quote(installation.gateway_id, safe="")
        cid = quote(installation.controller_id, safe="")
        root = f"/api/subscriptions/{sid}/resourceGroups/{rgid}"
        gateway = await self.async_get(f"{root}/GWD3/{gid}?$expand=Tags")
        controller = await self.async_get(f"{root}/WDC/{cid}?$expand=Tags")
        return Installation(
            subscription_id=installation.subscription_id,
            resource_group_id=installation.resource_group_id,
            gateway_id=installation.gateway_id,
            controller_id=installation.controller_id,
            gateway=gateway,
            controller=controller,
            schema=installation.schema,
        )
