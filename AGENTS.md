# AGENTS.md

## Zweck und Geltungsbereich

Diese Regeln gelten für das gesamte Repository `C:\Localdata\Projekte\seltron_clausius`. Maßgebliche Quellen sind der aktuelle Code, `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `VERIFIED_STATE.md`, `pyproject.toml` und die CI-Workflows.

## Vor jeder Änderung

1. `AGENTS.md` und `VERIFIED_STATE.md` vollständig lesen.
2. `git status --short --branch`, den aktuellen Branch und relevante Diffs prüfen.
3. Betroffene Symbole bis zu Definitionen und Aufrufstellen verfolgen; keine APIs, Imports oder Abhängigkeiten annehmen.
4. Bei Verhaltensänderungen zuerst passende Tests ergänzen oder anpassen.
5. Keine vorhandenen untracked, ignorierten oder sensiblen Dateien löschen, verschieben oder veröffentlichen, ohne ihren Zweck zu klären.

## Projektarchitektur und Sicherheitsgrenzen

- `api.py` kapselt die Auth0-/SeltronHome-Kommunikation.
- `runtime.py` verwaltet Tokenrotation, Polling, Schreibsynchronisierung und bestätigendes Rücklesen.
- `coordinator.py` integriert den Laufzeitstatus in Home Assistant.
- `models.py` normalisiert Cloud-Antworten.
- `controls.py` definiert Allowlisten, Wertebereiche und Schrittweiten.
- Die Entity-Plattformen projizieren den Coordinator-Zustand in Home Assistant.

Read-only ist der Standard. Neue Cloud-Schreibzugriffe dürfen nicht aus Namen, UI-Verhalten oder Vermutungen abgeleitet werden. Für jeden neuen Schreibpfad sind ein belegter Endpoint, HTTP-Verb, Payload, Grenzen, Capability-Gating, Fehlerbehandlung, Hardwaretest und bestätigendes Rücklesen erforderlich. Relais-, Pumpen-, Mischer-, Kessel-, Zeitprogramm-, Firmware-, Gateway- und Reglerkonfigurations-Schreibzugriffe bleiben ohne ausdrückliche Maintainerfreigabe außerhalb des erlaubten Umfangs.

Live-Schreiboperationen gegen reale Geräte oder die Seltron-Cloud dürfen nicht als gewöhnlicher Test ausgeführt werden. Die separat installierte Probe bleibt read-only.

## Datenschutz und Geheimnisse

Niemals Zugangsdaten, Tokens, E-Mail-Adressen, Seriennummern, Installations-/Geräte-IDs, rohe Cloud-Antworten, HAR-Dateien, Home-Assistant-Backups, `.storage`-Daten oder private Diagnosen lesen, ausgeben, committen oder veröffentlichen. Diagnosedaten müssen redigiert bleiben.

Lokale sensible und projektbezogene Hilfsdaten liegen unter:

`C:\Localdata\Hilfsdateien\seltron_clausius`

Insbesondere befinden sich dort `diagnostics-private`, lokale Release-Artefakte, Recherchekopien und Secrets. Hermes-Sessions und Hermes-Projekte dürfen nicht in andere Projekte verschoben werden.

## Werkzeuge und lokale Umgebung

Externe Werkzeuge, verwaltete Laufzeiten, globale Pakete, Downloads und Tool-Caches werden ausschließlich unter `C:\Localdata\Tools` installiert oder gespeichert. Keine Installationen im Windows-Benutzerprofil und keine verteilten Tool-Installationen.

Für dieses Projekt gelten auf diesem Rechner:

```bash
export PATH='/c/Localdata/Tools/uv/0.12.3:$PATH'
export UV_CACHE_DIR='C:\Localdata\Tools\Caches\uv'
export UV_PYTHON_INSTALL_DIR='C:\Localdata\Tools\uv\python'
export UV_PYTHON_PREFERENCE=only-managed
```

Die virtuelle Projektumgebung `.venv` darf im Projektroot liegen; sie ist abgeleitet und ignoriert. Der von Hermes geerbte globale `PYTHONPATH` kann fremde Pakete einschleusen. Projektprüfungen deshalb mit `env -u PYTHONPATH` ausführen.

## Implementierungsregeln

- Änderungen eng begrenzen; keine nebenläufigen Refactorings oder Formatierungsaktionen.
- Bestehenden Stil, Typisierung, immutable Datenmodelle und async-Konventionen beibehalten.
- Abhängigkeiten nur über `pyproject.toml` und `uv.lock` ändern; Lockfile bewusst aktualisieren.
- Keine generierten Artefakte, Caches, Release-ZIPs oder private Diagnosedaten committen.
- Benutzerwirksame Änderungen in `README.md` und `CHANGELOG.md` dokumentieren.
- Keine Commits, Pushes, Releases oder History-Rewrites ohne ausdrücklichen Auftrag.

## Verbindliche Prüfungen

Nach Code-, Abhängigkeits- oder Teständerungen mindestens:

```bash
export PATH='/c/Localdata/Tools/uv/0.12.3:$PATH'
export UV_CACHE_DIR='C:\Localdata\Tools\Caches\uv'
export UV_PYTHON_INSTALL_DIR='C:\Localdata\Tools\uv\python'
export UV_PYTHON_PREFERENCE=only-managed

env -u PYTHONPATH uv sync --frozen --extra test
env -u PYTHONPATH uv run pytest -q
env -u PYTHONPATH uvx ruff check custom_components tests
env -u PYTHONPATH uv run python -m compileall -q custom_components tests
```

Zusätzlich vor sicherheitsrelevanten Übergaben:

```bash
env -u PYTHONPATH uv lock --check
env -u PYTHONPATH uv run python -m pip check
/c/Localdata/Tools/gitleaks/8.30.1/gitleaks.exe git . --config .gitleaks.toml --redact --no-banner
```

Fehlschläge nicht durch erfundene Ergebnisse ersetzen. Ursache untersuchen, alternative belastbare Prüfwege verwenden und verbleibende Blocker offen dokumentieren.

## VERIFIED_STATE.md

`VERIFIED_STATE.md` beschreibt nur einen tatsächlich gemessenen Zustand. Nach Änderungen an Code, Abhängigkeiten, Architektur, Testinfrastruktur oder Release-Metadaten die dokumentierten Prüfungen erneut ausführen und erst danach Datum, Commit und Ergebnisse aktualisieren.
