# Dicom Video Extractor

Modernized standalone DICOM-to-video converter based on the upstream project
[`YangChuan80/WillowbendDICOM`](https://github.com/YangChuan80/WillowbendDICOM).

This repository now separates:

- archived upstream reference material
- active application source code
- local build artifacts that should never be committed

## Current Project Layout

- `src/dicom_video_extractor/`
  Active application code.
- `tests/`
  Lightweight regression tests for core conversion behavior.
- `scripts/build-windows.ps1`
  PyInstaller-based Windows build entry point.
- `Original/Source/`
  Archived upstream source reference kept for comparison during migration.
- `Enhanced/`
  Archived enhanced upstream source reference without bundled runtime binaries.

## Why This Fork Exists

The upstream repository mixes source code with frozen binaries, installers,
notebook checkpoints, and historical Windows runtime payloads. That makes the
project large and difficult to maintain.

This fork is being reshaped to provide:

- a cleaner Python package structure
- a more robust DICOM conversion pipeline
- a standalone Windows executable build path
- room for fixes, extensions, and better testing

## What Has Been Modernized Already

- conversion logic was extracted from the old single-file scripts into
  dedicated modules
- DICOM metadata handling and frame-rate inference were separated from the GUI
- the new Tkinter GUI now acts as a thin wrapper around reusable conversion code
- basic tests now cover frame normalization, FPS inference, and output naming
- historical bundled binaries and installers were removed from the current
  project tree

## Local Development

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

## Building A Windows EXE

Use the provided build script:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
```

The generated application will be placed under:

```text
dist/Dicom-Video-Extractor/
```

## Release Strategy

Going forward, this repository should keep only:

- source code
- tests
- small static assets
- build scripts

It should not store generated EXEs, installers, embedded Python runtimes, or
temporary notebook artifacts in Git. New releases should be created from the
build output in `dist/`, ideally through GitHub Releases rather than committed
binary payloads.

## Known Next Steps

- validate the new converter against real-world DICOM samples
- improve handling for compressed transfer syntaxes and edge-case pixel layouts
- add smoke tests for the packaged Windows build
- optionally clean the historical Git history to remove legacy large binaries

## License

MIT. See [LICENSE](LICENSE).
