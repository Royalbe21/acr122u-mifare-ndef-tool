param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

function Get-PythonCommand {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python")
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-3")
    }
    throw "Python 3.10 or newer was not found. Install it from https://www.python.org/downloads/windows/"
}

function Invoke-Python {
    param(
        [string[]]$Arguments
    )

    $exe = $script:PythonCommand[0]
    $prefix = @()
    if ($script:PythonCommand.Length -gt 1) {
        $prefix = $script:PythonCommand[1..($script:PythonCommand.Length - 1)]
    }
    & $exe @prefix @Arguments
}

if (-not (Test-Path ".git")) {
    throw "Run this script from the repo root."
}

$script:PythonCommand = Get-PythonCommand
$iconPath = "assets\windows\master-nfc-writer.ico"
$pngPath = "assets\windows\master-nfc-writer.png"
$entryPoint = "src\master_nfc_writer_windows11.py"
$appName = "MasterNfcWriter-Windows11"

if (-not (Test-Path $iconPath)) {
    throw "Missing icon: $iconPath"
}

if (-not (Test-Path $pngPath)) {
    throw "Missing icon image: $pngPath"
}

if (-not $SkipInstall) {
    Invoke-Python @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-Python @("-m", "pip", "install", "-r", "requirements.txt", "pyinstaller")
}

Invoke-Python @(
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name",
    $appName,
    "--icon",
    $iconPath,
    "--add-data",
    "assets\windows\master-nfc-writer.png;assets\windows",
    "--hidden-import",
    "smartcard.System",
    "--hidden-import",
    "smartcard.Exceptions",
    "--hidden-import",
    "smartcard.util",
    $entryPoint
)

Write-Host ""
Write-Host "Build complete:"
Write-Host "  dist\$appName\$appName.exe"
