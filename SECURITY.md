# Security policy

## Supported version

Security fixes are applied to the newest published release.

## Reporting a vulnerability

Please use GitHub's **Report a vulnerability** private security-advisory form for this repository. Do not open a public issue containing credentials, tokens, cloud responses, serial numbers, installation identifiers, Home Assistant diagnostics, or network captures.

Include the affected version, impact, reproduction steps using synthetic/redacted data, and any proposed mitigation. Credentials exposed outside this repository should be revoked or rotated directly with the relevant provider.

## Safety scope

This unofficial integration uses a proprietary cloud API. It intentionally does not implement relay, pump, mixer, boiler, schedule, firmware, or controller-configuration writes. A security report should distinguish integration behavior from controller-side safety mechanisms and cloud-service availability.
