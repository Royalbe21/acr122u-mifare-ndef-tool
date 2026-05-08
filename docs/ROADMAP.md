# Roadmap

## v0.4 - Cleanup and reliability

- Split the large app file into modules:
  - `pcsc_reader.py`
  - `mifare_classic.py`
  - `ndef.py`
  - `config.py`
  - `cli.py`
- Add better card-type detection
- Add safer backup/restore for owned cards
- Improve batch writer flow
- Add clearer error messages for authentication failure

## v0.5 - GUI

- Build a Windows GUI with Python + Tkinter or PySide6
- Add card status panel
- Add preset editor
- Add batch writer screen
- Add one-click verify button

## v0.6 - More tag support

- Add NTAG213/215/216 support
- Add MIFARE Classic 4K support
- Add export/import card templates

## v1.0 - Production release

- Installer package
- Signed release binaries
- Full documentation
- User-friendly GUI
