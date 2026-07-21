[CmdletBinding()]
param(
    [string[]]$PythonVersions = @("3.11", "3.12", "3.13", "3.14"),
    [switch]$SkipPull
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$supportedVersions = @("3.11", "3.12", "3.13", "3.14")
$requestedVersions = @($PythonVersions | Select-Object -Unique)

foreach ($version in $requestedVersions) {
    if ($version -notin $supportedVersions) {
        throw "Versión no soportada: $version. Use: $($supportedVersions -join ', ')."
    }
}

docker version --format "{{.Server.Version}}" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop no está disponible. Inícielo y vuelva a ejecutar el script."
}

$containerCommand = @'
set -eu
apt-get update -qq
apt-get install -y -qq --no-install-recommends git >/dev/null
rm -rf /var/lib/apt/lists/*
git config --global --add safe.directory /workspace
git clone --quiet --no-hardlinks /workspace /work
cd /work
python -m pip install --quiet --upgrade "pip==26.1.2"
python -m pip install --quiet -r requirements.txt
python scripts/check_git_flow.py
python scripts/check_lock.py
python -m pip check
python -m ruff check .
python -m black --check .
python -m pytest -p no:cacheprovider
python scripts/build_distribution.py --output /tmp/elan-quantum-ci.zip
python scripts/build_distribution.py --verify /tmp/elan-quantum-ci.zip
'@

$mount = "type=bind,source=$repoRoot,target=/workspace,readonly"

foreach ($version in $requestedVersions) {
    $image = "python:$version-slim"
    Write-Host "`n=== ELAN CI | Python $version ===" -ForegroundColor Cyan

    if (-not $SkipPull) {
        docker pull $image
        if ($LASTEXITCODE -ne 0) {
            throw "No se pudo descargar $image."
        }
    }

    docker run --rm `
        --mount $mount `
        --workdir /tmp `
        --env PYTHONDONTWRITEBYTECODE=1 `
        --env COVERAGE_FILE=/tmp/.coverage `
        $image sh -lc $containerCommand

    if ($LASTEXITCODE -ne 0) {
        throw "La matriz falló en Python $version."
    }
}

Write-Host "`nMatriz CI superada: $($requestedVersions -join ', ')." -ForegroundColor Green
