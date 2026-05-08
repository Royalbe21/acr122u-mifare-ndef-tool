Write-Host "Creating GitHub release v0.2.1 for Master NFC Writer..."

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "GitHub CLI not found. Install with: winget install --id GitHub.cli"
    exit 1
}

if (-not (Test-Path ".git")) {
    Write-Host "This must be run from the repo root."
    exit 1
}

$tag = "v0.2.1"
$hasTag = git tag --list $tag
if (-not $hasTag) {
    git tag -a $tag -m "v0.2.1 - Guided GUI Batch Writing"
    git push origin $tag
} else {
    Write-Host "Tag $tag already exists locally."
}

gh release create $tag `
    --title "v0.2.1 - Guided GUI Batch Writing" `
    --notes-file "docs/RELEASE_NOTES_v0.2.1.md"

Write-Host "Release created."
