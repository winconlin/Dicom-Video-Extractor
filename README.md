# Dicom Video Extractor

Modernized standalone DICOM-to-video converter based on the upstream project
[`YangChuan80/WillowbendDICOM`](https://github.com/YangChuan80/WillowbendDICOM).

## Deutsch

### Was dieses Programm macht

Dieses Programm liest DICOM-Dateien ein und exportiert daraus Videos.

Neu im modernisierten Fork:

- einfachere Bedienung
- robustere DICOM-Konvertierung
- optionale Metadaten-Einblendung direkt im Video
- optionale Anonymisierung für eingeblendete Personendaten
- automatische Build-Pipeline für Windows, macOS und Linux über GitHub Releases

### Download für normale Nutzer

Du musst die EXE normalerweise **nicht selbst bauen**.

Sobald Releases erstellt werden, kannst du auf der GitHub-Seite einfach die
passende Datei herunterladen:

- `Dicom-Video-Extractor-windows-x64.zip`
- `Dicom-Video-Extractor-macos.zip`
- `Dicom-Video-Extractor-linux-x64.tar.gz`

Die Dateien werden automatisch über GitHub Actions gebaut, wenn ein neues Tag
wie `v1.0.0` erstellt wird oder der Workflow manuell gestartet wird.

### Windows Anleitung

1. Auf GitHub den neuesten Release öffnen.
2. `Dicom-Video-Extractor-windows-x64.zip` herunterladen.
3. ZIP-Datei entpacken.
4. Den Ordner `Dicom-Video-Extractor` öffnen.
5. `Dicom-Video-Extractor.exe` starten.

Falls Windows nachfragt:

- mit "Weitere Informationen" und dann "Trotzdem ausführen" bestätigen
- das kann bei nicht signierten Programmen normal sein

### macOS Anleitung

1. Auf GitHub den neuesten Release öffnen.
2. `Dicom-Video-Extractor-macos.zip` herunterladen.
3. ZIP-Datei entpacken.
4. Die App aus dem entpackten Ordner starten.

Falls macOS blockiert:

- in `Systemeinstellungen -> Datenschutz & Sicherheit` die App erlauben
- beim ersten Start eventuell Rechtsklick -> Öffnen verwenden

Hinweis:

- die App ist aktuell nicht notariell signiert

### Linux Anleitung

1. Auf GitHub den neuesten Release öffnen.
2. `Dicom-Video-Extractor-linux-x64.tar.gz` herunterladen.
3. Archiv entpacken.
4. Im entpackten Ordner das Programm starten.

Beispiel:

```bash
tar -xzf Dicom-Video-Extractor-linux-x64.tar.gz
cd Dicom-Video-Extractor
./Dicom-Video-Extractor
```

### Bedienung ganz einfach

1. DICOM-Dateien auswählen.
2. Zielordner auswählen.
3. Optional Format und FPS anpassen.
4. Optional "Video overlay" aktivieren.
5. Auswählen, welche Metadaten eingeblendet werden sollen.
6. Optional "Anonymize personal data" aktivieren.
7. Auf `Convert` klicken.

### Was bei der Anonymisierung passiert

Wenn die Anonymisierung aktiviert ist, werden eingeblendete Personendaten
verändert:

- Name wird in einen Platzhalternamen wie `Max Mustermann`, `Erika Musterfrau`,
  `John Doe` oder `Jane Doe` umgewandelt
- Patient ID wird zu einem anonymisierten Kennzeichen wie `ANON-XXXXXXXX`
- Geburtsdatum wird zu Geburtsjahr oder Alter reduziert, wenn das möglich ist

### Wichtiger Hinweis zu komprimierten DICOM-Dateien

Einige DICOM-Dateien brauchen zusätzliche Decoder. Wenn so eine Datei nicht
gelesen werden kann, gibt das Programm inzwischen einen klareren Hinweis auf
passende Decoder wie `GDCM` oder `pylibjpeg`.

## English

### What it does

This application converts DICOM files into video files and can optionally burn
selected metadata into the exported video.

### Simple downloads

End users should not need to build the app themselves. GitHub Actions can build
release artifacts for:

- Windows
- macOS
- Linux

Tagged releases such as `v1.0.0` publish downloadable archives on the GitHub
Releases page.

### Local development

Recommended Python version:

```powershell
Python 3.11+
```

Create a virtual environment and install dependencies:

```powershell
python -m venv .venv --without-pip
python -m pip --python .\.venv\Scripts\python.exe install -e .[build]
```

Run tests:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Run the app:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe app.py
```

### Build locally

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
```

Cross-platform local build entry point:

```powershell
python .\scripts\build-release.py
```

Build output:

```text
release-build/dist/Dicom-Video-Extractor/
```

## Current Project Layout

- `src/dicom_video_extractor/`
  Active application code.
- `tests/`
  Regression tests for conversion, frame-rate inference, and overlay behavior.
- `scripts/build-release.py`
  Shared PyInstaller entry point for release builds.
- `.github/workflows/release.yml`
  Cross-platform GitHub Actions build and release pipeline.
- `Original/Source/`
  Archived upstream source reference kept for comparison during migration.
- `Enhanced/`
  Archived enhanced upstream source reference without bundled runtime binaries.

## License

MIT. See [LICENSE](LICENSE).
