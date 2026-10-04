# SeltronHome Clausius for Home Assistant

[![Tests](https://github.com/subi900/seltron-clausius-home-assistant/actions/workflows/tests.yml/badge.svg)](https://github.com/subi900/seltron-clausius-home-assistant/actions/workflows/tests.yml)
[![HACS validation](https://github.com/subi900/seltron-clausius-home-assistant/actions/workflows/validate.yml/badge.svg)](https://github.com/subi900/seltron-clausius-home-assistant/actions/workflows/validate.yml)

An unofficial Home Assistant custom integration for observing and narrowly controlling a Seltron GWD3/GWD3E gateway and WDC controller through the SeltronHome cloud.

> [!IMPORTANT]
> This community project is not affiliated with or endorsed by Seltron. It depends on a proprietary, publicly undocumented cloud API and can stop working if Seltron changes that service. It is not a local integration and requires working internet, SeltronHome, and Auth0 services.

## Supported entities

- gateway and WDC connectivity
- measured and calculated temperatures; disconnected `-50 °C` sensor values are omitted
- heating-circuit operation mode and active timetable
- neutral read-only relay states
- boiler, communication, sensor, and message warnings
- last successful cloud update
- operation-mode `select` entities for recognized circuits
- temperature-setpoint `number` entities only for values reported by the controller
- Party, Eco, Holiday, and domestic-hot-water single-activation controls only when the controller reports the corresponding user-function capability
- persistent user-selected end-date entities for Party, Eco, and Holiday

Hardware and firmware versions are attached to Home Assistant device-registry entries. Under **Settings → Devices & services → SeltronHome Clausius → Configure**, local options can change the cloud polling interval and channel display labels without changing stable channel codes or unique IDs. Available intervals are 30 seconds and 1, 2, 3, 4, 5, 10, 15, 20, 25, 30, or 60 minutes; the default is 5 minutes.

## Safety boundary

- Routine polling uses HTTP `GET` only.
- Authentication uses `POST` only against the fixed Auth0 token endpoint.
- Writes are limited to recognized WDC operation modes, reported temperature setpoints, and reported normal-user functions.
- Relay, pump, mixer, boiler, schedule, firmware, gateway, and controller-configuration writes are not implemented.
- Every write is caused by an explicit Home Assistant entity action; coordinator updates never write.
- Before writing, the integration validates an allowlisted value, obtains fresh controller data, and checks gateway/controller connectivity and the live capability.
- Polling and writes share a lock. After a write, the controller is reread up to three times over three seconds. Home Assistant publishes success only when the requested state is confirmed.
- Unknown circuits, payload keys, modes, unavailable setpoints, invalid end times, and out-of-range/off-step values are rejected.
- Party uses the current day setpoint, Eco the night setpoint, and Holiday the frost-protection setpoint. Their end time must be explicitly selected, timezone-aware, in the future, and at most 366 days away.

This software cannot make a cloud-controlled heating system inherently safe. Keep all controller-side limits, frost protection, boiler safeties, and physical controls operational.

## Installation with HACS

1. Create and verify a current Home Assistant backup.
2. In HACS, open **Integrations**, choose **Custom repositories**, and add:
   `https://github.com/subi900/seltron-clausius-home-assistant`
   with category **Integration**.
3. Install **SeltronHome Clausius**.
4. Restart Home Assistant when you are ready.
5. Open **Settings → Devices & services → Add integration**, search for **SeltronHome Clausius**, and enter your SeltronHome account credentials.

The Config Entry stores the email address and password locally alongside access/refresh tokens and their expiry. The integration first renews access via the refresh token; only a rejected refresh token triggers automatic sign-in with the saved credentials. Concurrent polling and controls share the same authentication lock. A rejected access token causes at most one renewal and retry of the read; control writes are never automatically replayed.

Existing token-only installations continue working. To enable automatic sign-in without removing the integration, open **Settings → Devices & services → SeltronHome Clausius → entry menu (⋮) → Reconfigure** and enter the original account credentials once. Alternatively, the next required reauthentication saves them. Entity IDs and polling/label options are retained. Saved passwords are never prefilled into forms.

Temporary network, rate-limit and server errors do not request reauthentication; Home Assistant retries polling normally. Automatic password attempts after a temporary login failure are spaced at least five minutes apart per loaded integration. Incorrect/revoked credentials or repeated rejection of newly issued access tokens still require user intervention. These limits avoid endless login loops; cloud outages can still make entities temporarily unavailable.

**Security:** credentials are not separately encrypted by this integration. Anyone with access to Home Assistant configuration storage or a readable backup may obtain them. Protect configuration access and encrypt/restrict backups. Diagnostics redact both email and password. Never publish `.storage` files or backups.

### Manual installation

Copy `custom_components/seltron_clausius` into `/config/custom_components/`, restart Home Assistant, and add the integration from **Settings → Devices & services**.

## Privacy and diagnostics

The integration sends requests only to the fixed SeltronHome API and Auth0 endpoints. Diagnostics redact tokens, account details, local labels, and installation/device identifiers. Do not publish raw cloud responses, HAR files, serial numbers, Home Assistant backups, `.storage` data, or files from `diagnostics-private/`.

## Development

```bash
uv sync --frozen --extra test
uv run pytest -q
uvx ruff check custom_components tests
uv run python -m compileall -q custom_components tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).
