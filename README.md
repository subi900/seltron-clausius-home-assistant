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

Hardware and firmware versions are attached to Home Assistant device-registry entries. Local options can change channel display labels without changing stable channel codes or unique IDs.

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

The password is used only for the immediate Auth0 exchange. The Config Entry stores access/refresh tokens and their expiry, not the email address or password. Reauthentication requires the same account.

### Manual installation

Copy `custom_components/seltron_clausius` into `/config/custom_components/`, restart Home Assistant, and add the integration from **Settings → Devices & services**.

## Privacy and diagnostics

The integration sends requests only to the fixed SeltronHome API and Auth0 endpoints. Diagnostics redact tokens, account details, local labels, and installation/device identifiers. Do not publish raw cloud responses, HAR files, serial numbers, Home Assistant backups, `.storage` data, or files from `diagnostics-private/`.

## Development

```bash
uv sync --extra test
uv run pytest -q
uvx ruff check custom_components tests
python -m compileall -q custom_components tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).
