# Changelog

## v0.3.0

- added preview playback for moving-image DICOMs and single-frame preview for still-image DICOMs
- added automatic content detection with dual export strategy:
  - moving image DICOM -> MP4 + AVI
  - single image DICOM -> PNG + JPG
- added recursive folder import and support for extensionless DICOM files
- added queue workflow with pause, resume, cancel, prioritization, and failed-file reload
- added DICOMDIR parsing with series-level selection dialog
- added medical window presets (CT/MR/US) and preset application before export
- added metadata sidecar export per source file (`.json` + `.csv`)
- added export profiles (`Custom`, `Clinic Standard`, `Research`, `Anonymized`)
- added queue-level conversion report export (`conversion-report-YYYYMMDD-HHMMSS.json`)
- added persistent app settings (folders, profile/options, overlay selections) across app restarts
- added quick actions to open output folder and open the last generated queue report
- expanded automated tests for queue helpers, settings persistence, and report generation

## v0.2.0

- modernized the old WillowbendDICOM codebase into a maintainable Python package
- added standalone packaging for Windows and automated release builds for macOS and Linux
- cleaned historical binary artifacts from the repository and release strategy
- improved DICOM robustness for more pixel array shapes and better frame-rate inference
- added optional metadata overlays directly in exported videos
- added optional anonymization for overlaid patient data
- expanded the README with simple German and English usage instructions
- prepared curated release notes for GitHub Releases
