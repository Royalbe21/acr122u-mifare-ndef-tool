# Guided GUI Batch Writing

v0.2.1 adds a safer GUI workflow for writing multiple owned NFC business cards.

## How it works

1. Open the GUI:

```powershell
python -m src.master_nfc_writer_gui
```

2. Choose your preset/payload.
3. Click **Guided Batch Mode**.
4. Choose a mode:
   - **Format + Write fresh cards** for blank/factory cards.
   - **Write only already-formatted cards** for cards that already have the MIFARE Classic NDEF/MAD layout.
5. Click **Start / Reset Batch**.
6. Place one card on the ACR122U.
7. Click **Write Current Card**.
8. Wait for success, remove the card, then repeat.

## Counters

The GUI tracks:

- successful cards
- failed cards
- last UID written
- duplicate UIDs already written in this batch

## Safety

Use only on blank cards or cards you own.

Do not use this tool on access badges, hotel cards, employee cards, transit cards, apartment/gate cards, gym cards, or anything that controls access.
