@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

:: --- 1. Administrator rights (winws / WinDivert require admin) ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator rights ^(accept the UAC prompt^)...
    if "%~1"=="" (
        powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    ) else (
        powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -ArgumentList '%*' -Verb RunAs"
    )
    if errorlevel 1 (
        echo.
        echo [ERROR] Could not elevate. Right-click kzapret.bat -^> "Run as administrator".
        pause
    )
    exit /b
)

title kzapret
echo [kzapret] Administrator: OK
echo [kzapret] Folder: %cd%

:: --- 2. Python virtual environment (textual + cryptography) ---
if not exist ".venv\Scripts\python.exe" (
    echo [kzapret] Creating Python venv ^(first run, internet needed^)...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if not exist ".venv\Scripts\python.exe" (
        echo [ERROR] venv creation failed. Is Python 3 installed?  https://python.org
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] pip install failed. Check your internet connection.
        pause
        exit /b 1
    )
)

:: --- 3. Run kzapret ---
echo [kzapret] Starting...
echo.
set "PYTHONUTF8=1"
".venv\Scripts\python.exe" -X utf8 -m kzapret %*
set "RC=%errorlevel%"

echo.
echo [kzapret] Finished (exit code %RC%).
if not "%RC%"=="0" echo See logs\kzapret.log for error details.
echo Press any key to close this window...
pause >nul
endlocal
