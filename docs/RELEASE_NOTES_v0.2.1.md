# v0.2.1 - Guided GUI Batch Writing

## Summary

Adds guided GUI batch writing for owned NFC business cards and improves handling of already-formatted MIFARE Classic cards.

## Added

- Guided GUI batch-writing window
- Success/failure counters
- Last UID display
- Duplicate UID detection
- Overwrite checkbox for cards with existing NDEF data
- Batch mode choice:
  - Format + Write fresh cards
  - Write Only already-formatted cards
- Troubleshooting doc for `Write block 7 failed. SW=63 00`

## Fixed

- `Format + Write` is more forgiving on cards that were already formatted once and block sector trailer rewrites.

## Safety

Use only on blank cards or cards you own. Do not use this on access badges, hotel cards, transit cards, employee cards, or any card that controls access.
