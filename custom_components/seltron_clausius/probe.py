from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from getpass import getpass
from pathlib import Path
from typing import Any

import aiohttp

from .api import Installation, SeltronApi, async_password_login
from .diagnostics import redact_payload


def build_probe_report(installations: list[Installation]) -> dict[str, Any]:
    """Build a redacted structural report suitable for local fixture review."""
    return {
        "captured_at": datetime.now(UTC).isoformat(),
        "installations": [
            {
                "gateway": redact_payload(installation.gateway),
                "controller": redact_payload(installation.controller),
            }
            for installation in installations
        ],
    }


async def async_run_probe(output_path: Path) -> int:
    """Run a one-shot read-only probe with hidden local credential entry."""
    email = getpass("SeltronHome email (hidden): ")
    password = getpass("SeltronHome password (hidden): ")
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tokens = await async_password_login(session, email, password)
        del email, password
        api = SeltronApi(session, access_token=tokens.access_token)
        await api.async_get("/api/accounts/me")
        installations = await api.async_discover_installations()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(build_probe_report(installations), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return len(installations)


def main() -> None:
    """Console entry point; never prints credentials, tokens, IDs, or raw responses."""
    output = Path("diagnostics-private") / "probe-redacted.json"
    try:
        count = asyncio.run(async_run_probe(output))
    except Exception as err:  # noqa: BLE001 - CLI must fail closed without leaking payloads
        print(f"Probe failed safely: {type(err).__name__}")
        raise SystemExit(1) from None
    print(f"Read-only probe succeeded: {count} installation(s); redacted report saved locally.")


if __name__ == "__main__":
    main()
