# Windows 11 App

Master NFC Writer now includes a Windows 11 desktop entry point that reuses the same NFC engine as the command-line tool.

## Run From Source

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the Windows 11 app:

```powershell
.\run_windows11_app.bat
```

Or run it directly:

```powershell
python -m src.master_nfc_writer_windows11
```

## Build The EXE

From the repo root:

```powershell
.\scripts\build_windows11_app.ps1
```

The packaged app is created at:

```text
dist\MasterNfcWriter-Windows11\MasterNfcWriter-Windows11.exe
```

The build script uses PyInstaller, the Windows icon in `assets/windows/`, and the existing `pyscard` dependency.

## Build The Installer

Install Inno Setup 6, then run:

```powershell
.\scripts\build_windows_installer.ps1
```

The installer is created at:

```text
installers\MasterNfcWriter-Windows11-Setup.exe
```

## Hardware

- Windows 11
- ACS ACR122U reader/writer
- MIFARE Classic 1K cards you own
- PC/SC smart card service enabled

## Notes

Use the app only on blank cards or cards you own. Do not write to access badges, employee cards, hotel cards, transit cards, apartment cards, gym cards, or any card that controls access.
