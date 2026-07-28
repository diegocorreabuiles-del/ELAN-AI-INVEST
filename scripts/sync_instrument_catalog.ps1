$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$python = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "No existe .venv. Ejecuta .\update.bat antes de actualizar el catálogo."
}

& $python ".\scripts\sync_instrument_catalog.py"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
