"""Authentication recovery uses synthetic credentials and never contacts the cloud."""
import asyncio
from unittest.mock import AsyncMock

import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.seltron_clausius.api import (
    AUTH0_TOKEN_URL,
    AuthenticationError,
    Installation,
    SeltronApi,
    TokenSet,
    async_password_login,
    async_refresh_tokens,
)
from custom_components.seltron_clausius.runtime import SeltronRuntime


@pytest.mark.parametrize("status", [429, 500, 502, 503, 403])
@pytest.mark.parametrize("login", [False, True])
async def test_service_errors_are_not_reauthentication(status, login):
    async with aiohttp.ClientSession() as session:
        with aioresponses() as mocked:
            mocked.post(AUTH0_TOKEN_URL, status=status, payload={"error": "server_error"})
            with pytest.raises(RuntimeError):
                if login:
                    await async_password_login(session, "synthetic@example.invalid", "dummy")
                else:
                    await async_refresh_tokens(session, "dummy-refresh")


async def test_invalid_grant_is_genuine_rejection():
    async with aiohttp.ClientSession() as session:
        with aioresponses() as mocked:
            mocked.post(AUTH0_TOKEN_URL, status=400, payload={"error": "invalid_grant"})
            with pytest.raises(AuthenticationError):
                await async_refresh_tokens(session, "dummy-refresh")


@pytest.mark.parametrize("payload", [{}, [], {"access_token": "a", "expires_in": "bad"}])
async def test_malformed_token_response_is_service_failure(payload):
    async with aiohttp.ClientSession() as session:
        with aioresponses() as mocked:
            mocked.post(AUTH0_TOKEN_URL, payload=payload)
            with pytest.raises(RuntimeError):
                await async_refresh_tokens(session, "dummy-refresh")


async def test_forbidden_data_is_not_expired_authentication():
    async with aiohttp.ClientSession() as session:
        with aioresponses() as mocked:
            mocked.get("https://api.seltronhome.com/api/accounts/me", status=403)
            with pytest.raises(RuntimeError):
                await SeltronApi(session, access_token="dummy").async_get("/api/accounts/me")


def recovery_runtime(*, expired=True, refresh_error=None, read_failures=0, saved=True):
    installation = Installation("s", "g", "gw", "c", {}, {})
    api = AsyncMock()
    api.async_discover_installations.side_effect = [
        *[AuthenticationError("rejected") for _ in range(read_failures)],
        [installation],
    ]
    api.async_refresh_installation.return_value = installation
    refresh = AsyncMock(return_value=TokenSet("fresh", "rotated", 10000))
    if refresh_error:
        refresh.side_effect = refresh_error
    login = AsyncMock(return_value=TokenSet("login", "login-refresh", 10000))
    persist = AsyncMock()
    runtime = SeltronRuntime(
        object(), TokenSet("old", "old-refresh", 0 if expired else 10000),
        persist_tokens=persist, refresh_tokens=refresh,
        password_login=login,
        credentials=("synthetic@example.invalid", "dummy") if saved else None,
        api_factory=lambda *args, **kwargs: api, now=lambda: 1000,
    )
    return runtime, refresh, login, persist, api


async def test_invalid_refresh_automatically_logs_in_and_persists_once_concurrently():
    runtime, refresh, login, persist, _ = recovery_runtime(
        refresh_error=AuthenticationError("invalid grant")
    )
    await asyncio.gather(runtime.async_update(), runtime.async_update())
    assert refresh.await_count == login.await_count == persist.await_count == 1
    assert persist.call_args.args[0].refresh_token == "login-refresh"


@pytest.mark.parametrize("error", [RuntimeError("service"), TimeoutError(), aiohttp.ClientError()])
async def test_transient_refresh_does_not_use_saved_password(error):
    runtime, _, login, persist, _ = recovery_runtime(refresh_error=error)
    with pytest.raises(type(error)):
        await runtime.async_update()
    login.assert_not_awaited()
    persist.assert_not_awaited()


async def test_legacy_entry_rejected_refresh_requires_reauth():
    runtime, _, login, _, _ = recovery_runtime(
        saved=False, refresh_error=AuthenticationError("invalid grant")
    )
    with pytest.raises(AuthenticationError):
        await runtime.async_update()
    login.assert_not_awaited()


async def test_early_access_rejection_refreshes_and_retries_read_once():
    runtime, refresh, login, _, api = recovery_runtime(expired=False, read_failures=1)
    await runtime.async_update()
    refresh.assert_awaited_once()
    login.assert_not_awaited()
    assert api.async_discover_installations.await_count == 2


async def test_repeated_read_rejection_is_bounded():
    runtime, refresh, login, _, api = recovery_runtime(expired=False, read_failures=2)
    with pytest.raises(AuthenticationError):
        await runtime.async_update()
    refresh.assert_awaited_once()
    login.assert_not_awaited()
    assert api.async_discover_installations.await_count == 2


async def test_rejected_password_not_retried_on_every_operation():
    runtime, _, login, _, _ = recovery_runtime(refresh_error=AuthenticationError("invalid grant"))
    login.side_effect = AuthenticationError("invalid password")
    for _ in range(2):
        with pytest.raises(AuthenticationError):
            await runtime.async_update()
    login.assert_awaited_once()


async def test_transient_password_failure_is_rate_limited_then_recovers():
    runtime, _, login, persist, _ = recovery_runtime(refresh_error=AuthenticationError("invalid grant"))
    login.side_effect = [RuntimeError("outage"), TokenSet("login", "rotated", 10000)]
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await runtime.async_update()
    assert login.await_count == 1
    runtime._now = lambda: 1301
    await runtime.async_update()
    assert login.await_count == 2
    persist.assert_awaited_once()


async def test_malformed_error_payload_is_a_service_failure():
    async with aiohttp.ClientSession() as session:
        with aioresponses() as mocked:
            mocked.post(AUTH0_TOKEN_URL, status=400, payload={"error": ["unexpected"]})
            with pytest.raises(RuntimeError):
                await async_refresh_tokens(session, "dummy")
