# Dicom Video Extractor v0.3.0

## Deutsch

### Highlights

- Vorschau direkt in der App:
  - Bewegtbild-DICOMs als laufende Vorschau
  - Einzelbild-DICOMs als Standbild-Vorschau
- Automatische DICOM-Erkennung:
  - Bewegtbild -> Export als MP4 + AVI
  - Einzelbild -> Export als PNG + JPG
- Deutlich verbesserter Import:
  - rekursiver Ordner-Import
  - DICOMDIR-Import mit Serienauswahl
  - Unterstützung für DICOM-Dateien ohne Dateiendung
- Erweiterte Queue-Funktionen:
  - Pause, Resume, Cancel
  - Priorisierung (Move Up/Down, Prioritize Selected)
  - fehlgeschlagene Dateien wieder direkt laden (`Load Failed`)
- Exportqualität und Nachvollziehbarkeit:
  - Window-Presets (CT/MR/US)
  - Sidecars pro Datei (`.json` + `.csv`)
  - Queue-Report pro Lauf (`conversion-report-YYYYMMDD-HHMMSS.json`)
  - Export-Profile (`Custom`, `Clinic Standard`, `Research`, `Anonymized`)
- Komfort:
  - Einstellungen bleiben zwischen App-Starts erhalten
  - Schnellzugriff auf Ausgabeordner und letzten Report

### Artefakte

- `Dicom-Video-Extractor-windows-x64.zip`
- `Dicom-Video-Extractor-macos.zip`
- `Dicom-Video-Extractor-linux-x64.tar.gz`

### Hinweise

- macOS-Builds sind derzeit nicht signiert/notarisiert.
- Einige komprimierte DICOM-Dateien benötigen weiterhin Decoder wie `GDCM` oder `pylibjpeg`.

## English

### Highlights

- In-app preview:
  - moving-image DICOM playback
  - single-image DICOM still preview
- Automatic DICOM content detection:
  - moving image -> MP4 + AVI
  - single image -> PNG + JPG
- Improved import workflows:
  - recursive folder import
  - DICOMDIR import with series selection
  - extensionless DICOM file support
- Extended queue controls:
  - pause, resume, cancel
  - prioritization (move up/down, prioritize selected)
  - quick failed-item reload (`Load Failed`)
- Better export traceability:
  - CT/MR/US window presets
  - per-file sidecars (`.json` + `.csv`)
  - per-run queue report (`conversion-report-YYYYMMDD-HHMMSS.json`)
  - export profiles (`Custom`, `Clinic Standard`, `Research`, `Anonymized`)
- Usability:
  - persistent settings across app restarts
  - quick open actions for output folder and latest report

### Artifacts

- `Dicom-Video-Extractor-windows-x64.zip`
- `Dicom-Video-Extractor-macos.zip`
- `Dicom-Video-Extractor-linux-x64.tar.gz`

### Notes

- macOS builds are currently unsigned / not notarized.
- Some compressed DICOM files still require extra decoder backends such as `GDCM` or `pylibjpeg`.
