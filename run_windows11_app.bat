@echo off
setlocal
cd /d "%~dp0"

python -m src.master_nfc_writer_windows11
if errorlevel 1 (
    echo.
    echo Python command failed. Trying the py launcher...
    py -m src.master_nfc_writer_windows11
)

if errorlevel 1 (
    echo.
    echo Master NFC Writer could not start.
    echo Install Python 3.10 or newer, then run install_requirements.bat.
    pause
)
