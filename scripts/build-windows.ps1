$ErrorActionPreference = "Stop"

$pythonPath = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
$iconPath = Join-Path $PSScriptRoot "..\Original\Heart.ico"
$titlePath = Join-Path $PSScriptRoot "..\Original\Title.png"
$entryPoint = Join-Path $PSScriptRoot "..\app.py"

if (-not (Test-Path $pythonPath)) {
  throw "Expected virtual environment python at $pythonPath"
}

& $pythonPath -m PyInstaller `
  --noconfirm `
  --clean `
  --name "Dicom-Video-Extractor" `
  --windowed `
  --paths (Join-Path $PSScriptRoot "..\src") `
  --icon $iconPath `
  --add-data "$iconPath;Original" `
  --add-data "$titlePath;Original" `
  $entryPoint
