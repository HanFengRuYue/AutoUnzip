param(
    [Parameter(Mandatory = $true)]
    [string]$Tag,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$logFormat = '--pretty=format:- %s (%h)'

Push-Location $repoRoot
try {
    $tagRef = "refs/tags/$Tag"
    git rev-parse --verify $tagRef *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Tag not found: $Tag"
    }

    $previousTag = $null
    git rev-parse --verify "$Tag^" *> $null
    if ($LASTEXITCODE -eq 0) {
        $candidate = git describe --tags --abbrev=0 "$Tag^" 2>$null
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($candidate)) {
            $previousTag = $candidate.Trim()
        }
    }

    if ($previousTag) {
        $range = "$previousTag..$Tag"
        $lines = @(
            '## Changes',
            '',
            ('- Previous version: `{0}`' -f $previousTag),
            ('- Current version: `{0}`' -f $Tag),
            ''
        )
    }
    else {
        $range = $Tag
        $lines = @(
            '## Changes',
            '',
            ('- First release: `{0}`' -f $Tag),
            ''
        )
    }

    $commitLines = @(git log --reverse $logFormat $range)
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to generate git log for range: $range"
    }

    if (-not $commitLines -or ($commitLines.Count -eq 1 -and [string]::IsNullOrWhiteSpace($commitLines[0]))) {
        $commitLines = @('- No commits found in the selected range')
    }

    Set-Content -Path $OutputPath -Value ($lines + $commitLines) -Encoding utf8
}
finally {
    Pop-Location
}
