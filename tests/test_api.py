from __future__ import annotations

from typing import Any, Self

import pytest

from custom_components.seltron_clausius.api import SeltronApi, UnsafePathError


class FakeResponse:
    status = 200

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    async def json(self) -> dict[str, str]:
        return {"name": "private"}


class RecordingSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append(("GET", url, kwargs))
        return FakeResponse()


@pytest.mark.asyncio
async def test_api_data_request_uses_get_only() -> None:
    session = RecordingSession()
    api = SeltronApi(session, access_token="secret-access")  # type: ignore[arg-type]

    result = await api.async_get("/api/accounts/me")

    assert result == {"name": "private"}
    assert [(method, url) for method, url, _ in session.calls] == [
        ("GET", "https://api.seltronhome.com/api/accounts/me")
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["https://evil.example/x", "//evil.example/x", "/oauth/token"])
async def test_data_request_rejects_paths_outside_seltron_api(path: str) -> None:
    session = RecordingSession()
    api = SeltronApi(session, access_token="secret-access")  # type: ignore[arg-type]

    with pytest.raises(UnsafePathError):
        await api.async_get(path)

    assert session.calls == []
