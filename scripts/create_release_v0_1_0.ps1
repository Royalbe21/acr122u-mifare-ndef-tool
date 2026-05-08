param(
    [switch]$Public
)

Write-Host "Creating GitHub release v0.1.0 for Master NFC Writer..."

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "GitHub CLI not found. Install with:"
    Write-Host "winget install --id GitHub.cli"
    exit 1
}

if (-not (Test-Path ".git")) {
    Write-Host "This must be run from the repo root."
    exit 1
}

git status

$hasTag = git tag --list "v0.1.0"
if (-not $hasTag) {
    git tag -a v0.1.0 -m "v0.1.0 - Initial working CLI release"
    git push origin v0.1.0
} else {
    Write-Host "Tag v0.1.0 already exists locally."
}

gh release create v0.1.0 `
    --title "v0.1.0 - Initial working CLI release" `
    --notes-file "docs/RELEASE_NOTES_v0.1.0.md"

Write-Host "Release created."
