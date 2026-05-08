@echo off
python -m src.master_nfc_writer_gui
if errorlevel 1 (
    echo.
    echo Python command failed. Trying py launcher...
    py -m src.master_nfc_writer_gui
)
pause
