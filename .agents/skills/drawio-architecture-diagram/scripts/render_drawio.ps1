param(
    [Parameter(Mandatory = $true)]
    [string]$InputFile,

    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory,

    [double]$Scale = 1.5,

    [int]$Border = 20,

    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"

$resolvedInput = (Resolve-Path -LiteralPath $InputFile).Path
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$resolvedOutput = (Resolve-Path -LiteralPath $OutputDirectory).Path

$command = Get-Command "draw.io" -ErrorAction SilentlyContinue
$candidates = @(
    if ($command) { $command.Source },
    "$env:LOCALAPPDATA\Programs\draw.io\draw.io.exe",
    "$env:ProgramFiles\draw.io\draw.io.exe",
    "${env:ProgramFiles(x86)}\draw.io\draw.io.exe"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

if (-not $candidates) {
    throw "draw.io Desktop CLI was not found. Install it or add draw.io to PATH."
}

$drawio = $candidates[0]
[xml]$document = Get-Content -LiteralPath $resolvedInput -Raw
$pages = @($document.mxfile.diagram)

if ($pages.Count -eq 0) {
    throw "No draw.io pages found in $resolvedInput"
}

$baseName = [System.IO.Path]::GetFileNameWithoutExtension($resolvedInput)

if ($ValidateOnly) {
    Write-Output "draw.io CLI: $drawio"
    Write-Output "Pages: $($pages.Count)"
    for ($index = 1; $index -le $pages.Count; $index++) {
        Write-Output "Page ${index}: $($pages[$index - 1].name)"
    }
    return
}

for ($index = 1; $index -le $pages.Count; $index++) {
    $outputFile = Join-Path $resolvedOutput "$baseName-page-$index.png"
    & $drawio `
        --export `
        --format png `
        --page-index $index `
        --scale $Scale `
        --border $Border `
        --output $outputFile `
        $resolvedInput

    if ($LASTEXITCODE -ne 0) {
        throw "draw.io export failed for page $index with exit code $LASTEXITCODE"
    }
    if (-not (Test-Path -LiteralPath $outputFile)) {
        throw "draw.io reported success but did not create $outputFile"
    }

    Write-Output "Rendered page $index ($($pages[$index - 1].name)): $outputFile"
}
