$ErrorActionPreference = "Stop"

$pythonPath = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
$buildScript = Join-Path $PSScriptRoot "build-release.py"

if (-not (Test-Path $pythonPath)) {
  throw "Expected virtual environment python at $pythonPath"
}

& $pythonPath $buildScript
