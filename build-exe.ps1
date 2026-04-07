$ErrorActionPreference = "Stop"

$repoRoot = $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

function Resolve-BootstrapPython {
    $candidates = @(
        "C:\Users\huang\AppData\Local\Python\bin\python.exe",
        "python.exe",
        "py.exe"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -eq "py.exe") {
            $command = Get-Command $candidate -ErrorAction SilentlyContinue
            if ($command) {
                return @{
                    Path = $command.Source
                    Args = @("-3")
                }
            }
            continue
        }

        if (Test-Path $candidate) {
            return @{
                Path = $candidate
                Args = @()
            }
        }

        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) {
            return @{
                Path = $command.Source
                Args = @()
            }
        }
    }

    throw "No usable Python interpreter was found. Please install Python 3.14+."
}

Push-Location $repoRoot
try {
    if (-not (Test-Path $venvPython)) {
        Write-Host "No .venv detected. Creating virtual environment..."
        $bootstrap = Resolve-BootstrapPython
        & $bootstrap.Path @($bootstrap.Args) -m venv .venv
    }

    Write-Host "Building AutoUnzip one-file EXE..."
    & powershell.exe -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\build.ps1")
}
finally {
    Pop-Location
}
