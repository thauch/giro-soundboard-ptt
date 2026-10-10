@echo off
setlocal
cd /d "%~dp0"
set /p HELPER_VERSION=<VERSION
py -3 --version >nul 2>&1
if errorlevel 1 (
  echo Install Python 3 for Windows first, then run this file again.
  pause
  exit /b 1
)
py -3 -m venv .build-venv
if errorlevel 1 goto failed
".build-venv\Scripts\python.exe" -m pip install "pyinstaller==6.22.2"
if errorlevel 1 goto failed
".build-venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name "Giro-Soundboard-PTT-v%HELPER_VERSION%" soundboard-ptt.py
if errorlevel 1 goto failed
echo.
echo Built: %CD%\dist\Giro-Soundboard-PTT-v%HELPER_VERSION%.exe
start "" "%CD%\dist"
pause
exit /b 0
:failed
echo Build failed. Review the error above.
pause
exit /b 1
