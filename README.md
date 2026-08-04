# SeltronHome Clausius for Home Assistant

A local custom integration for observing and safely controlling a Seltron GWD3/GWD3E gateway and WDC20 controller through the SeltronHome cloud. Version 0.2.1 corrects writable requests to match the official Clausius client: operation modes use a JSON body and all control requests carry a correlation ID. Resulting state is read back before Home Assistant publishes it.

## Safety boundary

- Normal status polling remains HTTP `GET` only.
- HTTP `POST` is used only against the fixed Auth0 token endpoint for login and token refresh.
- Writes are limited to confirmed WDC heating-circuit operation modes and temperature setpoints.
- Supported operation modes are `Timer`, `Day`, `Night`, `Off` for `HC1`/`HC2`, and `Timer`, `On`, `Off` for `DHWC`.
- Setpoint limits are day 8–30 °C, night 4–40 °C, and domestic hot water 20–80 °C, all in 0.5 °C increments.
- Every command serializes writes, performs up to three bounded controller refreshes over three seconds, and verifies the returned value. A mismatch is reported as a failed command; no optimistic state is published.
- Unknown circuits, modes, setpoint keys and out-of-range or off-step values are rejected before network access.
- There are no relay, schedule, gateway/controller configuration, diagnostic or firmware controls. Relays remain observed binary sensors only.

## Entities

- GWD3/GWD3E and WDC20 connectivity
- measured and calculated temperatures (`-50 °C` disconnected values are omitted)
- heating-circuit operation modes and active timetables
- neutral relay states
- boiler, communication, sensor and message warnings
- last successful cloud update
- operation-mode `select` entities only for confirmed circuit types
- setpoint `number` entities only for confirmed keys and limits

Hardware and firmware versions are attached to Home Assistant device-registry entries.

## Local channel labels

The integration options expose discovered temperature, relay and circuit channels. Optional labels change only the displayed entity names. Channel codes and unique IDs remain stable. Label changes reload the integration; Home Assistant entity-registry custom names remain under Home Assistant's control.

## Polling and credentials

After initial discovery, each five-minute update performs exactly two direct Seltron API `GET` requests: one for the known gateway and one for the known WDC20. The config flow uses the password only for the immediate Auth0 exchange and stores only access/refresh tokens and expiry. Rotated refresh tokens are persisted together in one Config Entry update.

## Installation (only after a current Home Assistant backup)

1. Create and verify a current full Home Assistant backup.
2. Copy `custom_components/seltron_clausius` into Home Assistant's `/config/custom_components/` directory.
3. Restart Home Assistant only with explicit approval.
4. Add **SeltronHome Clausius** under **Settings → Devices & services → Add integration**.
5. Enter SeltronHome email and password in the local Home Assistant config flow.

Do not commit or share credentials, tokens, raw account responses, HAR files, serial numbers or private account/device identifiers. Never package `diagnostics-private/`.

## Local verification

```bash
uv venv --python 3.11
uv pip install --python .venv/Scripts/python.exe -e '.[test]'
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m compileall -q custom_components tests
```
