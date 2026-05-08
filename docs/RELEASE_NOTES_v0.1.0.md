# v0.1.0 - Initial working CLI release

## Summary

This release captures the first confirmed working version of **Master NFC Writer**.

It can format owned MIFARE Classic 1K cards as MAD1/NDEF cards, write NFC business-card URL records, verify the write, and produce cards readable by Android and iPhone in the confirmed test setup.

## Confirmed working

- ACS ACR122U reader/writer
- MIFARE Classic 1K card
- URL NDEF record writing
- MIFARE Classic MAD1/NDEF formatting
- Android phone reading
- iPhone reading

## Core features

- PC/SC reader detection
- Card UID read
- MIFARE Classic sector authentication check
- NDEF URI/text encoding
- NDEF read/decode
- Format + write workflow
- Batch write workflow
- Configurable business presets
- CSV write log

## Safety note

Use only on blank cards or cards you own. Do not use this project on access badges, transit cards, hotel cards, employee cards, gym cards, apartment cards, or any card that controls access to property or systems.
