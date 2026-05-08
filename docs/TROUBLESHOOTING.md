# Troubleshooting: `Write block 7 failed. SW=63 00`

## What it means

Block `7` is the **sector 1 trailer block** on a MIFARE Classic 1K card.

If the tool reports:

```text
NFC error: Write block 7 failed. SW=63 00
```

that usually means the card was already formatted once and its sector trailer permissions now block rewriting the trailer.

## Is the card dead?

No.

This usually means the card is already in a protected NFC/NDEF-style state. The fix is to **rewrite the NDEF payload without reformatting**, or use the hotfixed formatter that skips blocked trailer rewrites and continues to payload writing.

## Immediate workaround

Use:

```text
Business Card Mode
Write default business card without formatting
```

Do **not** choose `Format + Write` again on the same already-formatted card unless using the hotfix.

## Why the hotfix helps

The hotfix changes `format_mifare_classic_1k_as_ndef()` so that if a sector trailer rewrite is blocked, the tool continues and relies on the later payload write/verify step as the actual pass/fail test.
