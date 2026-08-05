# Contributing

Contributions are welcome, especially redacted fixtures for additional Seltron controller variants.

1. Do not commit credentials, tokens, emails, serial numbers, installation IDs, raw diagnostics, HAR files, Home Assistant backups, or proprietary application bundles.
2. Create a branch and keep changes narrowly scoped.
3. Add tests before changing behavior. Never add a write endpoint based only on inference, labels, or UI appearance; document evidence for the exact endpoint, verb, payload, validation limits, and controller readback.
4. Run:

   ```bash
   uv sync --extra test
   uv run pytest -q
   uvx ruff check custom_components tests
   python -m compileall -q custom_components tests
   ```

5. Explain user-visible and safety-boundary changes in the pull request.

Relay, pump, mixer, boiler, schedule, firmware, gateway, and controller-configuration writes are outside the accepted scope unless independently documented, hardware-tested, conservatively capability-gated, and explicitly approved by the maintainer.
