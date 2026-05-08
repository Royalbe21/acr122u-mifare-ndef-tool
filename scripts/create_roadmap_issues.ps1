Write-Host "Creating GitHub roadmap issues..."

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "GitHub CLI not found. Install with:"
    Write-Host "winget install --id GitHub.cli"
    exit 1
}

if (-not (Test-Path ".git")) {
    Write-Host "This must be run from the repo root."
    exit 1
}

$issues = @(
    @{
        Title="v0.2.0: Build Windows GUI starter"
        Body="Create a Tkinter-based GUI around the proven CLI core. Include reader selection, scan/read card status, preset selection, write, format + write, and activity log."
        Labels="enhancement,gui"
    },
    @{
        Title="v0.2.1: Add guided batch writing to GUI"
        Body="Add a GUI workflow for writing many cards in sequence, with success/failure counters, duplicate UID detection, and card remove/insert prompts."
        Labels="enhancement,gui,batch"
    },
    @{
        Title="v0.3.0: Package Windows executable"
        Body="Use PyInstaller to build a portable Windows .exe/ZIP so the app can run without launching Python manually."
        Labels="enhancement,packaging"
    },
    @{
        Title="Add NTAG213/215/216 support"
        Body="Add detection and writing support for NTAG cards. NTAG cards are generally more universal for NFC business cards than MIFARE Classic."
        Labels="enhancement,nfc"
    },
    @{
        Title="Add owned-card backup/restore"
        Body="Add optional backup and restore for owned blank/business cards before formatting, with clear safety warnings and no support for unauthorized access cards."
        Labels="enhancement,safety"
    },
    @{
        Title="Improve test coverage for NDEF encoding/decoding"
        Body="Expand tests for URI, phone, email, text, TLV padding, extraction, and decode behavior."
        Labels="testing"
    },
    @{
        Title="Add screenshots and setup photos to README"
        Body="Add screenshots of the CLI/GUI workflow and photos showing the ACR122U setup for easier onboarding."
        Labels="documentation"
    }
)

foreach ($issue in $issues) {
    gh issue create --title $issue.Title --body $issue.Body --label $issue.Labels
}

Write-Host "Roadmap issues created."
