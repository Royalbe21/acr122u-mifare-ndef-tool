param(
    [string]$RepoName = "acr122u-mifare-ndef-tool",
    [switch]$Public
)

$ErrorActionPreference = "Stop"

Write-Host "Master NFC Writer - GitHub push helper" -ForegroundColor Cyan

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Install Git for Windows, then run this script again."
    exit 1
}

$visibility = if ($Public) { "--public" } else { "--private" }

if (Get-Command gh -ErrorAction SilentlyContinue) {
    Write-Host "GitHub CLI found. Creating/pushing repo with gh..." -ForegroundColor Green

    if (-not (Test-Path ".git")) {
        git init
        git add .
        git commit -m "Initial commit: Master NFC Writer"
        git branch -M main
    }

    gh repo create $RepoName $visibility --source . --remote origin --push
    Write-Host "Done. Repo should be available at:" -ForegroundColor Green
    Write-Host "https://github.com/Royalbe21/$RepoName"
}
else {
    Write-Host "GitHub CLI was not found." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Create an empty GitHub repo named: $RepoName"
    Write-Host "Then run these commands:"
    Write-Host ""
    Write-Host "git init"
    Write-Host "git add ."
    Write-Host 'git commit -m "Initial commit: Master NFC Writer"'
    Write-Host "git branch -M main"
    Write-Host "git remote add origin https://github.com/Royalbe21/$RepoName.git"
    Write-Host "git push -u origin main"
}
