$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$vendorDir = Join-Path $repoRoot "vendor\7zip"
$assetDir = Join-Path $repoRoot "assets"
$iconPath = Join-Path $assetDir "app_icon.ico"

if (-not (Test-Path $python)) {
    throw "Virtual environment Python not found: $python"
}

Push-Location $repoRoot
try {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $vendorDir) | Out-Null
    & $python -m pip install -e ".[build]"
    & $python .\scripts\generate_icon.py
    & $python .\scripts\fetch_7zip.py
    & $python -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --name AutoUnzip `
        --icon $iconPath `
        --specpath .\build\spec `
        --paths .\src `
        --add-data "${assetDir};assets" `
        --add-data "${vendorDir};vendor\7zip" `
        .\src\launcher.py

    $distRoot = Join-Path $repoRoot "dist\AutoUnzip"
    New-Item -ItemType Directory -Force -Path $distRoot | Out-Null
    if (-not (Test-Path ".\dist\AutoUnzip.exe")) {
        throw "PyInstaller did not produce dist\\AutoUnzip.exe"
    }
    Move-Item -Force ".\dist\AutoUnzip.exe" (Join-Path $distRoot "AutoUnzip.exe")
    Write-Host "Build complete: $distRoot\\AutoUnzip.exe"
}
finally {
    Pop-Location
}
