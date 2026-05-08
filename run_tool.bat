@echo off
python master_nfc_writer.py
if errorlevel 1 (
    echo.
    echo Python command failed. Trying py launcher...
    py master_nfc_writer.py
)
pause
