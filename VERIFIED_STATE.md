# VERIFIED_STATE

Stand: 2026-08-09 17:30 CEST

## Geltungsbereich

Dieses Dokument beschreibt den auf diesem Rechner real geprüften Zustand des Projekts `C:\Localdata\Projekte\seltron_clausius`. Maßgeblich bleiben der aktuelle Quellcode und erneut ausgeführte Prüfungen; dieses Dokument ist kein Ersatz für eine neue Verifikation nach Änderungen.

## Projektzweck

Seltron Clausius ist eine inoffizielle Home-Assistant-Custom-Integration für Seltron-Gateways und WDC-Heizungsregler über die SeltronHome-Cloud. Sie stellt Zustände als Sensoren und Binärsensoren bereit und erlaubt einen bewusst begrenzten, capability-gesteuerten Satz von Benutzeraktionen.

## Architektur

- `custom_components/seltron_clausius/config_flow.py`: Anmeldung, Reauthentication und Options Flow.
- `custom_components/seltron_clausius/api.py`: Auth0- und SeltronHome-HTTP-Kommunikation.
- `custom_components/seltron_clausius/runtime.py`: Tokenrotation, gemeinsames Polling-/Schreib-Locking, Preflight, Capability-Prüfung und bestätigendes Rücklesen.
- `custom_components/seltron_clausius/coordinator.py`: Home-Assistant-`DataUpdateCoordinator` mit fünfminütigem Polling.
- `custom_components/seltron_clausius/models.py`: Normalisierung proprietärer Cloud-Antworten in unveränderliche Datenmodelle.
- `custom_components/seltron_clausius/controls.py`: Allowlisten, Wertebereiche und Schrittweiten für erlaubte Schreibvorgänge.
- `sensor.py`, `binary_sensor.py`, `select.py`, `number.py`, `switch.py`, `datetime.py`: Entity-Plattformen.
- `diagnostics.py`: redigierte Diagnosedaten.
- `probe.py`: separat aufrufbare, ausschließlich lesende Cloud-Probe.

Schreibzugriffe sind standardmäßig deaktiviert, capability-gesteuert, vorvalidiert und durch Rücklesen bestätigt. Relais, Pumpen, Mischer, Kessel, Zeitprogramme, Firmware und Reglerkonfiguration bleiben absichtlich read-only.

## Git-Zustand

- Vorhandenes Repository: ja; es wurde nicht neu initialisiert.
- Branch: `main`
- Upstream: `origin/main`
- Divergenz zum Upstream bei der Verifikation: `0` voraus / `0` zurück
- Verifizierter HEAD: `11530d8fa5928347172d0daa748153bc8faf0933`
- Kurzform: `11530d8 ci: align gitleaks version with local validation`
- Lokale Tags nach Synchronisierung: `pre-publication-0.4.0`, `v0.4.1`
- `v0.4.1` zeigt auf den verifizierten HEAD.
- Vor dem Erstellen von `AGENTS.md` und `VERIFIED_STATE.md` war der Arbeitsbaum frei von tracked, staged und untracked Projektdateien.

Das Repository enthält vier vorhandene Commits und den Remote `https://github.com/subi900/seltron-clausius-home-assistant.git`. Diese Provenienz widerspricht der Annahme, das übertragene Projekt habe nie ein Git-Repository besessen; die vorhandene Historie wurde deshalb bewahrt.

## Version und Release

- Projektversion in `pyproject.toml`: `0.4.1`
- Integrationsversion in `custom_components/seltron_clausius/manifest.json`: `0.4.1`
- GitHub-Release/Tag: `v0.4.1`
- Bereits verifizierter Archivname: `seltron_clausius-0.4.1.zip`
- Bereits verifizierte Größe: `69.469 Bytes`
- Bereits verifizierter SHA-256: `264ddb3c792940b5b72096c06796cae208e6bf12c6f715d8021e06f4be8cf2d5`

## Lokale Werkzeug- und Python-Umgebung

Die vom anderen Rechner übertragene `.venv` war nicht sauber relokalisiert; `uv run` scheiterte mit `uv trampoline failed to canonicalize script path`. Sie wurde kontrolliert neu erzeugt.

- `uv`: `0.12.3` unter `C:\Localdata\Tools\uv\0.12.3`
- verwaltete Python-Laufzeit: `C:\Localdata\Tools\uv\python\cpython-3.11-windows-x86_64-none`
- Python: `3.11.15`
- Projektumgebung: `C:\Localdata\Projekte\seltron_clausius\.venv`
- uv-Cache: `C:\Localdata\Tools\Caches\uv`
- pytest: `9.1.1`
- Ruff über `uvx`: `0.16.2`
- Gitleaks: `8.30.1` unter `C:\Localdata\Tools\gitleaks\8.30.1`

Für verlässliche Prüfungen muss der von Hermes geerbte globale `PYTHONPATH` entfernt werden. Verwendete Umgebungsvariablen:

```bash
export PATH='/c/Localdata/Tools/uv/0.12.3:$PATH'
export UV_CACHE_DIR='C:\Localdata\Tools\Caches\uv'
export UV_PYTHON_INSTALL_DIR='C:\Localdata\Tools\uv\python'
export UV_PYTHON_PREFERENCE=only-managed
export COVERAGE_FILE='C:\Localdata\Hilfsdateien\seltron_clausius\.coverage'
env -u PYTHONPATH <Befehl>
```

## Reproduzierbare Prüfungen

Die folgenden Prüfungen wurden nach der Neuerzeugung der Umgebung real ausgeführt:

```bash
env -u PYTHONPATH uv lock --check
env -u PYTHONPATH uv sync --check --frozen --extra test
env -u PYTHONPATH uv run python -m pip check
env -u PYTHONPATH uv run pytest -q
env -u PYTHONPATH uv run pytest -q --cov=custom_components.seltron_clausius --cov-report=term-missing
env -u PYTHONPATH uvx ruff check custom_components tests
env -u PYTHONPATH uv run python -m compileall -q custom_components tests
/c/Localdata/Tools/gitleaks/8.30.1/gitleaks.exe git . --config .gitleaks.toml --redact --no-banner
```

Ergebnisse:

- Lockfile gültig.
- Umgebung vollständig synchron; `uv sync --check` würde keine Änderungen vornehmen.
- Keine defekten Python-Anforderungen.
- `82 passed`, eine Deprecation-Warnung aus Home Assistant `2023.12.4`.
- Coverage-Lauf erfolgreich: 80 % Gesamt-Coverage, ebenfalls `82 passed`.
- Ruff: `All checks passed!`
- Syntaxkompilierung: erfolgreich.
- Gitleaks `8.30.1`: vier Commits geprüft, keine Leaks gefunden.

Die GitHub-Actions-Workflows `Tests` und `Home Assistant and HACS validation` waren beim Audit für den verifizierten HEAD erfolgreich.

## Lokale Hilfs- und sensible Daten

Projektbezogene Hilfsdateien wurden aus dem Projektbaum nach `C:\Localdata\Hilfsdateien\seltron_clausius` verschoben:

- `hermes/transferred-project-state/`: alte Hilfsskripte und HACS-Recherchekopien
- `diagnostics-private/`: private Diagnostik- und Prüfevidenz
- `release/`: lokale Release-Archive und Release-Notizen
- `docs/`: ausgelagerte Entwurfsdokumentation
- `secrets/ha_token`: lokales Geheimnis; Inhalt nicht geprüft oder dokumentiert

Hermes-Sessions und Hermes-Projekte wurden nicht verschoben. Neue externe Werkzeuge, Laufzeiten und Tool-Caches gehören nach `C:\Localdata\Tools`; neue projektspezifische Hilfsdateien nach `C:\Localdata\Hilfsdateien\seltron_clausius`.

## Bekannte Grenzen

- Die SeltronHome-Cloud-API ist proprietär und nicht öffentlich dokumentiert.
- Live-Schreiboperationen wurden bei der Bestandsverifikation aus Sicherheitsgründen nicht gegen reale Geräte ausgelöst.
- Home Assistant `2023.12.4` erzeugt in der Testumgebung eine Deprecation-Warnung.
- Die Integration unterstützt bewusst nur einen begrenzten Satz capability-gesteuerter Schreiboperationen.
- Explizite `TODO`-, `FIXME`-, `NotImplemented`-, Skip- oder Xfail-Marker wurden im maßgeblichen Code und in den Tests nicht gefunden.

## Aktualisierung dieses Dokuments

Nach jeder Änderung an Code, Abhängigkeiten, Testinfrastruktur, Release-Metadaten oder Architektur sind die oben genannten Prüfungen erneut auszuführen. Erst danach dürfen Datum, Git-Commit und Ergebnisse in diesem Dokument aktualisiert werden.
