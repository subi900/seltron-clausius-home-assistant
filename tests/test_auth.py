from __future__ import annotations

from typing import Any, Self

import pytest

from custom_components.seltron_clausius.api import (
    AUTH0_TOKEN_URL,
    TokenSet,
    async_password_login,
    async_refresh_tokens,
)


class AuthResponse:
    status = 200

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def json(self) -> dict[str, Any]:
        return {
            "access_token": "dummy-access-value",
            "refresh_token": "dummy-refresh-value",
            "expires_in": 3600,
        }


class AuthSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def post(self, url: str, **kwargs: Any) -> AuthResponse:
        self.calls.append((url, kwargs))
        return AuthResponse()


@pytest.mark.asyncio
async def test_password_login_uses_auth0_and_token_repr_is_redacted() -> None:
    session = AuthSession()

    tokens = await async_password_login(
        session, "user@example.invalid", "dummy-password"  # type: ignore[arg-type]
    )

    assert isinstance(tokens, TokenSet)
    assert tokens.access_token == "dummy-access-value"
    assert tokens.refresh_token == "dummy-refresh-value"
    assert session.calls[0][0] == AUTH0_TOKEN_URL
    payload = session.calls[0][1]["data"]
    assert payload["grant_type"] == "http://auth0.com/oauth/grant-type/password-realm"
    assert payload["realm"] == "Username-Password-Authentication"
    assert "dummy-access-value" not in repr(tokens)
    assert "dummy-refresh-value" not in repr(tokens)


class RotationResponse(AuthResponse):
    async def json(self) -> dict[str, Any]:
        return {
            "access_token": "rotated-access-value",
            "refresh_token": "rotated-refresh-value",
            "expires_in": 7200,
        }


class RotationSession(AuthSession):
    def post(self, url: str, **kwargs: Any) -> RotationResponse:
        self.calls.append((url, kwargs))
        return RotationResponse()


@pytest.mark.asyncio
async def test_refresh_uses_rotated_refresh_token() -> None:
    session = RotationSession()

    tokens = await async_refresh_tokens(
        session, "old-refresh-value"  # type: ignore[arg-type]
    )

    assert tokens.refresh_token == "rotated-refresh-value"
    payload = session.calls[0][1]["data"]
    assert payload == {
        "grant_type": "refresh_token",
        "client_id": "lbO893m2FNTundKaTrRM00jTw5LTLMz2",
        "refresh_token": "old-refresh-value",
    }
