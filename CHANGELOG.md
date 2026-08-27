# Changelog

All notable user-visible changes are documented here.

## [0.4.2] - 2026-08-27

### Added

- A Home Assistant integration option for selecting the cloud polling interval: 30 seconds; 1, 2, 3, 4, 5, 10, 15, 20, 25, 30, or 60 minutes.

### Changed

- Existing installations continue to use a five-minute polling interval by default. Saving the option reloads the integration so the selected interval takes effect immediately.

## [0.4.1] - 2026-08-05

### Added

- Home Assistant reauthentication and local channel-label options.
- Diagnostics with redaction of credentials and private installation identifiers.
- Party, Eco, Holiday, and domestic-hot-water single-activation entities when reported by the controller.
- Explicit persistent end-date controls for timed heating functions.
- English and German config-flow translations.

### Changed

- A fresh controller snapshot and connectivity/capability check now precedes every write.
- All writes require confirmed controller readback; cloud requests have a bounded timeout.
- Rejected cloud access tokens trigger Home Assistant reauthentication.
- Capability detection no longer exposes controls from circuit names alone.

### Security

- Relays, pumps, mixers, boilers, firmware, schedules, and controller configuration remain read-only.
- Diagnostics and repository secret scanning were hardened.

## [0.4.0]

- Initial internal integration baseline with cloud polling, controller status, recognized operation modes, setpoints, warnings, and verified write readback.
