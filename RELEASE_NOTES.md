# Dicom Video Extractor v0.2.0

## Deutsch

Diese Version macht aus dem früheren WillowbendDICOM-Projekt einen deutlich einfacher nutzbaren und besser wartbaren Stand.

### Neu in dieser Version

- automatische Release-Builds für Windows, macOS und Linux
- deutlich vereinfachte README mit deutscher und englischer Anleitung
- robustere DICOM-Verarbeitung für zusätzliche Pixel-Layouts und bessere FPS-Ermittlung
- optionale Metadaten-Einblendung direkt im exportierten Video
- optionale Anonymisierung für eingeblendete personenbezogene Daten

### Hinweise

- Windows wird als ZIP mit ausführbarer `.exe` bereitgestellt
- macOS und Linux werden als Archiv bereitgestellt
- macOS-Builds sind derzeit noch nicht signiert oder notariell beglaubigt
- bestimmte komprimierte DICOM-Dateien benötigen weiterhin zusätzliche Decoder wie `GDCM` oder `pylibjpeg`

## English

This release turns the older WillowbendDICOM project into a much easier-to-use and more maintainable distribution.

### Included in this release

- automated release builds for Windows, macOS, and Linux
- a much simpler README with German and English instructions
- more robust DICOM handling for additional pixel layouts and better FPS inference
- optional metadata overlays burned directly into exported videos
- optional anonymization for overlaid personal data

### Notes

- Windows is shipped as a ZIP containing the executable `.exe`
- macOS and Linux are shipped as archives
- macOS builds are not yet signed or notarized
- some compressed DICOM files still require additional decoders such as `GDCM` or `pylibjpeg`
