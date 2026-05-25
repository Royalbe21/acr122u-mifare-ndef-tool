$ErrorActionPreference = "Stop"

if (-not (Test-Path ".git")) {
    throw "Run this script from the repo root."
}

$isccCandidates = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)

$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source
if (-not $iscc) {
    $iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not $iscc) {
    throw "Inno Setup 6 compiler was not found. Install it from https://jrsoftware.org/isinfo.php"
}

Write-Host "Building Windows 11 app..."
& ".\scripts\build_windows11_app.ps1"

$issPath = "installer\MasterNfcWriterWindows11.iss"
if (-not (Test-Path $issPath)) {
    throw "Missing installer script: $issPath"
}

Write-Host "Building installer..."
& $iscc $issPath

Write-Host ""
Write-Host "Installer complete:"
Write-Host "  installers\MasterNfcWriter-Windows11-Setup.exe"
