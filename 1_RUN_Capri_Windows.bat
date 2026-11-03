@echo off
cd /d "%~dp0"
set PY=python
where py >nul 2>nul
if %errorlevel%==0 set PY=py
%PY% -m pip install --quiet --no-warn-script-location pillow
%PY% capri.py
if errorlevel 1 pause
