# Master NFC Writer

A Windows-friendly NFC business-card writer for the **ACS ACR122U** reader/writer and **MIFARE Classic 1K** cards.

This project started as a practical tool for writing phone-readable NFC business cards. The current version can format owned MIFARE Classic 1K cards as MAD1/NDEF tags, write URL/phone/email/text records, verify the write, read existing NDEF payloads, and batch-write multiple cards.

> Tested successfully with an ACR122U, MIFARE Classic 1K cards, Android, and iPhone.

---

## Features

- Detects PC/SC readers such as the **ACS ACR122U**
- Windows 11 desktop app with launcher icon
- Reads card UID
- Inspects MIFARE Classic 1K sector authentication
- Formats owned MIFARE Classic 1K cards as **MAD1/NDEF**
- Writes NFC business card links
- Writes URL, phone, email, and text records
- Reads and decodes simple NDEF records
- Batch write mode for multiple cards
- Overwrite safety prompts
- CSV write logging
- Configurable business-card presets

---

## Hardware

Recommended:

- ACS ACR122U NFC reader/writer
- Blank/owned MIFARE Classic 1K cards
- Windows 10/11 PC

---

## Install

```powershell
python -m pip install -r requirements.txt
```

If `python` does not work, try:

```powershell
py -m pip install -r requirements.txt
```

---

## Run

From the repo folder:

```powershell
python .\master_nfc_writer.py
```

Or double-click:

```text
run_tool.bat
```

For the Windows 11 desktop app:

```text
run_windows11_app.bat
```

To build a packaged Windows `.exe`:

```powershell
.\scripts\build_windows11_app.ps1
```

See [`docs/WINDOWS_11_APP.md`](docs/WINDOWS_11_APP.md).

---

## Recommended workflow

For one card:

```text
1. Business Card Mode
1. Format + write default business card
```

For a stack of cards:

```text
1. Business Card Mode
4. Batch format + write default business card
```

To verify a card:

```text
4. Read / Decode NDEF
```

---

## Configuration

Copy the example config:

```powershell
copy config.example.json config.json
```

Edit `config.json` with your business card link, website, phone, and email.

`config.json` is ignored by Git so your personal/business details are not accidentally committed.

---

## Safety

Use this only on cards you own.

Do **not** use this on:

- Access badges
- Employee cards
- Hotel cards
- Transit cards
- Apartment/gate cards
- Gym cards
- Any card that controls access to property or systems

This tool is for NFC business cards and owned personal NFC tags only.

---

## Card compatibility note

MIFARE Classic 1K can work, and this project successfully made one readable by Android and iPhone. Still, for broad customer-facing production cards, **NTAG213/215/216** tags are generally more universal.

---

## Roadmap

See [`docs/ROADMAP.md`](docs/ROADMAP.md).

---

## License

MIT License. See [`LICENSE`](LICENSE).
