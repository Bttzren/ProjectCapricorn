@echo off
cd /d "%~dp0"
set PY=python
where py >nul 2>nul
if %errorlevel%==0 set PY=py
%PY% -m pip install --quiet --no-warn-script-location pyinstaller pillow
%PY% -m PyInstaller --noconfirm --onefile --windowed --name Capri --add-data "sprites;sprites" capri.py
echo.
echo Done. Your app is dist\Capri.exe  (chat works offline; paste an API key in the chat window to unlock the AI)
pause
