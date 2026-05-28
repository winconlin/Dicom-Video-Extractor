# Dicom Video Extractor

Modernized standalone DICOM converter based on [`YangChuan80/WillowbendDICOM`](https://github.com/YangChuan80/WillowbendDICOM).

## Deutsch

### Was die App kann

- DICOM-Dateien automatisch als **Einzelbild** oder **Bewegtbild** erkennen
- In-App-Vorschau:
  - Einzelbild als Standbild
  - Bewegtbild als laufende Vorschau
- Automatischer Export je nach Inhalt:
  - Bewegtbild-DICOM -> `MP4` + `AVI`
  - Einzelbild-DICOM -> `PNG` + `JPG`
- DICOM-Import:
  - Dateiauswahl (inkl. Dateien ohne Endung)
  - rekursiver Ordner-Import
  - `DICOMDIR` mit Serienauswahl
- Queue-Workflow:
  - Pause / Resume / Cancel
  - Priorisierung (Move Up, Move Down, Prioritize Selected)
  - fehlgeschlagene Dateien direkt erneut laden (`Load Failed`)
- Export-Optionen:
  - Window-Presets (CT/MR/US + Auto)
  - Export-Profile (`Custom`, `Clinic Standard`, `Research`, `Anonymized`)
  - optionales Overlay mit optionaler Anonymisierung
- Nachvollziehbarkeit:
  - Sidecars pro Datei (`.json` + `.csv`)
  - Queue-Report pro Lauf (`conversion-report-YYYYMMDD-HHMMSS.json`)
- Komfort:
  - Einstellungen werden zwischen App-Starts gespeichert
  - Schnellzugriff auf Ausgabeordner und letzten Queue-Report

### Download für Endnutzer

Releases enthalten fertige Pakete:

- `Dicom-Video-Extractor-windows-x64.zip`
- `Dicom-Video-Extractor-macos.zip`
- `Dicom-Video-Extractor-linux-x64.tar.gz`

### Schneller Ablauf

1. DICOM-Dateien, DICOM-Ordner oder DICOMDIR auswählen.
2. Vorschau und Metadaten prüfen.
3. Ausgabeordner und Export-Optionen festlegen.
4. `Convert Queue` starten.
5. Bei Bedarf Queue pausieren, fortsetzen oder abbrechen.
6. Nach dem Lauf Report/Sidecars prüfen und fehlgeschlagene Dateien per `Load Failed` erneut laden.

### Hinweise

- macOS-Builds sind aktuell nicht signiert/notarisiert.
- Einige komprimierte DICOM-Dateien benötigen zusätzliche Decoder (z. B. `GDCM`, `pylibjpeg`).

## English

### What the app does

- Automatically detects whether a DICOM contains a **single image** or **moving image**
- In-app preview:
  - still preview for single-image DICOMs
  - playback preview for moving-image DICOMs
- Automatic content-based export:
  - moving-image DICOM -> `MP4` + `AVI`
  - single-image DICOM -> `PNG` + `JPG`
- Import options:
  - file picker (including extensionless files)
  - recursive folder scan
  - `DICOMDIR` import with series picker
- Queue workflow:
  - pause / resume / cancel
  - prioritization controls
  - reload failed files (`Load Failed`)
- Export controls:
  - medical window presets (CT/MR/US + Auto)
  - export profiles (`Custom`, `Clinic Standard`, `Research`, `Anonymized`)
  - optional overlay with optional anonymization
- Traceability:
  - per-file sidecars (`.json` + `.csv`)
  - per-run queue report (`conversion-report-YYYYMMDD-HHMMSS.json`)
- Usability:
  - persistent settings across app restarts
  - quick open buttons for output folder and latest report

## Local development

### Requirements

- Python `3.11+`

### Setup

```powershell
python -m venv .venv --without-pip
python -m pip --python .\.venv\Scripts\python.exe install -e .[build]
```

Optional decoder backends:

```powershell
python -m pip --python .\.venv\Scripts\python.exe install -e .[decoders]
```

### Run tests

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Run the app

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe app.py
```

## Build

### Local build

```powershell
python .\scripts\build-release.py
```

Output folder:

```text
release-build/dist/Dicom-Video-Extractor/
```

### GitHub Release build

The workflow in `.github/workflows/release.yml` builds artifacts for Windows, macOS, and Linux when a tag `v*` is pushed.

## Project layout

- `src/dicom_video_extractor/` - application code
- `tests/` - regression tests
- `scripts/build-release.py` - cross-platform PyInstaller entrypoint
- `.github/workflows/release.yml` - CI build + GitHub release publishing

## License

MIT. See [LICENSE](LICENSE).
