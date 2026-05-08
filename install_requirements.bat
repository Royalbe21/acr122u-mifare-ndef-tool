@echo off
echo Installing Python dependency: pyscard
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Python command failed. Trying py launcher...
    py -m pip install -r requirements.txt
)
pause
